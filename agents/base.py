"""Decision interface. The engine only talks to agents through choose()."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, Any

from ..engine.state import GameState, Target


# ---- Requests (engine -> agent) ----
@dataclass
class PriorityRequest:
    state: GameState
    player: int
    # respond with: Pass | PlayLand | CastSpell | ActivateAbility
    # (see engine.actions.legal_actions for the legal set)


@dataclass
class DeclareAttackersRequest:
    state: GameState
    player: int
    legal_attackers: list[int]
    # respond with: list[int] of attacker object ids (empty = no attack)


@dataclass
class DeclareBlockersRequest:
    state: GameState
    player: int
    legal_blockers: list[int]
    attackers: list[int]
    # respond with: dict[blocker_id, attacker_id]


@dataclass
class DiscardRequest:
    state: GameState
    player: int
    count: int
    # respond with: list[int] of `count` hand object ids


# ---- Responses (agent -> engine) ----
@dataclass
class Pass:
    pass


@dataclass
class PlayLand:
    obj_id: int


@dataclass
class CastSpell:
    obj_id: int
    targets: tuple[Target, ...] = ()


@dataclass
class ActivateAbility:
    source_id: int
    ability_index: int
    targets: tuple[Target, ...] = ()


class Agent(Protocol):
    def choose(self, request: Any) -> Any: ...
