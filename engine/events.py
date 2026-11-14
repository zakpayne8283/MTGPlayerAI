"""Every state change is an Event passed through apply(). Hooks for replacement/prevention/triggers live here."""
from __future__ import annotations
from dataclasses import dataclass, field, replace
from typing import Callable

from engine.state import GameState, Zone, Target


@dataclass(frozen=True)
class Event:
    pass


@dataclass(frozen=True)
class ZoneChange(Event):
    obj_id: int
    from_zone: Zone
    to_zone: Zone
    controller: int | None = None  # for Control Magic / enters under another's control
    new_id: int | None = field(default=None, compare=None)


@dataclass(frozen=True)
class DamageDealt(Event):
    source_id: int | None
    target: Target
    amount: int
    is_combat: bool = False


@dataclass(frozen=True)
class LifeChanged(Event):
    player: int
    delta: int


@dataclass(frozen=True)
class CardDrawn(Event):
    player: int


@dataclass(frozen=True)
class TapChanged(Event):
    obj_id: int
    tapped: bool


@dataclass(frozen=True)
class SpellCast(Event):
    stack_id: int
    controller: int


@dataclass(frozen=True)
class Destroyed(Event):
    obj_id: int  # replacement hook point for regeneration


# Returns a modified Event, the same event to pass through, or None to cancel it.
Replacement = Callable[[GameState, Event], Event | None]
REPLACEMENTS: list[Replacement] = []  # TODO: move onto GameState so it's per-game and clonable


def apply(state: GameState, event: Event) -> None:
    """The one mutation path."""
    ev = _run_replacements(state, event)
    if ev is None:
        return
    ev = _mutate(state, ev)
    state.log.append(ev)
    _collect_triggers(state, ev)


def _run_replacements(state: GameState, event: Event) -> Event | None:
    # TODO: apply each replacement at most once per event; affected player chooses order
    for rep in REPLACEMENTS:
        result = rep(state, event)
        if result is None:
            return None
        event = result
    return event


def _mutate(state: GameState, ev: Event) -> None:
    if isinstance(ev, ZoneChange):
        if ev.obj_id not in state.objects:
            return None
        new = state.move(ev.obj_id, ev.to_zone, ev.controller)
        return replace(ev, new_id=new.id)
    elif isinstance(ev, DamageDealt):
        if ev.target.kind == "player":
            apply(state, LifeChanged(ev.target.id, -ev.amount))
        elif ev.target.id in state.objects:
            state.objects[ev.target.id].damage += ev.amount
    elif isinstance(ev, LifeChanged):
        state.players[ev.player].life += ev.delta
    elif isinstance(ev, CardDrawn):
        p = state.players[ev.player]
        if p.library:
            state.move(p.library[0], Zone.HAND)  # zone change => new object id, like any other
        else:
            p.drew_from_empty = True  # checked in SBA
    elif isinstance(ev, TapChanged):
        if ev.obj_id in state.objects:
            state.objects[ev.obj_id].tapped = ev.tapped
    elif isinstance(ev, Destroyed):
        if ev.obj_id in state.objects and state.objects[ev.obj_id].zone is Zone.BATTLEFIELD:
            apply(state, ZoneChange(ev.obj_id, Zone.BATTLEFIELD, Zone.GRAVEYARD))
    # SpellCast: informational only


def _collect_triggers(state: GameState, ev: Event) -> None:
    """Queue matching triggered abilities; stack placement happens in the priority loop."""
    from cards.abilities.ability import AbilityKind
    for obj in state.permanents():
        for ab in obj.card.abilities:
            if ab.kind is AbilityKind.TRIGGERED and ab.trigger and isinstance(ev, ab.trigger.event_type):
                if ab.trigger.condition(state, obj, ev):
                    targets = ab.trigger.bind(state, obj, ev) if ab.trigger.bind else ()
                    state.pending_triggers.append((obj.id, obj.controller, ab, targets))
    # TODO: leaves-the-battlefield triggers need last-known information from before the move
