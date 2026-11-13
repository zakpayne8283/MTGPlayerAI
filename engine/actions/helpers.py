from cards.abilities.ability import Ability, AbilityKind
from engine.stack import target_is_legal
from engine.state import GameState, IllegalAction, Step, Target

MAIN_STEPS = {Step.MAIN1, Step.MAIN2}

# ---------- helpers ----------
def _require_priority(state: GameState, player: int) -> None:
    if state.priority_player != player:
        raise IllegalAction("you don't have priority")


def _sorcery_timing(state: GameState, player: int) -> bool:
    return state.active_player == player and state.step in MAIN_STEPS and not state.stack


def _spell_ability(card) -> Ability | None:
    return next((a for a in card.abilities if a.kind is AbilityKind.SPELL), None)


def legal_targets(state: GameState, spec, caster: int) -> list[Target]:
    cands = [Target("player", p.id) for p in state.players]
    cands += [Target("object", i) for i in state.battlefield]
    return [t for t in cands if target_is_legal(state, spec, t, caster)]


def _check_targets(state: GameState, specs, targets, player: int) -> None:
    if len(targets) != len(specs):
        raise IllegalAction("wrong number of targets")
    for spec, t in zip(specs, targets):
        if not target_is_legal(state, spec, t, player):
            raise IllegalAction("illegal target")