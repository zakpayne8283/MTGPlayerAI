"""Stack objects, casting, and resolution."""
from __future__ import annotations
from dataclasses import dataclass

from ..cards.ability import Ability, AbilityKind, TargetSpec
from ..cards.card_def import CardType
from .state import GameState, Zone, Target, IllegalAction
from .events import apply, ZoneChange, SpellCast, TapChanged


@dataclass
class StackObject:
    id: int
    source_id: int            # card/permanent that produced this
    controller: int
    ability: Ability | None   # None => permanent spell
    targets: tuple[Target, ...] = ()
    is_spell: bool = False    # True for cast spells (counterable), False for abilities


def target_is_legal(state: GameState, spec: TargetSpec, target: Target, caster: int) -> bool:
    if target.kind == "player":
        return spec.kind in ("player", "any") and 0 <= target.id < len(state.players)
    obj = state.objects.get(target.id)
    if obj is None or obj.zone is not Zone.BATTLEFIELD:
        return False
    if spec.kind == "permanent":
        ok = True
    elif spec.kind in ("creature", "any"):
        ok = CardType.CREATURE in state.characteristics(obj.id).types
    else:
        ok = False
    return ok and (spec.legal is None or spec.legal(state, caster, obj))


def cast_spell(state: GameState, player: int, card_obj_id: int, targets: tuple[Target, ...]) -> None:
    """Raw: move the card to the stack. Use actions.cast() for validation and mana payment."""
    new = state.move(card_obj_id, Zone.STACK)
    ability = next((a for a in new.card.abilities if a.kind is AbilityKind.SPELL), None)
    so = StackObject(new.id, new.id, player, ability, tuple(targets), is_spell=True)
    state.stack.append(so)
    apply(state, SpellCast(so.id, player))


def resolve_mana_ability(state: GameState, player: int, source_id: int, ability: Ability) -> None:
    """Mana abilities skip the stack: pay the tap cost, run effects immediately."""
    obj = state.objects[source_id]
    if ability.cost and ability.cost.tap_self:
        if obj.tapped:
            raise IllegalAction("already tapped")
        apply(state, TapChanged(source_id, True))
    so = StackObject(-1, source_id, player, ability)
    for eff in ability.effects:
        eff.resolve(state, so)


def targets_still_legal(state: GameState, so: StackObject) -> bool:
    """If the spell has targets and ALL are now illegal, it fizzles. Partial legality still resolves."""
    specs = so.ability.targets if so.ability else ()
    if not specs:
        return True
    return any(target_is_legal(state, spec, t, so.controller) for spec, t in zip(specs, so.targets))


def resolve_top(state: GameState) -> None:
    so = state.stack.pop()
    if so.ability is not None and not targets_still_legal(state, so):
        _cleanup_spell(state, so)  # fizzle
        return
    if so.ability is None:
        apply(state, ZoneChange(so.source_id, Zone.STACK, Zone.BATTLEFIELD, controller=so.controller))
        return
    for eff in so.ability.effects:
        eff.resolve(state, so)
    if so.ability.custom:
        so.ability.custom(state, so)
    _cleanup_spell(state, so)


def _cleanup_spell(state: GameState, so: StackObject) -> None:
    if so.is_spell and so.source_id in state.objects:
        apply(state, ZoneChange(so.source_id, Zone.STACK, Zone.GRAVEYARD))
