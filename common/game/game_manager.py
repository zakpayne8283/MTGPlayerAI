from common.deck.deck import Deck
from common.game.game_state import GameState

class GameManager:

    def __init__(self, player_one_deck: Deck, player_two_deck: Deck):
        self.player_one_deck:Deck = player_one_deck
        self.player_two_deck:Deck = player_two_deck

        self.game_state = GameState(player_one_deck, player_two_deck)

    def initialize_game(self):
        # shuffle both decks
        self.player_one_deck.shuffle()
        self.player_two_deck.shuffle()

        # always starts with player one
        # draw opening hand
        self.game_state.draw_card(7)

        # switch to player two
        self.game_state.pass_active_player()
        # draw opening hand
        self.game_state.draw_card(7)

        # switch back to player one
        self.game_state.pass_active_player()

        print('-'*5, 'GAME INITIALIZED', '-'*5)
        print(self.game_state)
    
    def run_game(self):
        
        # as long as the game isn't over, continue playing
        while not self.game_state.is_over():
            
            available_actions = self.game_state.get_available_actions()