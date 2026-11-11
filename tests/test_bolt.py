"""Raw stack path: cast_spell + resolve_top without validation or mana."""
from mtg.engine.stack import cast_spell, resolve_top
from mtg.engine.state import Zone, Target
from .helpers import make_game, put


def test_bolt_face():
    g = make_game()
    bolt = put(g, "Lightning Bolt", Zone.HAND)
    cast_spell(g, 0, bolt.id, (Target("player", 1),))
    resolve_top(g)
    assert g.players[1].life == 17
    assert len(g.players[0].graveyard) == 1
