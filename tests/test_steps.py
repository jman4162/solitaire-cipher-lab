"""Each of the five transformations, tested on its own.

The edge cases here -- jokers wrapping past the bottom, adjacent jokers, a joker
as the bottom card -- are where implementations of Solitaire actually break, and
none of them is caught by an encrypt-then-decrypt round trip.
"""

import pytest

from helpers import deck_with_jokers_at, random_decks
from solitaire_lab.cards import Card, Joker
from solitaire_lab.deck import ORDERED_DECK, format_deck, parse_deck, validate_deck
from solitaire_lab.steps import count_cut, move_joker_a, move_joker_b, output_card, triple_cut

JA = Card.the_joker(Joker.A)
JB = Card.the_joker(Joker.B)


class TestMoveJokers:
    def test_joker_a_moves_down_one(self):
        deck = deck_with_jokers_at(10, 40)
        result = move_joker_a(deck)
        assert result.deck.index(JA) == 11
        assert result.metadata["from_index"] == 10
        assert result.metadata["wrapped"] is False

    def test_joker_b_moves_down_two(self):
        deck = deck_with_jokers_at(10, 40)
        result = move_joker_b(deck)
        assert result.deck.index(JB) == 42

    def test_joker_a_at_bottom_wraps_to_second_from_top(self):
        """A joker on the bottom goes *below the top card*, not to the top."""
        deck = deck_with_jokers_at(53, 20)
        result = move_joker_a(deck)
        assert result.deck.index(JA) == 1
        assert result.metadata["wrapped"] is True

    def test_wrap_rule_makes_the_step_non_invertible(self):
        """Crowley (1999): a joker on top and a joker on the bottom land in the same place.

        Same card order apart from the joker, so two distinct decks step to one
        deck. The explainer's section 6 cites this; the test keeps it true.
        """
        rest = [c for c in ORDERED_DECK if c != JA]
        on_top = validate_deck([JA, *rest])
        on_bottom = validate_deck([*rest, JA])
        assert on_top != on_bottom
        assert move_joker_a(on_top).deck == move_joker_a(on_bottom).deck

    def test_joker_b_at_bottom_ends_third_from_top(self):
        """Moving down two from the bottom is two single moves: bottom -> 1 -> 2."""
        deck = deck_with_jokers_at(20, 53)
        result = move_joker_b(deck)
        assert result.deck.index(JB) == 2

    def test_joker_b_second_from_bottom_ends_second_from_top(self):
        deck = deck_with_jokers_at(20, 52)
        result = move_joker_b(deck)
        assert result.deck.index(JB) == 1

    def test_joker_at_top_moves_normally(self):
        deck = deck_with_jokers_at(0, 30)
        assert move_joker_a(deck).deck.index(JA) == 1

    @pytest.mark.parametrize("deck", list(random_decks(40)))
    def test_moves_preserve_all_cards(self, deck):
        for step in (move_joker_a, move_joker_b):
            validate_deck(step(deck).deck)


class TestTripleCut:
    def test_swaps_outer_segments(self):
        deck = deck_with_jokers_at(2, 50)
        result = triple_cut(deck)
        assert result.deck.index(JA) == 3
        assert result.deck.index(JB) == 51
        assert result.deck[:3] == deck[51:]
        assert result.deck[52:] == deck[:2]

    def test_jokers_at_both_ends_is_identity(self):
        deck = deck_with_jokers_at(0, 53)
        assert triple_cut(deck).deck == deck

    def test_adjacent_jokers(self):
        deck = deck_with_jokers_at(20, 21)
        result = triple_cut(deck)
        assert result.deck.index(JA) == 32
        assert result.deck.index(JB) == 33

    def test_works_regardless_of_joker_order(self):
        """The rule is about the topmost and bottommost joker, not A before B."""
        deck = deck_with_jokers_at(40, 5)
        result = triple_cut(deck)
        assert result.metadata["first_joker_index"] == 5
        assert result.metadata["second_joker_index"] == 40

    @pytest.mark.parametrize("deck", list(random_decks(40)))
    def test_preserves_all_cards(self, deck):
        validate_deck(triple_cut(deck).deck)


class TestCountCut:
    def test_bottom_card_never_moves(self):
        for deck in random_decks(30):
            assert count_cut(deck).deck[-1] == deck[-1]

    def test_moves_count_cards_from_the_top(self):
        deck = ORDERED_DECK
        result = count_cut(deck, 3)
        assert result.deck[:3] == deck[3:6]
        assert result.deck[-4:-1] == deck[:3]

    def test_joker_on_the_bottom_is_an_identity(self):
        """A joker is worth 53, so all but the bottom card move -- and return."""
        deck = deck_with_jokers_at(10, 53)
        result = count_cut(deck)
        assert result.deck == deck
        assert result.metadata["identity"] is True

    def test_explicit_count_is_recorded_as_from_a_letter(self):
        result = count_cut(ORDERED_DECK, 6)
        assert result.metadata["from_letter"] is True
        assert result.metadata["count"] == 6

    def test_rejects_out_of_range_count(self):
        with pytest.raises(ValueError):
            count_cut(ORDERED_DECK, 54)


class TestOutputCard:
    def test_does_not_modify_the_deck(self):
        for deck in random_decks(30):
            assert output_card(deck).deck == deck

    def test_counts_down_from_the_top_card_value(self):
        deck = parse_deck(format_deck(ORDERED_DECK))
        result = output_card(deck)
        assert result.metadata["count"] == deck[0].value
        assert result.output == deck[deck[0].value]

    def test_joker_output_yields_nothing(self):
        """The skipped-round case. Invisible to any round-trip test."""
        deck = deck_with_jokers_at(1, 30)
        deck = (Card.pip(1, "C"),) + tuple(c for c in deck if c != Card.pip(1, "C"))
        deck = validate_deck(deck)
        assert deck[0].value == 1
        assert deck[1].is_joker
        result = output_card(deck)
        assert result.output is None
        assert result.metadata["is_joker"] is True

    def test_joker_on_top_counts_53_and_stays_in_range(self):
        deck = deck_with_jokers_at(0, 30)
        result = output_card(deck)
        assert result.metadata["count"] == 53
        assert result.metadata["output_index"] == 53
