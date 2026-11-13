from cards.card_def import CardType
from engine.actions.helpers import _require_priority, _sorcery_timing
from engine.events import apply, ZoneChange
from engine.state import GameState, IllegalAction, Zone

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