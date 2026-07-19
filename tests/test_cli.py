from click.testing import CliRunner

from mockware.cli import main


def test_help_succeeds() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "mockware" in result.output
    assert "scan" in result.output
    assert "parse" in result.output
    assert "generate" in result.output


def test_scan_help_succeeds() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["scan", "--help"])
    assert result.exit_code == 0
    assert "PROJECT_PATH" in result.output
    assert "--mode" in result.output


def test_parse_help_succeeds() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["parse", "--help"])
    assert result.exit_code == 0
    assert "PROJECT_PATH" in result.output


def test_generate_help_succeeds() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["generate", "--help"])
    assert result.exit_code == 0
    assert "--project" in result.output
    assert "--input" in result.output
    assert "--output" in result.output


def test_scan_fails_without_project_path() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["scan"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_generate_fails_without_required_opts() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["generate"])
    assert result.exit_code != 0
    assert "Error" in result.output
