from pathlib import Path

from click.testing import CliRunner

from mockware.cli import main


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "mockware" in result.output
    assert "generate" in result.output


def test_generate_help():
    runner = CliRunner()
    result = runner.invoke(main, ["generate", "--help"])
    assert result.exit_code == 0
    assert "TEMPLATE" in result.output


def test_generate_basic_c(samples_dir: Path, tmp_path: Path):
    runner = CliRunner()
    template = str(samples_dir / "basic_c.yml")
    output = str(tmp_path / "out")
    result = runner.invoke(main, ["generate", template, "-o", output])
    assert result.exit_code == 0
    assert "Done" in result.output

    assert (Path(output) / "include" / "esp_err.h").exists()
    assert (Path(output) / "include" / "driver" / "gpio.h").exists()
    assert (Path(output) / "include" / "freertos" / "task.h").exists()
    assert (Path(output) / "source" / "driver" / "gpio.c").exists()
    assert (Path(output) / "include" / "mockware" / "fakes.h").exists()


def test_generate_verbose(samples_dir: Path, tmp_path: Path):
    runner = CliRunner()
    template = str(samples_dir / "basic_c.yml")
    output = str(tmp_path / "out")
    result = runner.invoke(main, ["generate", template, "-o", output, "-v"])
    assert result.exit_code == 0
    assert "header:" in result.output
    assert "source:" in result.output
    assert "fakes:" in result.output


def test_generate_basic_cpp(samples_dir: Path, tmp_path: Path):
    runner = CliRunner()
    template = str(samples_dir / "basic_cpp.yml")
    output = str(tmp_path / "out")
    result = runner.invoke(main, ["generate", template, "-o", output])
    assert result.exit_code == 0
    assert (Path(output) / "include" / "device" / "sensor.hpp").exists()
    assert (Path(output) / "source" / "device" / "sensor.cpp").exists()
