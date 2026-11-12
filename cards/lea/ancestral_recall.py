from cards.card_def import CardDef, CardType, Color, ManaCost
from cards.ability import Ability, AbilityKind, TargetSpec
from engine.effects import Draw

class AncestralRecall(CardDef):
    # Card Info
    name = 'Ancestral Recall'
    cost = ManaCost(generic=0, colored=(Color.BLUE,))
    types=frozenset({CardType.INSTANT})
    # Abilities
    abilities=(Ability(
        kind=AbilityKind.SPELL,
        effects=(Draw(count=3, target_index=0),),
        targets=(TargetSpec('player'),)
    ),)
