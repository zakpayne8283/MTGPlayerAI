from cards.card_def import CardDef, CardType, Color, ManaCost
from cards.abilities.ability import Ability, AbilityKind
from cards.abilities.keywords.flying import FLYING

class AirElemental(CardDef):
    # Card Info
    name = 'Air Elemental'
    cost = ManaCost(generic=3, colored=(Color.BLUE, Color.BLUE))
    types = frozenset({CardType.CREATURE})
    subtypes = frozenset({'Elemental'})
    power = 4
    toughness = 4
    abilities = (FLYING,)
