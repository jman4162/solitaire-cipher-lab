"""The command line interface."""

import json

import pytest

from solitaire_lab.cli import main


def run(capsys, *argv):
    code = main(list(argv))
    return code, capsys.readouterr().out


def test_encrypt_matches_the_published_vector(capsys):
    code, out = run(capsys, "encrypt", "--ordered-deck", "AAAAAAAAAAAAAAA")
    assert code == 0
    assert "EXKYI ZSGEH UNTIQ" in out


def test_encrypt_with_passphrase(capsys):
    _, out = run(capsys, "encrypt", "-p", "CRYPTONOMICON", "SOLITAIRE")
    assert "KIRAK SFJAN" in out


def test_decrypt_reverses_encrypt(capsys):
    _, out = run(capsys, "decrypt", "-p", "FOO", "ITHZUJIWGRFARMW")
    assert "AAAAA AAAAA AAAAA" in out


def test_keystream(capsys):
    _, out = run(capsys, "keystream", "--ordered-deck", "-n", "15")
    assert "DWJXH YRFDG TMSHP" in out
    assert "4 49 10 24" in out


def test_unkeyed_deck_is_flagged_as_not_a_key(capsys):
    _, out = run(capsys, "keystream", "--ordered-deck", "-n", "3")
    assert "not a key" in out


def test_encrypt_warns_that_this_is_not_real_security(capsys):
    _, out = run(capsys, "encrypt", "-p", "KEY", "HELLO")
    assert "not use it to protect real information" in " ".join(out.split())


def test_teach_explains_each_step(capsys):
    _, out = run(capsys, "teach", "--ordered-deck", "-r", "1")
    assert "Move joker A down one" in out
    assert "Triple cut" in out
    assert "Count cut" in out


def test_worksheet_lists_every_round(capsys, tmp_path):
    out_file = tmp_path / "w.txt"
    code, _ = run(capsys, "worksheet", "--ordered-deck", "-r", "4", "-o", str(out_file))
    assert code == 0
    text = out_file.read_text()
    assert "HAND WORKSHEET" in text
    assert "Round   1:" in text
    assert "no output (joker)" in text


def test_export_writes_valid_trace_json(capsys, tmp_path):
    out_file = tmp_path / "t.json"
    run(capsys, "export", "--ordered-deck", "-r", "3", "-o", str(out_file))
    data = json.loads(out_file.read_text())
    assert data["schema"] == 1
    assert len(data["initial_deck"]) == 54
    assert data["events"]


def test_export_of_a_message_carries_the_keystream(capsys, tmp_path):
    out_file = tmp_path / "m.json"
    run(capsys, "export", "-p", "KEY", "-m", "HELLO", "-o", str(out_file))
    data = json.loads(out_file.read_text())
    assert len(data["output"]) == 5


def test_deck_subcommand_renders_a_deck(capsys):
    code, out = run(capsys, "deck", "-p", "SECRET")
    assert code == 0
    assert "JA" in out


def test_analyze_reuse(capsys):
    _, out = run(capsys, "analyze", "reuse", "--passphrase", "DEMOKEY")
    assert "identical: True" in out


def test_analyze_bias(capsys):
    _, out = run(capsys, "analyze", "bias", "--samples", "40", "--length", "60")
    assert "Solitaire's keystream repeats" in out


def test_bad_deck_reports_an_error_not_a_traceback(capsys):
    code, out = run(capsys, "encrypt", "-d", "AC 2C 3C", "HELLO")
    assert code == 2
    assert "error:" in out


def test_brackets_in_user_input_are_not_read_as_markup(capsys):
    """Rich would parse "[/x]" as a closing tag and crash before printing the error."""
    code, out = run(capsys, "encrypt", "-d", "[/x] AC", "HELLO")
    assert code == 2
    assert "error:" in out


def test_reuse_shows_a_bracketed_passphrase_verbatim(capsys):
    code, out = run(capsys, "analyze", "reuse", "--passphrase", "[red]KEY")
    assert code == 0
    assert "[red]KEY" in out


@pytest.mark.parametrize("command", ["encrypt", "decrypt"])
@pytest.mark.parametrize("flag", ["-p", "-d"])
def test_an_empty_key_is_an_error_not_the_unkeyed_deck(capsys, command, flag):
    code, out = run(capsys, command, flag, "", "HELLO")
    assert code == 2
    assert "error:" in out


def test_key_options_are_mutually_exclusive():
    with pytest.raises(SystemExit):
        main(["encrypt", "-p", "KEY", "--ordered-deck", "HELLO"])
