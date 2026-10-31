import random

from common.card.card import Card
import common.deck.deck_lists as deck_lists

class Deck:

    def __init__(self, deck_color):
        self.cards:list[Card] = self.__deck_selector(deck_color)

    def draw_top_x(self, x) -> list[Card]:
        output:list[Card] = []

        for _ in range(0, x):
            output.append(self.cards.pop(0))

        return output
    
    def shuffle(self):
        random.shuffle(self.cards)

    @staticmethod
    def __deck_selector(deck_color):
        if str.lower(deck_color) == 'white':
            return deck_lists.WHITE_DECK
        
        if str.lower(deck_color) == 'blue':
            return deck_lists.BLUE_DECK