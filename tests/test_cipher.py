"""Encryption, decryption, and the statelessness that makes them teachable."""

import pytest

from helpers import random_decks
from solitaire_lab.cipher import decrypt, encrypt
from solitaire_lab.codec import add_mod26, normalize, subtract_mod26
from solitaire_lab.deck import ORDERED_DECK
from solitaire_lab.keying import passphrase_deck


@pytest.mark.parametrize("deck", list(random_decks(20)))
def test_round_trip(deck):
    """Decryption recovers the *padded* plaintext -- the X pad is not guessed away."""
    message = "ATTACKATDAWN"
    cipher = encrypt(message, deck)
    assert decrypt(cipher.text, deck).text == "ATTACKATDAWNXXX"


def test_encryption_does_not_mutate_the_caller_s_deck():
    deck = ORDERED_DECK
    encrypt("HELLO", deck)
    assert deck == ORDERED_DECK


def test_repeated_calls_are_independent():
    """There is no hidden cipher object, so a second call cannot depend on a first."""
    deck = ORDERED_DECK
    assert encrypt("HELLO", deck).text == encrypt("HELLO", deck).text


def test_final_deck_is_returned_for_explicit_chaining():
    """Continuing a stream is possible, but only by passing the deck on yourself."""
    first = encrypt("HELLOWORLD", ORDERED_DECK)
    second = encrypt("AAAAAAAAAA", first.final_deck)
    combined = encrypt("HELLOWORLDAAAAAAAAAA", ORDERED_DECK)
    assert first.text + second.text == combined.text


def test_input_is_normalized():
    assert encrypt("do not use pc!", ORDERED_DECK).text == encrypt("DONOTUSEPC", ORDERED_DECK).text


def test_plaintext_is_padded_to_whole_groups():
    assert len(encrypt("HELLO WORLDS", ORDERED_DECK).text) == 15
    assert len(encrypt("HELLO WORLD", ORDERED_DECK).text) == 10
    assert len(encrypt("ABCDE", ORDERED_DECK).text) == 5


def test_padding_can_be_disabled():
    assert len(encrypt("HELLOWORLD!", ORDERED_DECK, pad_message=False).text) == 10


def test_decrypt_does_not_pad():
    """Padding is added when encrypting; decryption must not add more."""
    cipher = encrypt("HELLO", ORDERED_DECK)
    assert len(decrypt(cipher.text, ORDERED_DECK).text) == len(cipher.text)


def test_grouped_output():
    assert encrypt("HELLOWORLD", ORDERED_DECK).grouped.count(" ") == 1


def test_keystream_is_reported_alongside_the_text():
    result = encrypt("HELLO", ORDERED_DECK)
    assert len(result.keystream) == len(result.text)


def test_ciphertext_is_plaintext_plus_keystream():
    """The whole cipher, in one assertion: C = P + K (mod 26)."""
    result = encrypt("DONOTUSEPC", ORDERED_DECK, pad_message=False)
    plain = [ord(c) - 64 for c in normalize("DONOTUSEPC")]
    keys = [k % 26 or 26 for k in result.keystream]
    assert [ord(c) - 64 for c in result.text] == [add_mod26(p, k) for p, k in zip(plain, keys, strict=True)]


def test_keystream_values_above_26_wrap_before_being_added():
    """Card values run to 52; the keystream letter is the value mod 26."""
    result = encrypt("A" * 40, ORDERED_DECK)
    assert any(k > 26 for k in result.keystream)
    assert all("A" <= ch <= "Z" for ch in result.text)


@pytest.mark.parametrize("passphrase", ["FOO", "SECRETKEY", "CRYPTONOMICON"])
def test_round_trip_under_passphrase_keying(passphrase):
    deck, _ = passphrase_deck(passphrase)
    assert decrypt(encrypt("MEETATDAWN", deck).text, deck).text == "MEETATDAWN"


def test_mod26_arithmetic_stays_in_range():
    for a in range(1, 27):
        for b in range(1, 27):
            assert 1 <= add_mod26(a, b) <= 26
            assert 1 <= subtract_mod26(a, b) <= 26
            assert subtract_mod26(add_mod26(a, b), b) == a
