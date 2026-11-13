"""Effect primitives (one-shot) and continuous effects (computed on query)."""
from __future__ import annotations
from dataclasses import dataclass, replace
from enum import IntEnum
from typing import Callable, Protocol, TYPE_CHECKING

from cards.card_def import Color
from engine.state import GameState, Characteristics
from engine.events import apply, DamageDealt, CardDrawn, Destroyed

if TYPE_CHECKING:
    from .stack import StackObject


# ---------- one-shot effects ----------
class Effect(Protocol):
    def resolve(self, state: GameState, so: "StackObject") -> None: ...


@dataclass(frozen=True)
class DealDamage:
    amount: int
    target_index: int = 0

    def resolve(self, state, so):
        apply(state, DamageDealt(so.source_id, so.targets[self.target_index], self.amount))


@dataclass(frozen=True)
class Draw:
    count: int = 1
    target_index: int | None = None  # None => the controller draws

    def resolve(self, state, so):
        who = so.controller if self.target_index is None else so.targets[self.target_index].id
        for _ in range(self.count):
            apply(state, CardDrawn(who))


@dataclass(frozen=True)
class Destroy:
    target_index: int = 0

    def resolve(self, state, so):
        apply(state, Destroyed(so.targets[self.target_index].id))


@dataclass(frozen=True)
class AddMana:
    color: Color | None  # None = colorless
    amount: int = 1

    def resolve(self, state, so):
        state.players[so.controller].mana_pool.add(self.color, self.amount)


@dataclass(frozen=True)
class ModifyPT:
    power: int
    toughness: int
    until_end_of_turn: bool = True
    target_index: int = 0

    def resolve(self, state, so):
        tgt = so.targets[self.target_index].id
        state.continuous_effects.append(ContinuousEffect(
            source_id=so.source_id,
            timestamp=state.next_timestamp(),
            layer=Layer.PT_MODIFY,
            applies_to=lambda st, oid, t=tgt: oid == t,
            modify=lambda ch, p=self.power, t=self.toughness: replace(
                ch, power=ch.power + p, toughness=ch.toughness + t),
            duration="end_of_turn" if self.until_end_of_turn else "static",
        ))


# ---------- continuous effects ----------
class Layer(IntEnum):
    """Simplified layer order (rule 613). Expand as needed."""
    CONTROL = 2
    TYPE = 4
    COLOR = 5
    ABILITIES = 6
    PT_SET = 7
    PT_MODIFY = 8  # Crusade, Giant Growth


@dataclass
class ContinuousEffect:
    source_id: int | None
    timestamp: int
    layer: Layer
    applies_to: Callable[[GameState, int], bool]       # (state, affected object id)
    modify: Callable[[Characteristics], Characteristics]
    duration: str = "static"  # "static" (tied to source on battlefield) | "end_of_turn"


def compute_characteristics(state: GameState, obj_id: int) -> Characteristics:
    obj = state.objects[obj_id]
    ch = Characteristics(
        power=obj.card.power, toughness=obj.card.toughness,
        types=obj.card.types, subtypes=obj.card.subtypes,
        colors=obj.card.derived_colors, controller=obj.controller,
        abilities=obj.card.abilities
    )
    # TODO: gather static abilities of battlefield permanents into ContinuousEffects (Crusade etc.)
    # TODO: drop "static" effects whose source left the battlefield; handle dependencies
    active = [e for e in state.continuous_effects if e.applies_to(state, obj_id)]
    for eff in sorted(active, key=lambda e: (e.layer, e.timestamp)):
        ch = eff.modify(ch)
    return ch


def expire_end_of_turn_effects(state: GameState) -> None:
    state.continuous_effects = [e for e in state.continuous_effects if e.duration != "end_of_turn"]
