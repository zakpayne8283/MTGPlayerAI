from cards.card_def import CardDef

from cards.card_sets import lea as LEA

CARDS: dict[str, CardDef] = {}


def register(card: CardDef) -> CardDef:
    CARDS[card.name] = card
    return card

# basic lands
register(LEA.Plains())
register(LEA.Island())
register(LEA.Swamp())
register(LEA.Mountain())
register(LEA.Forest())

# ---- spells ----
register(LEA.AirElemental())
register(LEA.AnkhOfMishra())
register(LEA.AncestralRecall())
register(LEA.GiantGrowth())
register(LEA.GrizzlyBears())
register(LEA.HillGiant())
register(LEA.LightningBolt())
register(LEA.LlanowarElves())
register(LEA.Terror())
