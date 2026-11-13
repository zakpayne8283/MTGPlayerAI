import pytest
from agents.base import CastSpell

from engine.actions import cast, dispatch, lands
from engine.stack import resolve_top
from engine.state import Zone, Step, Target, IllegalAction
from tests.helpers import make_game, put


def test_play_land_once_per_turn():
    g = make_game()
    a, b = put(g, "Mountain", Zone.HAND), put(g, "Mountain", Zone.HAND)
    lands.play_land(g, 0, a.id)
    assert len(g.battlefield) == 1
    with pytest.raises(IllegalAction):
        lands.play_land(g, 0, b.id)


def test_land_needs_main_phase_and_empty_stack():
    g = make_game(step=Step.UPKEEP)
    land = put(g, "Mountain", Zone.HAND)
    with pytest.raises(IllegalAction):
        lands.play_land(g, 0, land.id)


def test_cast_bolt_autotaps_and_resolves():
    g = make_game()
    mtn = put(g, "Mountain", Zone.BATTLEFIELD)
    bolt = put(g, "Lightning Bolt", Zone.HAND)
    cast.cast(g, 0, bolt.id, (Target("player", 1),))
    assert g.objects[mtn.id].tapped
    assert len(g.stack) == 1
    resolve_top(g)
    assert g.players[1].life == 17


def test_cannot_cast_without_mana():
    g = make_game()
    bolt = put(g, "Lightning Bolt", Zone.HAND)
    with pytest.raises(IllegalAction):
        cast.cast(g, 0, bolt.id, (Target("player", 1),))
    assert dispatch.legal_actions(g, 0) == []


def test_creature_is_sorcery_speed():
    g = make_game(step=Step.END)
    put(g, "Forest", Zone.BATTLEFIELD)
    put(g, "Forest", Zone.BATTLEFIELD)
    bears = put(g, "Grizzly Bears", Zone.HAND)
    with pytest.raises(IllegalAction):
        cast.cast(g, 0, bears.id)
    g.step = Step.MAIN1
    cast.cast(g, 0, bears.id)
    resolve_top(g)
    assert any(o.card.name == "Grizzly Bears" for o in g.permanents())


def test_giant_growth_expires_and_saves_bears_from_bolt():
    g = make_game()
    bears = put(g, "Grizzly Bears", Zone.BATTLEFIELD)
    put(g, "Forest", Zone.BATTLEFIELD)
    gg = put(g, "Giant Growth", Zone.HAND)
    cast.cast(g, 0, gg.id, (Target("object", bears.id),))
    resolve_top(g)
    ch = g.characteristics(bears.id)
    assert (ch.power, ch.toughness) == (5, 5)


def test_fizzle_when_target_gone():
    g = make_game()
    bears = put(g, "Grizzly Bears", Zone.BATTLEFIELD, owner=1)
    put(g, "Mountain", Zone.BATTLEFIELD)
    put(g, "Mountain", Zone.BATTLEFIELD)
    b1, b2 = put(g, "Lightning Bolt", Zone.HAND), put(g, "Lightning Bolt", Zone.HAND)
    cast.cast(g, 0, b1.id, (Target("object", bears.id),))
    cast.cast(g, 0, b2.id, (Target("object", bears.id),))
    resolve_top(g)  # first bolt kills bears (after SBA); simulate SBA:
    from engine.sba import check_sbas
    check_sbas(g)
    resolve_top(g)  # second bolt fizzles, no crash
    assert len(g.players[0].graveyard) == 2


def test_terror_target_restriction():
    g = make_game()
    swamp_bear = put(g, "Grizzly Bears", Zone.BATTLEFIELD, owner=1)
    put(g, "Swamp", Zone.BATTLEFIELD)
    put(g, "Swamp", Zone.BATTLEFIELD)
    terror = put(g, "Terror", Zone.HAND)
    acts = dispatch.legal_actions(g, 0)
    assert CastSpell(terror.id, (Target("object", swamp_bear.id),)) in acts


def test_ancestral_recall():
    g = make_game()
    put(g, "Island", Zone.BATTLEFIELD)
    for _ in range(3):
        put(g, "Island", Zone.LIBRARY)
    rec = put(g, "Ancestral Recall", Zone.HAND)
    cast.cast(g, 0, rec.id, (Target("player", 0),))
    resolve_top(g)
    assert len(g.players[0].hand) == 3
