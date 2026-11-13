from cards.card_def import CardDef, CardType, Color, ManaCost

class GrizzlyBears(CardDef):
    # Card Info
    name = 'Grizzly Bears'
    cost = ManaCost(generic=1, colored=(Color.GREEN,))
    types = frozenset({CardType.CREATURE})
    subtypes = frozenset({'Bear'})
    power = 2
    toughness = 2
