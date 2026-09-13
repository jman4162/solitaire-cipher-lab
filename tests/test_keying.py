"""Keying the deck: ordered, explicit, shuffled and passphrase."""

import pytest

from solitaire_lab.deck import ORDERED_DECK, format_deck, validate_deck
from solitaire_lab.keying import explicit_deck, ordered_deck, passphrase_deck, shuffled_deck


def test_ordered_deck_is_in_bridge_order():
    deck = ordered_deck()
    assert [c.value for c in deck[:52]] == list(range(1, 53))
    assert deck[52].is_joker and deck[53].is_joker


def test_explicit_deck_round_trips_through_text():
    assert explicit_deck(format_deck(ORDERED_DECK)) == ORDERED_DECK


def test_explicit_deck_rejects_an_incomplete_deck():
    with pytest.raises(ValueError):
        explicit_deck("AC 2C 3C")


def test_explicit_deck_rejects_duplicates():
    codes = format_deck(ORDERED_DECK).split()
    codes[5] = codes[4]
    with pytest.raises(ValueError, match="permutation"):
        explicit_deck(" ".join(codes))


def test_shuffled_deck_is_valid_and_seedable():
    assert shuffled_deck(7) == shuffled_deck(7)
    assert shuffled_deck(7) != shuffled_deck(8)
    validate_deck(shuffled_deck(7))


@pytest.mark.parametrize("passphrase", ["A", "FOO", "CRYPTONOMICON"])
def test_passphrase_keying_produces_a_valid_deck(passphrase):
    deck, _ = passphrase_deck(passphrase)
    validate_deck(deck)


def test_passphrase_keying_is_deterministic():
    assert passphrase_deck("SECRET")[0] == passphrase_deck("SECRET")[0]


def test_different_passphrases_give_different_decks():
    assert passphrase_deck("SECRET")[0] != passphrase_deck("SECRETS")[0]


def test_passphrase_changes_the_deck():
    assert passphrase_deck("FOO")[0] != ORDERED_DECK


def test_passphrase_is_normalized():
    assert passphrase_deck("foo bar!")[0] == passphrase_deck("FOOBAR")[0]


def test_empty_passphrase_is_rejected():
    with pytest.raises(ValueError, match="at least one letter"):
        passphrase_deck("   ")


def test_keying_runs_one_round_per_letter():
    """Each letter drives four steps plus one extra letter-valued count cut."""
    _, trace = passphrase_deck("FOO", trace=True)
    assert trace.rounds == 3
    assert len(trace.events) == 3 * 5
    extra = [e for e in trace.events if e.meta.get("from_letter")]
    assert [e.meta["letter"] for e in extra] == ["F", "O", "O"]
    assert [e.meta["count"] for e in extra] == [6, 15, 15]


def test_keying_emits_no_keystream():
    """Keying uses the shuffling steps only; the output step never runs."""
    _, trace = passphrase_deck("SECRET", trace=True)
    assert all(e.phase != "output" for e in trace.events)
    assert trace.output == ()


def test_keying_can_continue_from_a_non_ordered_deck():
    once, _ = passphrase_deck("FOO")
    twice, _ = passphrase_deck("BAR", deck=once)
    assert twice != once
    validate_deck(twice)
