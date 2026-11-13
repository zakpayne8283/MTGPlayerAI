from cards.card_def import CardDef, CardType, Color
from cards.abilities.ability import Ability, AbilityKind, Cost
from engine.effects import AddMana

class Plains(CardDef):
    # Card Info
    name = 'Plains'
    cost = None
    types=frozenset({CardType.LAND})
    subtpyes=frozenset({'Basic', 'Plains'})
    # Abilities
    abilities=(Ability(
        kind=AbilityKind.MANA,
        effects=(AddMana(Color.WHITE, 1),),
        cost=Cost(tap_self=True)
    ),)
