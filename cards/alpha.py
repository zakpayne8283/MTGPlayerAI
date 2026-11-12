"""Alpha card pool. Start in code; migrate to JSON/YAML + loader once the shape settles."""
from __future__ import annotations
from cards.card_def import CardDef, CardType as T, Color as C, ManaCost
from cards.ability import Ability, AbilityKind as K, Cost, TargetSpec
from engine.effects import DealDamage, ModifyPT, AddMana, Draw, Destroy

from cards import lea as LEA

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
register(LEA.AncestralRecall())
register(LEA.GiantGrowth())
register(LEA.GrizzlyBears())
register(LEA.HillGiant())
register(LEA.LightningBolt())
register(LEA.LlanowarElves())
register(LEA.Terror())
