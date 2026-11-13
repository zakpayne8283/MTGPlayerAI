from dataclasses import dataclass, field
from typing import Callable

from cards.abilities.ability import Ability, AbilityKind

@dataclass(frozen=True)
class CombatAbility(Ability):
    kind: AbilityKind = AbilityKind.STATIC
    # (this creature's chars, a would-be blocker's chars) -> may it block?
    can_be_blocked_by: Callable[["Characteristics", "Characteristics"], bool] | None = field(default=None, compare=False)