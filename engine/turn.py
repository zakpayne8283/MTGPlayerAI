"""Turn structure and the priority loop."""
from __future__ import annotations

from agents.base import (PriorityRequest, Pass, DeclareAttackersRequest,
                           DeclareBlockersRequest, DiscardRequest)
from . import combat as combat_mod
from engine.actions import perform
from engine.combat import CombatState
from engine.effects import expire_end_of_turn_effects
from engine.events import apply, CardDrawn, TapChanged, ZoneChange
from engine.sba import check_sbas, GameOver
from engine.stack import resolve_top
from engine.state import GameState, Step, Target, Zone, IllegalAction

STEP_ORDER = list(Step)
NO_PRIORITY = {Step.UNTAP, Step.CLEANUP}
MAX_HAND = 7


def run_game(state: GameState, max_turns: int = 200) -> list[int]:
    """Run until someone wins. Returns winner ids ([] = draw or turn cap hit)."""
    try:
        while state.turn < max_turns:
            run_turn(state)
            state.active_player = (state.active_player + 1) % len(state.players)
    except GameOver as g:
        return g.winners
    return []


def run_turn(state: GameState) -> None:
    state.turn += 1
    state.combat = None
    state.players[state.active_player].lands_played = 0
    for step in STEP_ORDER:
        state.step = step
        has_attackers = state.combat is not None and bool(state.combat.attackers)
        if step in (Step.DECLARE_BLOCKERS, Step.COMBAT_DAMAGE) and not has_attackers:
            continue
        _turn_based_actions(state, step)
        if step is Step.DECLARE_ATTACKERS and not (state.combat and state.combat.attackers):
            continue  # no attackers declared: step is skipped
        if step not in NO_PRIORITY:
            priority_loop(state)
        if step is Step.END_COMBAT:
            state.combat = None
        for p in state.players:
            p.mana_pool.empty()  # pools empty at the end of each step


def _turn_based_actions(state: GameState, step: Step) -> None:
    ap = state.active_player
    if step is Step.UNTAP:
        for o in state.permanents():
            if o.controller == ap:
                apply(state, TapChanged(o.id, False))
    elif step is Step.DRAW:
        if state.turn > 1:  # TODO: proper first-player draw skip for >2 players
            apply(state, CardDrawn(ap))
    elif step is Step.DECLARE_ATTACKERS:
        _declare_attackers(state)
    elif step is Step.DECLARE_BLOCKERS:
        _declare_blockers(state)
    elif step is Step.COMBAT_DAMAGE:
        combat_mod.deal_combat_damage(state, state.combat)
    elif step is Step.CLEANUP:
        _cleanup(state)


def _declare_attackers(state: GameState) -> None:
    ap = state.active_player
    state.combat = CombatState()
    legal = combat_mod.legal_attackers(state, ap)
    if not legal:
        return
    chosen = state.players[ap].agent.choose(DeclareAttackersRequest(state, ap, legal))
    if chosen:
        defender = Target("player", (ap + 1) % len(state.players))  # TODO: multiplayer defender choice
        combat_mod.declare_attackers(state, state.combat, ap, list(chosen), defender)


def _declare_blockers(state: GameState) -> None:
    combat = state.combat
    for d in sorted({t.id for t in combat.attackers.values()}):
        legal = combat_mod.legal_blockers(state, d)
        if not legal:
            continue
        attackers = [a for a, t in combat.attackers.items() if t.id == d]
        assignment = state.players[d].agent.choose(DeclareBlockersRequest(state, d, legal, attackers))
        combat_mod.declare_blockers(state, combat, d, assignment or {})


def _cleanup(state: GameState) -> None:
    ap = state.active_player
    p = state.players[ap]
    excess = len(p.hand) - MAX_HAND
    if excess > 0:
        chosen = p.agent.choose(DiscardRequest(state, ap, excess))
        if len(set(chosen)) != excess or not set(chosen) <= set(p.hand):
            raise IllegalAction("invalid discard")
        for oid in chosen:
            apply(state, ZoneChange(oid, Zone.HAND, Zone.GRAVEYARD))
    for o in state.permanents():
        o.damage = 0
    expire_end_of_turn_effects(state)  # TODO: if this triggers anything, players get priority again


def priority_loop(state: GameState) -> None:
    passes = 0
    state.priority_player = state.active_player
    while True:
        check_sbas(state)
        _push_pending_triggers(state)
        player = state.players[state.priority_player]
        action = player.agent.choose(PriorityRequest(state, player.id))

        if isinstance(action, Pass):
            passes += 1
            if passes == len(state.players):
                if not state.stack:
                    return
                resolve_top(state)
                passes = 0
                state.priority_player = state.active_player
            else:
                state.priority_player = (state.priority_player + 1) % len(state.players)
        else:
            perform(state, player.id, action)  # raises IllegalAction on bad input
            passes = 0  # acting player keeps priority


def _push_pending_triggers(state: GameState) -> None:
    # TODO: APNAP ordering; controller orders own triggers; choose targets on placement
    state.pending_triggers.clear()
