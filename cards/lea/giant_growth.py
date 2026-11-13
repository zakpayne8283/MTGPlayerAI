from cards.card_def import CardDef, CardType, Color, ManaCost
from cards.abilities.ability import Ability, AbilityKind, TargetSpec
from engine.effects import ModifyPT

class GiantGrowth(CardDef):
    # Card Info
    name = 'Giant Growth'
    cost = ManaCost(generic=0, colored=(Color.GREEN,))
    types=frozenset({CardType.INSTANT})
    # Abilities
    abilities=(Ability(
        kind=AbilityKind.SPELL,
        effects=(ModifyPT(power=3, toughness=3, until_end_of_turn=True),),
        targets=(TargetSpec('creature'),)
    ),)
