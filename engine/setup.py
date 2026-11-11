"""Game setup: load decks, shuffle, draw opening hands."""
from __future__ import annotations
import random

from cards.alpha import CARDS
from events import apply, CardDrawn
from mana import ManaPool
from state import GameState, Player, Zone


def new_game(decks: list[list[str]], agents: list, seed: int = 0, hand_size: int = 7) -> GameState:
    """decks: list of card-name lists (one per player). Player 0 goes first. No mulligans yet."""
    state = GameState(
        players=[Player(i, agent=a, mana_pool=ManaPool()) for i, a in enumerate(agents)],
        rng=random.Random(seed),
    )
    for i, deck in enumerate(decks):
        for name in deck:
            state.create_object(CARDS[name], owner=i, zone=Zone.LIBRARY)
        state.rng.shuffle(state.players[i].library)
    for p in state.players:
        for _ in range(hand_size):
            apply(state, CardDrawn(p.id))
    return state
