import pytest
from mtg.agents.random_agent import RandomAgent
from mtg.engine.setup import new_game
from mtg.engine.turn import run_game
from .helpers import BOLT_DECK, GREEN_DECK, BLACK_DECK


def play(deck_a, deck_b, seed):
    g = new_game([deck_a, deck_b], [RandomAgent(seed), RandomAgent(seed + 1000)], seed=seed)
    return g, run_game(g)


def test_mountain_bolt_mirror_ends_with_a_winner():
    g, winners = play(BOLT_DECK, BOLT_DECK, seed=1)
    assert len(winners) == 1
    loser = 1 - winners[0]
    assert g.players[loser].life <= 0 or g.players[loser].drew_from_empty


def test_game_is_deterministic():
    g1, w1 = play(BOLT_DECK, BOLT_DECK, seed=7)
    g2, w2 = play(BOLT_DECK, BOLT_DECK, seed=7)
    assert w1 == w2 and g1.turn == g2.turn and [p.life for p in g1.players] == [p.life for p in g2.players]


@pytest.mark.parametrize("seed", range(25))
def test_random_games_never_crash(seed):
    decks = [BOLT_DECK, GREEN_DECK, BLACK_DECK]
    a, b = decks[seed % 3], decks[(seed + 1) % 3]
    g, winners = play(a, b, seed)
    assert g.turn <= 200
