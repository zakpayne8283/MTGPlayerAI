from cards.card_def import CardDef, CardType, Color
from cards.abilities.ability import Ability, AbilityKind, Cost
from engine.effects import AddMana

class Forest(CardDef):
    # Card Info
    name = 'Forest'
    cost = None
    types=frozenset({CardType.LAND})
    subtpyes=frozenset({'Basic', 'Forest'})
    # Abilities
    abilities=(Ability(
        kind=AbilityKind.MANA,
        effects=(AddMana(Color.GREEN, 1),),
        cost=Cost(tap_self=True)
    ),)
