from cards.card_def import CardDef, CardType, Color, ManaCost
from cards.ability import Ability, AbilityKind, TargetSpec
from engine.effects import DealDamage

class LightningBolt(CardDef):
    # Card Info
    name = 'Lightning Bolt'
    cost = ManaCost(generic=0, colored=(Color.RED,))
    types=frozenset({CardType.INSTANT})
    # Abilities
    abilities=(Ability(
        kind=AbilityKind.SPELL,
        effects=(DealDamage(3),),
        targets=(TargetSpec('any'),)
    ),)
