from __future__ import annotations

from engine.actions.dispatch import legal_actions
from .base import (Pass, PlayLand, CastSpell, ActivateAbility, PriorityRequest,
                   DeclareAttackersRequest, DeclareBlockersRequest, DiscardRequest)

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.state import GameState


def _name(state: GameState, obj_id:int) -> str:
    """
    Generates a friendly name from the state given an object id 
    
    :param state: GameState object for current game
    :param obj_id: int of GameObject to look up
    :return: `CardName (#obj_id)` formatted card name
    :rtype: str
    """
    return f'{state.objects[obj_id].card.name} (#{obj_id})'


def _ask(prompt: str) -> str:
    """
    Asks for which action to take
    
    :param prompt: String to prompt user
    :type prompt: str
    :return: User response
    :rtype: str
    """

    try:
        return input(prompt).strip()
    except EOFError:
        return ""


def _pick_many(prompt: str, options: list[int], state) -> list[int]:
    for i, oid in enumerate(options):
        print(f"  {i}: {_name(state, oid)}")
    raw = _ask(f"{prompt} (space-separated numbers, blank = none): ")
    return [options[int(x)] for x in raw.split() if x.isdigit() and int(x) < len(options)]


class CLIAgent:
    """Human at a terminal."""

    def describe(self, state, a) -> str:
        if isinstance(a, PlayLand):
            return f"Play {_name(state, a.obj_id)}"
        if isinstance(a, CastSpell):
            tg = ", ".join(f"{t.kind} {t.id}" for t in a.targets)
            return f"Cast {_name(state, a.obj_id)}" + (f" -> {tg}" if tg else "")
        if isinstance(a, ActivateAbility):
            return f"Activate {_name(state, a.source_id)} [{a.ability_index}]"
        return str(a)

    def show(self, state, p: int) -> None:
        me, opp = state.players[p], state.players[1 - p]
        print(f"\n=== Turn {state.turn} / {state.step.name} (active: P{state.active_player}) ===")
        print(f"You: {me.life} life | Opp: {opp.life} life, {len(opp.hand)} cards in hand")
        bf = lambda pl: ", ".join(
            _name(state, i) + ("(T)" if state.objects[i].tapped else "")
            for i in state.battlefield if state.objects[i].controller == pl) or "-"
        print(f"Opp battlefield: {bf(1 - p)}\nYour battlefield: {bf(p)}")
        print("Your hand: " + (", ".join(_name(state, i) for i in me.hand) or "-"))
        if state.stack:
            print("Stack (top last): " + ", ".join(_name(state, s.source_id) for s in state.stack
                                                  if s.source_id in state.objects))

    def choose(self, request):
        s, p = request.state, request.player
        if isinstance(request, PriorityRequest):
            self.show(s, p)
            acts = legal_actions(s, p)
            print("0: Pass")
            for i, a in enumerate(acts, 1):
                print(f"{i}: {self.describe(s, a)}")
            raw = _ask("> ")
            return acts[int(raw) - 1] if raw.isdigit() and 0 < int(raw) <= len(acts) else Pass()
        if isinstance(request, DeclareAttackersRequest):
            self.show(s, p)
            return _pick_many("Attackers", request.legal_attackers, s)
        if isinstance(request, DeclareBlockersRequest):
            self.show(s, p)
            print("Attacking: " + ", ".join(_name(s, a) for a in request.attackers))
            out = {}
            for b in request.legal_blockers:
                raw = _ask(f"Block with {_name(s, b)}? attacker number (blank = no): ")
                if raw.isdigit() and int(raw) < len(request.attackers):
                    out[b] = request.attackers[int(raw)]
            return out
        if isinstance(request, DiscardRequest):
            self.show(s, p)
            return _pick_many(f"Discard {request.count}", s.players[p].hand, s)[:request.count]
        raise NotImplementedError(type(request))


class ScriptedAgent:
    """For tests: feed a fixed list of responses in order; Pass / empty answers when exhausted."""

    def __init__(self, script: list):
        self.script = list(script)

    def choose(self, request):
        if isinstance(request, PriorityRequest):
            return self.script.pop(0) if self.script else Pass()
        if isinstance(request, DeclareAttackersRequest):
            return self.script.pop(0) if self.script else []
        if isinstance(request, DeclareBlockersRequest):
            return self.script.pop(0) if self.script else {}
        raise NotImplementedError(type(request))
