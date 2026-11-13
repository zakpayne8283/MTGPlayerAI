from cards.card_def import CardType

from engine.actions.helpers import _check_targets, _require_priority, _spell_ability, _sorcery_timing
from engine.actions.mana import plan_payment, _pay_mana
from engine.stack import cast_spell
from engine.state import GameState, IllegalAction, Zone

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