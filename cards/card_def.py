"""Static, immutable card data. Never mutated at runtime."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
from typing import ClassVar, TYPE_CHECKING

if TYPE_CHECKING:
    from .abilities.ability import Ability


class CardType(Enum):
    LAND = auto()
    CREATURE = auto()
    INSTANT = auto()
    SORCERY = auto()
    ENCHANTMENT = auto()
    ARTIFACT = auto()


class Color(Enum):
    WHITE = "W"
    BLUE = "U"
    BLACK = "B"
    RED = "R"
    GREEN = "G"


@dataclass(frozen=True)
class ManaCost:
    generic: int = 0
    colored: tuple[Color, ...] = ()  # e.g. (Color.RED, Color.RED)

    def __str__(self):
        return f'{self.generic}' + f'{self.colored}'

    @property
    def cmc(self) -> int:
        return self.generic + len(self.colored)


class CardDef:
    name: ClassVar[str]
    cost: ClassVar[ManaCost | None]  # None for lands
    types: ClassVar[frozenset[CardType]]
    subtypes: frozenset[str] = frozenset()
    power: int | None = None
    toughness: int | None = None
    abilities: tuple["Ability", ...] = ()
    colors: frozenset[Color] | None = None  # override; otherwise derived from cost

    @property
    def derived_colors(self) -> frozenset[Color]:
        if self.colors is not None:
            return self.colors
        return frozenset(self.cost.colored) if self.cost else frozenset()
