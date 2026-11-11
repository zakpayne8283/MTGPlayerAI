"""Combat: attackers, blockers, damage. No keywords yet (flying, first strike, trample...)."""
from __future__ import annotations
from dataclasses import dataclass, field

from cards.card_def import CardType
from state import GameState, Target, IllegalAction
from events import apply, DamageDealt, TapChanged


@dataclass
class CombatState:
    attackers: dict[int, Target] = field(default_factory=dict)    # attacker id -> defending player
    blockers: dict[int, list[int]] = field(default_factory=dict)  # attacker id -> ordered blocker ids
    # presence of a key in `blockers` means that attacker is "blocked", even if blockers later vanish


def _untapped_creatures(state: GameState, player: int) -> list[int]:
    out = []
    for o in state.permanents():
        if o.controller == player and not o.tapped and \
                CardType.CREATURE in state.characteristics(o.id).types:
            out.append(o.id)
    return out


def legal_attackers(state: GameState, player: int) -> list[int]:
    return [i for i in _untapped_creatures(state, player) if not state.summoning_sick(state.objects[i])]


def legal_blockers(state: GameState, player: int) -> list[int]:
    return _untapped_creatures(state, player)  # TODO: evasion (flying, walks)


def declare_attackers(state: GameState, combat: CombatState, player: int, chosen: list[int],
                      defender: Target) -> None:
    legal = set(legal_attackers(state, player))
    for aid in chosen:
        if aid not in legal:
            raise IllegalAction(f"{aid} can't attack")
    for aid in dict.fromkeys(chosen):
        combat.attackers[aid] = defender
        apply(state, TapChanged(aid, True))  # TODO: vigilance


def declare_blockers(state: GameState, combat: CombatState, defender: int,
                     assignment: dict[int, int]) -> None:
    """assignment: blocker id -> attacker id."""
    legal = set(legal_blockers(state, defender))
    for blocker, attacker in assignment.items():
        if blocker not in legal:
            raise IllegalAction(f"{blocker} can't block")
        if attacker not in combat.attackers or combat.attackers[attacker].id != defender:
            raise IllegalAction(f"{attacker} isn't attacking this player")
        combat.blockers.setdefault(attacker, []).append(blocker)
    # TODO: attacker's controller should order blockers; currently declaration order


def _alive(state: GameState, oid: int) -> bool:
    return oid in state.objects and state.objects[oid].zone.name == "BATTLEFIELD"


def deal_combat_damage(state: GameState, combat: CombatState) -> None:
    """All combat damage is dealt simultaneously: collect first, then apply."""
    pending: list[DamageDealt] = []
    for aid, defender in combat.attackers.items():
        if not _alive(state, aid):
            continue
        power = state.characteristics(aid).power or 0
        if aid not in combat.blockers:
            pending.append(DamageDealt(aid, defender, power, is_combat=True))
            continue
        blockers = [b for b in combat.blockers[aid] if _alive(state, b)]
        # attacker assigns lethal damage in order; any excess goes on the last blocker
        remaining = power
        for i, b in enumerate(blockers):
            toughness = state.characteristics(b).toughness or 0
            lethal = max(toughness - state.objects[b].damage, 0)
            amt = remaining if i == len(blockers) - 1 else min(remaining, lethal)
            if amt > 0:
                pending.append(DamageDealt(aid, Target("object", b), amt, is_combat=True))
            remaining -= amt
        for b in blockers:
            bp = state.characteristics(b).power or 0
            if bp > 0:
                pending.append(DamageDealt(b, Target("object", aid), bp, is_combat=True))
    for ev in pending:
        apply(state, ev)
