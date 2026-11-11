"""Play a game in the terminal: python -m mtg.play  (you = P0, random bot = P1)"""
from agents.cli import CLIAgent
from agents.random_agent import RandomAgent
from engine.setup import new_game
from engine.turn import run_game

# define decks
# TODO: Deck selections
DECK_A = ["Mountain"] * 17 + ["Lightning Bolt"] * 8 + ["Hill Giant"] * 15
DECK_B = ["Forest"] * 17 + ["Grizzly Bears"] * 10 + ["Llanowar Elves"] * 6 + ["Giant Growth"] * 7

if __name__ == "__main__":
    # new game
    game = new_game([DECK_A, DECK_B], [CLIAgent(), RandomAgent(1)], seed=42)
    winners = run_game(game)
    print("\nWinner:", winners or "draw", "| life:", [player.life for player in game.players])
