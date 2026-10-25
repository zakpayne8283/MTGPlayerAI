from functools import wraps

from common.card.card import Card
from common.deck.deck import Deck
from common.game.game_exceptions import GameOverException

def run_check_state_based_actions(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        self.check_state_based_actions()
        return method(self, *args, **kwargs)
    return wrapper

class GameState:
    
    def __init__(self, player_one_lib: Deck, player_two_lib:Deck, player_one_life:int=20, player_two_life:int=20):

        self.game_loser = None

        self.player_one_life:int = player_one_life
        self.player_two_life:int = player_two_life

        self.player_one_library: Deck = player_one_lib
        self.player_two_library: Deck = player_two_lib

        self.player_one_hand: list[Card] = []   # TODO: Make a `Hand` class
        self.player_two_hand: list[Card] = []   # TODO: Make a `Hand` class

        self.active_player:int = 1

    def __str__(self):
        return f'Life: {self.player_one_life}-{self.player_two_life} ||' \
               f'Cards in Hand: {len(self.player_one_hand)}-{len(self.player_two_hand)} ||' \
               f'Cards in Library: {len(self.player_one_library)}-{len(self.player_two_library)}'

    def check_state_based_actions(self):
        if self.player_one_life <= 0:
            self.game_loser = 1
            raise GameOverException('Player One Loses: <= 0 life')
        
        if self.player_two_life <= 0:
            self.game_loser = 2
            raise GameOverException('Player Two Loses: <= 0 life')

    @check_state_based_actions
    def draw_card(self, cards_to_draw=1):
        try:
            if self.active_player == 1:
                self.player_one_hand.extend(self.player_one_library.top_x(cards_to_draw, draw=True))
            else:
                self.player_two_hand.extend(self.player_two_library.top_x(cards_to_draw, draw=True))
        except IndexError:
            if self.active_player == 1:
                self.game_loser = 1
                raise GameOverException('Player One Loses: 0 cards in library')
            
            self.game_loser = 2
            raise GameOverException('Player Two Loses: 0 cards in library')

    def get_available_actions(self):
        pass

    def is_over(self):
        return self.player_one_life < 0 or self.player_two_life < 0
    
    @check_state_based_actions
    def pass_active_player(self):
        if self.active_player == 1:
            self.active_player = 2
        else:
            self.active_player = 1


    
