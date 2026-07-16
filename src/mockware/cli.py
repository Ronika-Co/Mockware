import click


@click.group()
def main() -> None:
    """mockware — Generate mock SDK layers for embedded unit testing.

    \b
    Subcommands:
        parse     Scan SDK headers → generate YAML knowledge base.
        generate  From YAML + project sources → generate mock stubs.
    """


@main.command()
@click.argument("idf_path", type=click.Path(exists=True, file_okay=False))
@click.option("-o", "--output", default="known_apis.yml", show_default=True,
              help="Output YAML file path")
@click.option("--components", default=None,
              help="Comma-separated component names to scan (default: all)")
@click.option("--include", "-I", multiple=True,
              help="Extra include directories for the preprocessor")
@click.option("--verbose", "-v", is_flag=True)
def parse(idf_path: str, output: str, components: str | None,
          include: tuple[str, ...], verbose: bool) -> None:
    """Parse ESP-IDF headers at IDF_PATH into a YAML knowledge base.

    \b
    IDF_PATH must point to an ESP-IDF installation root (e.g. $IDF_PATH).
    The tool scans component include directories, extracts macros, types,
    enums, structs, and function declarations, and writes them to OUTPUT.
    """
    from .parser.header_parser import parse_headers
    from .parser.idf_scanner import discover_headers
    from .parser.macro_extractor import extract_macros
    from .parser.yaml_writer import write_yaml

    click.echo(f"Scanning {idf_path}…")
    headers = discover_headers(idf_path, components, verbose)
    if not headers:
        click.echo("No headers found. Check the path or --components filter.")
        raise click.Abort()

    click.echo(f"Found {len(headers)} headers — parsing…")
    result = parse_headers(idf_path, headers, list(include), verbose)

    click.echo("Extracting macros…")
    result = extract_macros(idf_path, headers, result, list(include), verbose)

    write_yaml(result, output)
    click.echo(f"Wrote {output}")


@main.command()
@click.option("-p", "--project", required=True,
              type=click.Path(exists=True, file_okay=False),
              help="Root of your ESP-IDF project")
@click.option("-i", "--input", required=True,
              type=click.Path(exists=True, dir_okay=False),
              help="YAML knowledge base (from `parse`)")
@click.option("-o", "--output", required=True,
              type=click.Path(file_okay=False),
              help="Output directory for the virtual ESP-IDF tree")
@click.option("--idf-path", default=None,
              type=click.Path(exists=True, file_okay=False),
              help="Optional IDF path to auto-discover component mappings")
@click.option("--custom-impl", default=None,
              type=click.Path(exists=True, file_okay=False),
              help="Directory with user-provided implementation overrides")
@click.option("--verbose", "-v", is_flag=True)
def generate(project: str, input: str, output: str, idf_path: str | None,
             custom_impl: str | None, verbose: bool) -> None:
    """Generate mock SDK stubs from a YAML knowledge base.

    \b
    Scans PROJECT's source files for ESP-IDF #include directives,
    looks them up in the YAML, and writes stub headers + function-pointer
    implementations to OUTPUT.
    """
    from .generator.cmake_gen import generate_cmake
    from .generator.fakes_header_gen import generate_fakes_headers
    from .generator.project_scanner import find_used_headers
    from .generator.stub_header_gen import expand_includes, generate_headers
    from .generator.stub_impl_gen import generate_implementations
    from .generator.yaml_reader import read_yaml

    click.echo(f"Scanning project {project}…")
    used = find_used_headers(project, verbose)
    if not used:
        click.echo("No ESP-IDF headers found in project sources.")
        raise click.Abort()

    click.echo(f"Found {len(used)} referenced ESP-IDF header paths")

    click.echo(f"Reading {input}…")
    known_apis = read_yaml(input)
    missing = used - known_apis.keys()
    if missing:
        click.echo(f"Warning: {len(missing)} headers not in YAML (will be skipped):")
        for h in sorted(missing):
            click.echo(f"  {h}")

    # Expand to include transitive dependencies
    needed = expand_includes(known_apis, used & known_apis.keys())
    click.echo(f"Expanded to {len(needed)} headers (including transitive deps)")

    click.echo(f"Generating mock SDK in {output}…")
    generate_headers(output, known_apis, needed, verbose)
    generate_implementations(output, known_apis, needed, verbose)
    generate_fakes_headers(output, known_apis, needed, verbose)
    generate_cmake(output, known_apis, needed)

    click.echo(f"Done — mock SDK written to {output}")
