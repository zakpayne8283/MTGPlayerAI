import pytest

from engine import combat
from engine.sba import check_sbas
from engine.state import Zone, Target, IllegalAction
from tests.helpers import make_game, put


def setup_combat(attacker="Grizzly Bears"):
    g = make_game(turn=3)  # turn 3 is player 0's; creatures put at turn 0 aren't summoning sick
    a = put(g, attacker, Zone.BATTLEFIELD, owner=0)
    c = combat.CombatState()
    combat.declare_attackers(g, c, 0, [a.id], Target("player", 1))
    return g, c, a


def test_unblocked_damage():
    g, c, a = setup_combat()
    combat.deal_combat_damage(g, c)
    assert g.players[1].life == 18
    assert g.objects[a.id].tapped


def test_blocked_trade():
    g, c, a = setup_combat()
    blocker = put(g, "Grizzly Bears", Zone.BATTLEFIELD, owner=1)
    combat.declare_blockers(g, c, 1, {blocker.id: a.id})
    combat.deal_combat_damage(g, c)
    check_sbas(g)
    assert g.players[1].life == 20
    assert not g.battlefield  # both bears died


def test_summoning_sick_creature_cannot_attack():
    g = make_game(turn=3)
    old = put(g, "Grizzly Bears", Zone.BATTLEFIELD)
    fresh = put(g, "Grizzly Bears", Zone.BATTLEFIELD)
    fresh.entered_turn = 3  # entered this turn
    assert combat.legal_attackers(g, 0) == [old.id]

def test_flyer_only_blocked_by_flyer_or_reach():
    g, c, elemental = setup_combat("Air Elemental")
    bears = put(g, "Grizzly Bears", Zone.BATTLEFIELD, owner=1)
    assert not combat.can_block(g, bears.id, elemental.id)
    with pytest.raises(IllegalAction):
        combat.declare_blockers(g, c, 1, {bears.id: elemental.id})

    g, c, elemental = setup_combat('Air Elemental')
    def_elem = put(g, 'Air Elemental', Zone.BATTLEFIELD, owner=1)
    assert combat.can_block(g, def_elem.id, elemental.id)