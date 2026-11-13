from cards.card_def import CardDef, CardType, Color
from cards.abilities.ability import Ability, AbilityKind, Cost
from engine.effects import AddMana

class Mountain(CardDef):
    # Card Info
    name = 'Mountain'
    cost = None
    types=frozenset({CardType.LAND})
    subtpyes=frozenset({'Basic', 'Mountain'})
    # Abilities
    abilities=(Ability(
        kind=AbilityKind.MANA,
        effects=(AddMana(Color.RED, 1),),
        cost=Cost(tap_self=True)
    ),)