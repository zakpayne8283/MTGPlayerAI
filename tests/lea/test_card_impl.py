from engine.actions.lands import play_land
from engine.stack import resolve_top
from engine.state import Zone
from engine.turn import _push_pending_triggers

from tests.helpers import make_game, put

def test_ankh_damages_controller_of_entering_land():
    game = make_game()
    put(game, 'Ankh of Mishra', Zone.BATTLEFIELD, owner=0)
    land = put(game, 'Mountain', Zone.HAND, owner=1)
    game.active_player = game.priority_player = 1
    play_land(game, 1, land.id)
    assert len(game.pending_triggers) == 1
    _push_pending_triggers(game)
    resolve_top(game)
    assert game.players[1].life == 18   # the land's controller, not Ankh's