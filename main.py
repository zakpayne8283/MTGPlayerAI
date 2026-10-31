from common.deck.deck import Deck
from common.game.game_manager import GameManager

def main():
    # pull the decks
    player_one_deck:Deck = Deck('white')
    player_two_deck:Deck = Deck('blue')

    # setup the game
    gm = GameManager(player_one_deck, player_two_deck)
    gm.initialize_game()

if __name__ == '__main__':
    main()