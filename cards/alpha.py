"""Alpha card pool. Start in code; migrate to JSON/YAML + loader once the shape settles."""
from __future__ import annotations
from .card_def import CardDef, CardType as T, Color as C, ManaCost
from .ability import Ability, AbilityKind as K, Cost, TargetSpec
from ..engine.effects import DealDamage, ModifyPT, AddMana, Draw, Destroy

CARDS: dict[str, CardDef] = {}


def register(card: CardDef) -> CardDef:
    CARDS[card.name] = card
    return card


# ---- basic lands ----
for _name, _color in [("Plains", C.WHITE), ("Island", C.BLUE), ("Swamp", C.BLACK),
                      ("Mountain", C.RED), ("Forest", C.GREEN)]:
    register(CardDef(
        name=_name, cost=None, types=frozenset({T.LAND}), subtypes=frozenset({_name}),
        abilities=(Ability(K.MANA, effects=(AddMana(_color, 1),), cost=Cost(tap_self=True)),),
    ))

# ---- spells ----
register(CardDef(
    name="Lightning Bolt", cost=ManaCost(0, (C.RED,)), types=frozenset({T.INSTANT}),
    abilities=(Ability(K.SPELL, effects=(DealDamage(3),), targets=(TargetSpec("any"),)),),
))

register(CardDef(
    name="Giant Growth", cost=ManaCost(0, (C.GREEN,)), types=frozenset({T.INSTANT}),
    abilities=(Ability(K.SPELL, effects=(ModifyPT(3, 3, until_end_of_turn=True),),
                       targets=(TargetSpec("creature"),)),),
))

register(CardDef(
    name="Ancestral Recall", cost=ManaCost(0, (C.BLUE,)), types=frozenset({T.INSTANT}),
    abilities=(Ability(K.SPELL, effects=(Draw(3, target_index=0),), targets=(TargetSpec("player"),)),),
))


def _nonblack_nonartifact(state, caster, obj) -> bool:
    ch = state.characteristics(obj.id)
    return C.BLACK not in ch.colors and T.ARTIFACT not in ch.types


register(CardDef(
    name="Terror", cost=ManaCost(1, (C.BLACK,)), types=frozenset({T.INSTANT}),
    abilities=(Ability(K.SPELL, effects=(Destroy(),),
                       targets=(TargetSpec("creature", legal=_nonblack_nonartifact),)),),
))

# ---- creatures (vanilla / mana) ----
register(CardDef(
    name="Grizzly Bears", cost=ManaCost(1, (C.GREEN,)), types=frozenset({T.CREATURE}),
    subtypes=frozenset({"Bear"}), power=2, toughness=2,
))

register(CardDef(
    name="Hill Giant", cost=ManaCost(3, (C.RED,)), types=frozenset({T.CREATURE}),
    subtypes=frozenset({"Giant"}), power=3, toughness=3,
))

register(CardDef(
    name="Llanowar Elves", cost=ManaCost(0, (C.GREEN,)), types=frozenset({T.CREATURE}),
    subtypes=frozenset({"Elf"}), power=1, toughness=1,
    abilities=(Ability(K.MANA, effects=(AddMana(C.GREEN, 1),), cost=Cost(tap_self=True)),),
))

# TODO: Crusade (STATIC +1/+1 to white creatures), Regeneration, Control Magic, etc.
