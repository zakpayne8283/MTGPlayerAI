"""Ability definitions: declarative data that references effect primitives."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable, TYPE_CHECKING

from .card_def import ManaCost

if TYPE_CHECKING:
    from engine.effects import Effect
    from engine.state import GameState, GameObject
    from engine.events import Event


class AbilityKind(Enum):
    SPELL = auto()      # instant/sorcery text, or an aura's on-cast effect
    ACTIVATED = auto()
    MANA = auto()       # activated, but skips the stack
    TRIGGERED = auto()
    STATIC = auto()


@dataclass(frozen=True)
class TargetSpec:
    """What a target must be. `legal` is re-checked on resolution (fizzling)."""
    kind: str  # "creature" | "player" | "any" | "permanent" | ...
    legal: Callable[["GameState", int, "GameObject"], bool] | None = None


@dataclass(frozen=True)
class Cost:
    mana: ManaCost | None = None
    tap_self: bool = False
    sacrifice_self: bool = False


@dataclass(frozen=True)
class Trigger:
    event_type: type
    condition: Callable[["GameState", "GameObject", "Event"], bool]  # (state, source, event)


@dataclass(frozen=True)
class Ability:
    kind: AbilityKind
    effects: tuple["Effect", ...] = ()
    cost: Cost | None = None
    targets: tuple[TargetSpec, ...] = ()
    trigger: Trigger | None = None
    static_effects: tuple["Effect", ...] = ()  # STATIC: active while source is on battlefield
    # Escape hatch for oddball cards: arbitrary callable run on resolution
    custom: Callable[["GameState", object], None] | None = None
