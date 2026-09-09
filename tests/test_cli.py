from pathlib import Path

from pdf_split.cli import run


def test_cli_requires_existing_input_file(capsys):
    exit_code = run(["missing.pdf", "--pages", "100"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Input file does not exist" in captured.err


def test_cli_requires_one_split_mode(tmp_path, capsys):
    input_file = tmp_path / "input.pdf"
    input_file.write_bytes(b"%PDF-1.4\n")

    exit_code = run([str(input_file)])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "one of the arguments --pages --split-on is required" in captured.err
