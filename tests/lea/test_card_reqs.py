from cards.card_def import ManaCost
from cards.alpha import CARDS


def test_cards_created_correctly():

    for key, card in CARDS.items():
        # name required
        assert card.name != None, f'Card missing name - {key}'
        assert card.name != '', f'Card missing name - {key}'

        # cost required
        if card.cost != None:
            # must be ManaCost
            assert isinstance(card.cost, ManaCost), f'Card missing ManaCost - {card.name}'
            # colored must be tuple
            assert isinstance(card.cost.colored, tuple), f'Card colored mana not tuple - {card.name}'
        
        # needs at least one type
        assert isinstance(card.types, frozenset), f'Card types aren\'t a frozenset - {card.name}'
        assert len(card.types) > 0, f'Card has no type - {card.name}'

        # ability requirements
        if card.abilities != None:
            # abilities must be tuples
            assert isinstance(card.abilities, tuple), f'Card abilities are not a tuple - {card.name}'

            for ab in card.abilities:
                # must have ability type
                assert ab.kind != None
                # must have effect
                assert isinstance(ab.effects, tuple), f'Card ability effects not a tuple - {card.name}'
                # if there are targets must be a tuple
                if ab.targets != None:
                    assert isinstance(ab.targets, tuple), f'Card ability targets not a tuple - {card.name}'
