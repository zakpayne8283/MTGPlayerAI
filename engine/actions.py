"""Player actions: validation, execution, and legal-action enumeration.

Pattern: check_*() validates and raises IllegalAction *without mutating*; the executor calls check, then mutates.
legal_actions() = candidate actions filtered through the same validators, so the two can't drift apart.
"""
from __future__ import annotations
from collections import Counter
from itertools import product

from agents.base import PlayLand, CastSpell, ActivateAbility
from cards.ability import Ability, AbilityKind, Cost
from cards.card_def import CardType, ManaCost
from engine.effects import AddMana
from engine.events import apply, ZoneChange, TapChanged
from engine.stack import StackObject, cast_spell, resolve_mana_ability, target_is_legal
from engine.state import GameState, Zone, Step, Target, IllegalAction

MAIN_STEPS = {Step.MAIN1, Step.MAIN2}
_TAP_ONLY = Cost(tap_self=True)
_ANY = object()


# ---------- helpers ----------
def _require_priority(state: GameState, player: int) -> None:
    if state.priority_player != player:
        raise IllegalAction("you don't have priority")


def _sorcery_timing(state: GameState, player: int) -> bool:
    return state.active_player == player and state.step in MAIN_STEPS and not state.stack


def _spell_ability(card) -> Ability | None:
    return next((a for a in card.abilities if a.kind is AbilityKind.SPELL), None)


def legal_targets(state: GameState, spec, caster: int) -> list[Target]:
    cands = [Target("player", p.id) for p in state.players]
    cands += [Target("object", i) for i in state.battlefield]
    return [t for t in cands if target_is_legal(state, spec, t, caster)]


def _check_targets(state: GameState, specs, targets, player: int) -> None:
    if len(targets) != len(specs):
        raise IllegalAction("wrong number of targets")
    for spec, t in zip(specs, targets):
        if not target_is_legal(state, spec, t, player):
            raise IllegalAction("illegal target")


# ---------- mana ----------
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


# ---------- play land ----------
def check_play_land(state: GameState, player: int, obj_id: int) -> None:
    _require_priority(state, player)
    obj = state.objects.get(obj_id)
    if obj is None or obj.zone is not Zone.HAND or obj.owner != player:
        raise IllegalAction("card not in your hand")
    if CardType.LAND not in obj.card.types:
        raise IllegalAction("not a land")
    if not _sorcery_timing(state, player):
        raise IllegalAction("lands only in your main phase with an empty stack")
    if state.players[player].lands_played >= 1:
        raise IllegalAction("already played a land this turn")


def play_land(state: GameState, player: int, obj_id: int) -> None:
    check_play_land(state, player, obj_id)
    apply(state, ZoneChange(obj_id, Zone.HAND, Zone.BATTLEFIELD, controller=player))
    state.players[player].lands_played += 1  # playing a land doesn't use the stack


# ---------- cast ----------
def check_cast(state: GameState, player: int, obj_id: int, targets):
    _require_priority(state, player)
    obj = state.objects.get(obj_id)
    if obj is None or obj.zone is not Zone.HAND or obj.owner != player:
        raise IllegalAction("card not in your hand")
    if CardType.LAND in obj.card.types:
        raise IllegalAction("lands aren't cast")
    if CardType.INSTANT not in obj.card.types and not _sorcery_timing(state, player):
        raise IllegalAction("sorcery-speed only")
    ability = _spell_ability(obj.card)
    _check_targets(state, ability.targets if ability else (), targets, player)
    plan = plan_payment(state, player, obj.card.cost)
    if plan is None:
        raise IllegalAction("can't pay mana cost")
    return plan


def cast(state: GameState, player: int, obj_id: int, targets=()) -> None:
    plan = check_cast(state, player, obj_id, targets)
    _pay_mana(state, player, state.objects[obj_id].card.cost, plan)
    cast_spell(state, player, obj_id, tuple(targets))


# ---------- activate ----------
def check_activate(state: GameState, player: int, source_id: int, index: int, targets):
    _require_priority(state, player)
    obj = state.objects.get(source_id)
    if obj is None or obj.zone is not Zone.BATTLEFIELD or obj.controller != player:
        raise IllegalAction("not your permanent")
    if not 0 <= index < len(obj.card.abilities):
        raise IllegalAction("no such ability")
    ab = obj.card.abilities[index]
    if ab.kind not in (AbilityKind.ACTIVATED, AbilityKind.MANA):
        raise IllegalAction("not an activated ability")
    cost = ab.cost or Cost()
    if cost.tap_self:
        if obj.tapped:
            raise IllegalAction("already tapped")
        if CardType.CREATURE in state.characteristics(source_id).types and state.summoning_sick(obj):
            raise IllegalAction("summoning sick")
    _check_targets(state, ab.targets, targets, player)
    plan = []
    if cost.mana:
        plan = plan_payment(state, player, cost.mana, exclude=source_id)
        if plan is None:
            raise IllegalAction("can't pay mana cost")
    return ab, plan


def activate(state: GameState, player: int, source_id: int, index: int, targets=()) -> None:
    ab, plan = check_activate(state, player, source_id, index, targets)
    if ab.kind is AbilityKind.MANA:
        resolve_mana_ability(state, player, source_id, ab)
        return
    cost = ab.cost or Cost()
    if cost.mana:
        _pay_mana(state, player, cost.mana, plan)
    if cost.tap_self:
        apply(state, TapChanged(source_id, True))
    if cost.sacrifice_self:
        apply(state, ZoneChange(source_id, Zone.BATTLEFIELD, Zone.GRAVEYARD))
    state.stack.append(StackObject(state.next_id(), source_id, player, ab, tuple(targets)))


# ---------- dispatch / enumeration ----------
def perform(state: GameState, player: int, action) -> None:
    if isinstance(action, PlayLand):
        play_land(state, player, action.obj_id)
    elif isinstance(action, CastSpell):
        cast(state, player, action.obj_id, action.targets)
    elif isinstance(action, ActivateAbility):
        activate(state, player, action.source_id, action.ability_index, action.targets)
    else:
        raise IllegalAction(f"unknown action {action!r}")


def _try(fn, *args) -> bool:
    try:
        fn(*args)
        return True
    except IllegalAction:
        return False


def legal_actions(state: GameState, player: int, include_mana_abilities: bool = False) -> list:
    """All legal non-pass actions. Mana abilities are excluded by default because casting auto-taps."""
    if state.priority_player != player:
        return []
    acts: list = []
    for oid in state.players[player].hand:
        obj = state.objects[oid]
        if CardType.LAND in obj.card.types:
            if _try(check_play_land, state, player, oid):
                acts.append(PlayLand(oid))
            continue
        ability = _spell_ability(obj.card)
        options = [legal_targets(state, s, player) for s in (ability.targets if ability else ())]
        for combo in product(*options):
            if _try(check_cast, state, player, oid, combo):
                acts.append(CastSpell(oid, combo))
    for obj in state.permanents():
        if obj.controller != player:
            continue
        for i, ab in enumerate(obj.card.abilities):
            if ab.kind is AbilityKind.MANA and not include_mana_abilities:
                continue
            if ab.kind not in (AbilityKind.ACTIVATED, AbilityKind.MANA):
                continue
            for combo in product(*[legal_targets(state, s, player) for s in ab.targets]):
                if _try(check_activate, state, player, obj.id, i, combo):
                    acts.append(ActivateAbility(obj.id, i, combo))
    return acts
