from cards.card_def import CardDef, CardType, Color
from cards.abilities.ability import Ability, AbilityKind, Cost
from engine.effects import AddMana

class Swamp(CardDef):
    # Card Info
    name = 'Swamp'
    cost = None
    types=frozenset({CardType.LAND})
    subtpyes=frozenset({'Basic', 'Swamp'})
    # Abilities
    abilities=(Ability(
        kind=AbilityKind.MANA,
        effects=(AddMana(Color.BLACK, 1),),
        cost=Cost(tap_self=True)
    ),)
