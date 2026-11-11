"""State-based actions (rule 704). Run repeatedly until nothing changes."""
from __future__ import annotations

from cards.card_def import CardType
from state import GameState, Zone
from events import apply, Destroyed, ZoneChange


class GameOver(Exception):
    def __init__(self, winners: list[int]):
        self.winners = winners


def check_sbas(state: GameState) -> None:
    while _check_once(state):
        pass


def _check_once(state: GameState) -> bool:
    changed = False

    losers = [p.id for p in state.players if p.life <= 0 or p.drew_from_empty]
    if losers:  # TODO: simultaneous loss => draw
        raise GameOver([p.id for p in state.players if p.id not in losers])

    for obj in list(state.permanents()):
        ch = state.characteristics(obj.id)
        if CardType.CREATURE not in ch.types or ch.toughness is None:
            continue
        if ch.toughness <= 0:  # no regeneration possible
            apply(state, ZoneChange(obj.id, Zone.BATTLEFIELD, Zone.GRAVEYARD))
            changed = True
        elif obj.damage >= ch.toughness:  # destroy (regeneration can replace)
            apply(state, Destroyed(obj.id))
            changed = True

    # TODO: auras attached to illegal/missing objects go to graveyard
    return changed
