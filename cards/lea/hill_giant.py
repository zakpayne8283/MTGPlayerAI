from cards.card_def import CardDef, CardType, Color, ManaCost

class HillGiant(CardDef):
    # Card Info
    name = 'Hill Giant'
    cost = ManaCost(generic=3, colored=(Color.RED,))
    types = frozenset({CardType.INSTANT})
    subtypes = frozenset({'Giant'})
    power = 3
    toughness = 3
