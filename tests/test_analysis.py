"""The cryptanalysis experiments."""

import pytest

from solitaire_lab.analysis import bias, reuse
from solitaire_lab.codec import subtract_mod26, to_values


class TestKeyReuse:
    @pytest.fixture(scope="class")
    @classmethod
    def report(cls):
        return reuse.demonstrate("ATTACKATDAWN", "RETREATATTEN", passphrase="DEMOKEY")

    def test_the_keystream_cancels(self, report):
        """The whole lesson, as one assertion: C1 - C2 == P1 - P2."""
        assert report["key_cancelled"]
        assert report["cipher_difference"] == report["plain_difference"]

    def test_difference_is_computed_correctly(self, report):
        expected = [
            subtract_mod26(a, b)
            for a, b in zip(to_values(report["plaintext_1"]), to_values(report["plaintext_2"]), strict=True)
        ]
        assert to_values(report["plain_difference"]) == tuple(expected)

    def test_both_messages_use_the_same_keystream(self, report):
        assert len(report["keystream"]) == len(report["ciphertext_1"]) == len(report["ciphertext_2"])

    def test_ciphertexts_differ_from_plaintexts(self, report):
        assert report["ciphertext_1"] != report["plaintext_1"]
        assert report["ciphertext_2"] != report["plaintext_2"]

    def test_messages_of_unequal_length_are_truncated_to_the_shorter(self):
        report = reuse.demonstrate("SHORT", "MUCHLONGERMESSAGE")
        assert len(report["plaintext_1"]) == len(report["plaintext_2"])
        assert report["key_cancelled"]

    def test_render_mentions_the_identity(self, report):
        text = reuse.render(report)
        assert "C1 - C2" in text and "P1 - P2" in text


class TestBias:
    @pytest.fixture(scope="class")
    @classmethod
    def report(cls):
        return bias.measure(samples=300, length=120, seed=1)

    def test_repeat_rate_exceeds_the_ideal(self, report):
        """Solitaire repeats letters more often than a uniform stream would."""
        assert report["observed_rate"] > report["ideal_rate"]
        assert report["excess_ratio"] > 1.0

    def test_measured_rate_is_in_the_documented_range(self, report):
        """Published analyses put the repeat rate near 1/22.5, not 1/26."""
        assert 0.040 < report["observed_rate"] < 0.050

    def test_ideal_rate_is_one_in_twentysix(self, report):
        assert report["ideal_rate"] == pytest.approx(1 / 26)

    def test_measurement_is_reproducible(self):
        assert bias.measure(samples=50, length=60, seed=7) == bias.measure(samples=50, length=60, seed=7)

    def test_letter_frequencies_sum_to_one(self, report):
        assert sum(report["letter_frequencies"].values()) == pytest.approx(1.0)
        assert len(report["letter_frequencies"]) == 26

    def test_pairs_examined_is_consistent(self, report):
        assert report["pairs_examined"] == report["samples"] * (report["length"] - 1)
