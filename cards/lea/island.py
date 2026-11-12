from cards.card_def import CardDef, CardType, Color
from cards.ability import Ability, AbilityKind, Cost
from engine.effects import AddMana

class Island(CardDef):
    # Card Info
    name = 'Island'
    cost = None
    types=frozenset({CardType.LAND})
    subtpyes=frozenset({'Basic', 'Island'})
    # Abilities
    abilities=(Ability(
        kind=AbilityKind.MANA,
        effects=(AddMana(Color.BLUE, 1),),
        cost=Cost(tap_self=True)
    ),)
