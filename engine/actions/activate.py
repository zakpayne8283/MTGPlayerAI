from cards.abilities.ability import AbilityKind, Cost
from cards.card_def import CardType
from engine.actions.helpers import _check_targets, _require_priority
from engine.actions.mana import _pay_mana, plan_payment, resolve_mana_ability
from engine.events import apply, TapChanged, ZoneChange
from engine.stack import StackObject
from engine.state import GameState, IllegalAction, Zone

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
