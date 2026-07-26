from __future__ import annotations

from pathlib import Path

import click

from mockware.generator.fakes_gen import generate_fakes_header
from mockware.generator.header_gen import generate_headers
from mockware.generator.source_gen import generate_sources
from mockware.yaml_reader import read_configs


@click.group()
def main() -> None:
    """mockware -- Generate mock SDK layers for embedded unit testing.

    \b
    Usage:
        mockware generate <template.yml>... -o <output-dir>

    \b
    Takes one or more YAML templates describing external SDK headers
    (C and C++) and generates stub header files, mock implementations
    with function-pointer overrides, and a fakes header for test injection.

    \b
    Templates can be:
      * Individual YAML files:  mockware generate esp.yml nvs.yml -o sdk
      * A directory:            mockware generate templates/ -o sdk
      * Shell globs:            mockware generate templates/*.yml -o sdk
    """


@main.command()
@click.argument(
    "templates",
    nargs=-1,
    required=True,
    type=click.Path(exists=True),
)
@click.option(
    "-o", "--output", default="mock-sdk", show_default=True,
    help="Output directory for generated mock SDK",
)
@click.option("--verbose", "-v", is_flag=True)
def generate(templates: tuple[str, ...], output: str, verbose: bool) -> None:
    """Generate mock SDK from TEMPLATES YAML file(s).

    \b
    TEMPLATES is one or more YAML files or directories containing .yml files.
    Each file describes external headers to mock. When multiple files define
    the same header, fields are deep-merged (later files override per-field).

    \b
    Generated output::

        <output>/
        ├── include/
        │   ├── <header>.h / .hpp       -- stub headers
        │   └── mockware/
        │       └── fakes.h             -- extern function pointers
        └── source/
            └── <header>.c / .cpp       -- mock implementations
    """
    yaml_files: list[Path] = []
    for t in templates:
        p = Path(t)
        if p.is_dir():
            yaml_files.extend(sorted(p.glob("*.yml")))
            yaml_files.extend(sorted(p.glob("*.yaml")))
        else:
            yaml_files.append(p)

    if not yaml_files:
        raise click.BadParameter(
            "No .yml or .yaml files found in the given templates",
            param_hint="templates",
        )

    click.echo(f"Reading {len(yaml_files)} template file(s)")
    for f in yaml_files:
        click.echo(f"  {f}")
    config = read_configs(yaml_files)
    hdr_count = len(config.headers)
    click.echo(f"Configured {hdr_count} header(s)")

    click.echo(f"Generating mock SDK in {output}")
    generate_headers(output, config, verbose)
    generate_sources(output, config, verbose)
    generate_fakes_header(output, config, verbose)
    click.echo("Done")


if __name__ == "__main__":
    main()
