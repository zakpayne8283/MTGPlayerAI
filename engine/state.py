"""Game state. Plain data + small helpers; rules logic lives in other modules."""
from __future__ import annotations
import copy
import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

from cards.card_def import CardDef, CardType, Color

if TYPE_CHECKING:
    from engine.combat import CombatState
    from engine.stack import StackObject
    from engine.mana import ManaPool
    from engine.effects import ContinuousEffect
    from engine.events import Event
    from agents.base import Agent
    from cards.abilities.ability import Ability


class IllegalAction(Exception):
    """Raised when a requested game action isn't legal. Validators raise it before any mutation."""


class Zone(Enum):
    LIBRARY = auto()
    HAND = auto()
    BATTLEFIELD = auto()
    GRAVEYARD = auto()
    STACK = auto()
    EXILE = auto()


class Step(Enum):
    UNTAP = auto()
    UPKEEP = auto()
    DRAW = auto()
    MAIN1 = auto()
    BEGIN_COMBAT = auto()
    DECLARE_ATTACKERS = auto()
    DECLARE_BLOCKERS = auto()
    COMBAT_DAMAGE = auto()
    END_COMBAT = auto()
    MAIN2 = auto()
    END = auto()
    CLEANUP = auto()


@dataclass(frozen=True)
class Target:
    kind: str  # "object" | "player"
    id: int


@dataclass
class GameObject:
    """A runtime card/permanent/spell. A zone change creates a NEW object (new id)."""
    id: int
    card: CardDef
    owner: int
    controller: int
    zone: Zone
    timestamp: int
    damage: int = 0
    tapped: bool = False
    entered_turn: int = 0  # for summoning sickness
    counters: dict[str, int] = field(default_factory=dict)
    attached_to: int | None = None  # auras/equipment


@dataclass
class Characteristics:
    """Computed on query from base card + continuous effects. Never stored."""
    power: int | None
    toughness: int | None
    types: frozenset[CardType]
    subtypes: frozenset[str]
    colors: frozenset[Color]
    controller: int
    keywords: frozenset[str] = frozenset()

    abilities: tuple[Ability, ...] = ()

    def has(self, ability: Ability) -> bool:
        return ability in self.abilities


@dataclass
class Player:
    id: int
    agent: "Agent | None" = None
    life: int = 20
    library: list[int] = field(default_factory=list)  # top = index 0
    hand: list[int] = field(default_factory=list)
    graveyard: list[int] = field(default_factory=list)
    exile: list[int] = field(default_factory=list)
    mana_pool: "ManaPool | None" = None
    lands_played: int = 0
    drew_from_empty: bool = False


@dataclass
class GameState:
    players: list[Player]
    rng: random.Random = field(default_factory=lambda: random.Random(0))
    objects: dict[int, GameObject] = field(default_factory=dict)
    battlefield: list[int] = field(default_factory=list)   # object ids
    stack_cards: list[int] = field(default_factory=list)   # object ids of spells on the stack
    stack: list["StackObject"] = field(default_factory=list)  # resolution order, top = end
    continuous_effects: list["ContinuousEffect"] = field(default_factory=list)
    pending_triggers: list = field(default_factory=list)
    log: list["Event"] = field(default_factory=list)
    turn: int = 0
    active_player: int = 0
    priority_player: int = 0
    step: Step = Step.UNTAP
    combat: "CombatState | None" = None
    _next_id: int = 1
    _next_ts: int = 1

    # ---- ids / timestamps ----
    def next_id(self) -> int:
        self._next_id += 1
        return self._next_id - 1

    def next_timestamp(self) -> int:
        self._next_ts += 1
        return self._next_ts - 1

    # ---- object creation / zones ----
    def create_object(self, card: CardDef, owner: int, zone: Zone) -> GameObject:
        obj = GameObject(self.next_id(), card, owner, owner, zone, self.next_timestamp(),
                         entered_turn=self.turn)
        self.objects[obj.id] = obj
        self.zone_list(zone, owner).append(obj.id)
        return obj

    def zone_list(self, zone: Zone, owner: int) -> list[int]:
        if zone is Zone.BATTLEFIELD:
            return self.battlefield
        if zone is Zone.STACK:
            return self.stack_cards
        return getattr(self.players[owner], zone.name.lower())

    def move(self, obj_id: int, to: Zone, controller: int | None = None) -> GameObject:
        """Low-level zone change: removes old object, returns a NEW object. Call via ZoneChange event."""
        old = self.objects.pop(obj_id)
        self.zone_list(old.zone, old.owner).remove(obj_id)
        new = self.create_object(old.card, old.owner, to)
        if controller is not None:
            new.controller = controller
        return new

    # ---- queries ----
    def permanents(self) -> list[GameObject]:
        return [self.objects[i] for i in self.battlefield]

    def last_own_turn(self, player: int) -> int:
        """Most recent turn number started by `player` (assumes player 0 goes first, turns rotate)."""
        n = len(self.players)
        for t in range(self.turn, 0, -1):
            if (t - 1) % n == player:
                return t
        return 0

    def summoning_sick(self, obj: GameObject) -> bool:
        """True if the controller hasn't controlled it continuously since their most recent turn began."""
        return obj.entered_turn >= self.last_own_turn(obj.controller)

    def characteristics(self, obj_id: int) -> Characteristics:
        from .effects import compute_characteristics  # lazy: avoid import cycle
        return compute_characteristics(self, obj_id)

    def clone(self) -> "GameState":
        """Deepcopy for AI search/tests; agents are shared, not copied. Optimize later."""
        agents = [p.agent for p in self.players]
        for p in self.players:
            p.agent = None
        c = copy.deepcopy(self)
        for p, a in zip(self.players, agents):
            p.agent = a
        for p, a in zip(c.players, agents):
            p.agent = a
        return c
