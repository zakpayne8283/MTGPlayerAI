from collections import Counter

from cards.abilities.ability import AbilityKind, Cost
from cards.card_def import CardType, ManaCost
from engine.effects import AddMana
from engine.stack import resolve_mana_ability
from engine.state import GameState

_TAP_ONLY = Cost(tap_self=True)
_ANY = object()

def mana_sources(state: GameState, player: int, exclude: int | None = None):
    """(obj_id, ability_index, color) for untapped permanents with a plain 'T: add mana' ability."""
    out = []
    for obj in state.permanents():
        if obj.controller != player or obj.tapped or obj.id == exclude:
            continue
        if CardType.CREATURE in state.characteristics(obj.id).types and state.summoning_sick(obj):
            continue
        for i, ab in enumerate(obj.card.abilities):
            if (ab.kind is AbilityKind.MANA and ab.cost == _TAP_ONLY and len(ab.effects) == 1
                    and isinstance(ab.effects[0], AddMana) and ab.effects[0].amount == 1):
                out.append((obj.id, i, ab.effects[0].color))
                break
    return out


def plan_payment(state: GameState, player: int, cost: ManaCost, exclude: int | None = None):
    """Greedy auto-tap plan: floating pool mana first, then untapped sources. None if unaffordable."""
    pool = Counter(state.players[player].mana_pool.mana)
    sources = mana_sources(state, player, exclude)
    used: list = []

    def take(color=_ANY) -> bool:
        for s in sources:
            if s not in used and (color is _ANY or s[2] == color):
                used.append(s)
                return True
        return False

    print(cost)

    for c in cost.colored:
        if pool[c] > 0:
            pool[c] -= 1
        elif not take(c):
            return None
    for _ in range(cost.generic):
        k = next((k for k, v in pool.items() if v > 0), _ANY)
        if k is not _ANY:
            pool[k] -= 1
        elif not take():
            return None
    return used


def _pay_mana(state: GameState, player: int, cost: ManaCost, plan) -> None:
    for oid, idx, _ in plan:
        resolve_mana_ability(state, player, oid, state.objects[oid].card.abilities[idx])
    state.players[player].mana_pool.pay(cost)