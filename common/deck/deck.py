from common.card.card import Card

class Deck:

    def __init__(self):
        self.cards:list[Card] = []

    def top_x(self, x, draw=False) -> list[Card]:
        pass