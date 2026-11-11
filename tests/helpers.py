from mtg.agents.random_agent import RandomAgent
from mtg.engine.mana import ManaPool
from mtg.engine.state import GameState, Player, Zone, Step


def make_game(turn=1, step=Step.MAIN1) -> GameState:
    """Bare two-player state, player 0 active with priority."""
    g = GameState(players=[Player(0, mana_pool=ManaPool()), Player(1, mana_pool=ManaPool())])
    g.turn, g.step, g.active_player, g.priority_player = turn, step, 0, 0
    return g


def put(g, card, zone, owner=0):
    from mtg.cards.alpha import CARDS
    obj = g.create_object(CARDS[card], owner, zone)
    obj.entered_turn = 0  # pretend it's been there a while (not summoning sick)
    return obj


BOLT_DECK = ["Mountain"] * 20 + ["Lightning Bolt"] * 20
GREEN_DECK = ["Forest"] * 17 + ["Grizzly Bears"] * 10 + ["Llanowar Elves"] * 6 + ["Giant Growth"] * 7
BLACK_DECK = ["Swamp"] * 17 + ["Terror"] * 8 + ["Hill Giant"] * 0 + ["Grizzly Bears"] * 15
BLUE_DECK = ["Island"] * 17 + ["Ancestral Recall"] * 4 + ["Lightning Bolt"] * 0 + ["Hill Giant"] * 0 + ["Island"] * 19
