from collections.abc import Sequence

from cards.abilities.ability import AbilityKind, Cost
from cards.card_def import CardType
from engine.actions.helpers import _check_targets, _require_priority
from engine.actions.mana import _pay_mana, plan_payment, resolve_mana_ability
from engine.events import apply, TapChanged, ZoneChange
from engine.stack import StackObject
from engine.state import GameState, IllegalAction, Target, Zone

def check_activate(state: GameState, player: int, source_id: int, index: int, targets: Sequence[Target]):
    """
    - Checks if `player` can activate `source_id`s ability right now, with these `targets`.
    - Raises IllegalAction, or returns (ability, plan).
    - Used to help determine legal actions that can be performed
    
    :param state: Current GameState
    :type state: GameState
    :param player: Player checking for legal abilities
    :type player: int
    :param source_id: Source GameObject ID being checked
    :type source_id: int
    :param index: Which ability the object has that is being checked
    :type index: int
    :param targets: #TODO Description
    :type targets: Sequence[Target]
    """

    # check for priority - throws exception -> no priority = no actions
    _require_priority(state, player)

    # get the game object
    obj = state.objects.get(source_id)

    # check if the player controls that permanent #TODO: Might get weird with cycling?
    if obj is None or obj.zone is not Zone.BATTLEFIELD or obj.controller != player:
        raise IllegalAction("not your permanent")
    
    # check if the ability exists on the object
    if not 0 <= index < len(obj.card.abilities):
        raise IllegalAction("no such ability")
    
    # get the ability from the card
    ability = obj.card.abilities[index]

    # check that ability is activated
    if ability.kind not in (AbilityKind.ACTIVATED, AbilityKind.MANA):
        raise IllegalAction("not an activated ability")
    
    # get the ability cost
    cost = ability.cost or Cost()

    # if the cost is tapping itself
    if cost.tap_self:
        # can't tap something already tapped
        if obj.tapped:
            raise IllegalAction("already tapped")
        # can't tap a creature that is summoning sick
        if CardType.CREATURE in state.characteristics(source_id).types and state.summoning_sick(obj):
            raise IllegalAction("summoning sick")
    
    # check for legality of targets - throws exception
    _check_targets(state, ability.targets, targets, player)
    
    # plan how this ability can be paid for
    plan = []
    if cost.mana:
        plan = plan_payment(state, player, cost.mana, exclude=source_id)
        if plan is None:
            raise IllegalAction("can't pay mana cost")
        
    return ability, plan


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
