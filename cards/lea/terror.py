from typing import TYPE_CHECKING

from cards.card_def import CardDef, CardType, Color, ManaCost
from cards.ability import Ability, AbilityKind, TargetSpec
from engine.effects import Destroy

if TYPE_CHECKING:
    from engine.state import GameObject, GameState

# TODO: Move this to some other unified area for legality checking
def _nonblack_nonartifact(state: GameState, caster, obj: GameObject) -> bool:
        ch = state.characteristics(obj.id)
        return Color.BLACK not in ch.colors and CardType.ARTIFACT not in ch.types

class Terror(CardDef):
    # Card Info
    name = 'Terror'
    cost = ManaCost(generic=1, colored=(Color.BLACK,))
    types=frozenset({CardType.INSTANT})
    # Abilities
    abilities=(Ability(
        kind=AbilityKind.SPELL,
        effects=(Destroy(),),
        targets=(TargetSpec('creature', legal=_nonblack_nonartifact),)
    ),)



