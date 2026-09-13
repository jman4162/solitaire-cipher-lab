"""Known-answer tests against published vectors.

These, not round trips, are the correctness story.  A wrong implementation
decrypts its own wrong ciphertext perfectly, so ``decrypt(encrypt(m)) == m``
proves only internal consistency.  Only an externally published answer pins the
engine to the actual algorithm.
"""

import pytest

from solitaire_lab.cipher import encrypt
from solitaire_lab.deck import ORDERED_DECK
from solitaire_lab.keying import passphrase_deck
from solitaire_lab.keystream import generate, generate_fast


def deck_for(case):
    if case["keying"] == "ordered":
        return ORDERED_DECK
    if case["keying"] == "passphrase":
        return passphrase_deck(case["passphrase"])[0]
    raise AssertionError(f"unknown keying: {case['keying']}")


def test_vector_file_is_populated(published):
    assert published["keystreams"] and published["messages"]


def test_keystream_vectors(published):
    for case in published["keystreams"]:
        result = generate(deck_for(case), case["length"])
        assert list(result.values) == case["values"], case["name"]
        assert result.letters == case["letters"], case["name"]


def test_keystream_vectors_via_fast_path(published):
    """The fast path is held to the same published answers as the reference."""
    for case in published["keystreams"]:
        assert list(generate_fast(deck_for(case), case["length"])) == case["values"], case["name"]


def test_message_vectors(published):
    for case in published["messages"]:
        result = encrypt(case["plaintext"], deck_for(case))
        assert result.text == case["ciphertext"], case["name"]


@pytest.mark.parametrize("passphrase,plaintext,expected", [("CRYPTONOMICON", "SOLITAIRE", "KIRAKSFJAN")])
def test_short_message_is_padded_before_encryption(passphrase, plaintext, expected):
    """Nine letters become ten: the X pad is part of the published answer."""
    deck, _ = passphrase_deck(passphrase)
    result = encrypt(plaintext, deck)
    assert len(result.text) == 10
    assert result.text == expected
