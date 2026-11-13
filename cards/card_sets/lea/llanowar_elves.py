from cards.card_def import CardDef, CardType, Color, ManaCost
from cards.abilities.ability import Ability, AbilityKind, Cost
from engine.effects import AddMana

class LlanowarElves(CardDef):
    # Card Info
    name = 'Llanowar Elves'
    cost = ManaCost(generic=0, colored=(Color.GREEN,))
    types=frozenset({CardType.CREATURE})
    subtypes = frozenset({'Elf'})
    power = 1
    toughness = 1
    # Abilities
    abilities=(Ability(
        kind=AbilityKind.MANA,
        effects=(AddMana(Color.GREEN, 1),),
        cost=Cost(tap_self=True)
    ),)
