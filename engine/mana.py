"""Mana pool and cost payment."""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass, field

from ..cards.card_def import Color, ManaCost


@dataclass
class ManaPool:
    mana: Counter = field(default_factory=Counter)  # Color (or None for colorless) -> amount

    def add(self, color: Color | None, amount: int = 1) -> None:
        self.mana[color] += amount

    def total(self) -> int:
        return sum(self.mana.values())

    def can_pay(self, cost: ManaCost) -> bool:
        for c, n in Counter(cost.colored).items():
            if self.mana[c] < n:
                return False
        return self.total() >= cost.cmc

    def pay(self, cost: ManaCost, generic_preference: list[Color | None] | None = None) -> None:
        """Pay colored first, then generic from what remains (agent may specify the order)."""
        assert self.can_pay(cost)
        for c in cost.colored:
            self.mana[c] -= 1
        remaining = cost.generic
        for c in (generic_preference or list(self.mana.keys())):
            take = min(self.mana[c], remaining)
            self.mana[c] -= take
            remaining -= take
        assert remaining == 0

    def empty(self) -> None:
        self.mana.clear()
