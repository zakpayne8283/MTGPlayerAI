from itertools import product

from agents.base import ActivateAbility, CastSpell, PlayLand
from cards.abilities.ability import AbilityKind
from cards.card_def import CardType
from engine.actions.activate import activate, check_activate
from engine.actions.cast import cast, check_cast, _spell_ability
from engine.actions.helpers import legal_targets
from engine.actions.lands import check_play_land, play_land
from engine.state import GameState, IllegalAction

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
