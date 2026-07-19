import click


@click.group()
def main() -> None:
    """mockware — Generate mock SDK layers for embedded unit testing.


    \b
    Workflow:
        1. scan      — auto-detect missing external SDK dependencies
        2. (edit)    — review & customize the generated YAML
        3. generate  — produce stub headers + function-pointer fakes

    \b
    Subcommands:
        scan      Scan your project for missing external headers.
        parse     Alias for scan (identical behaviour).
        generate  From YAML + project sources → generate mock stubs.
    """


@main.command()
@click.argument("project_path", type=click.Path(exists=True, file_okay=False))
@click.option("-o", "--output", default="missing_apis.yml", show_default=True,
              help="Output YAML file path")
@click.option("--mode", type=click.Choice(["full", "partial"]),
              default="partial", show_default=True,
              help="full=create complete YAML from scratch; "
                   "partial=merge new items into existing YAML")
@click.option("--existing", default=None,
              type=click.Path(exists=True, dir_okay=False),
              help="Existing YAML to merge into (for --mode partial)")
@click.option("--include-dir", "-I", multiple=True,
              help="Directories to check when deciding if a header is "
                   "'present' in the project")
@click.option("--include", "include_patterns", multiple=True,
              default=["**/*.c", "**/*.h", "**/*.cpp", "**/*.hpp",
                       "**/*.cc", "**/*.cxx"],
              help="Glob patterns for source files to scan (default: "
                   "**/*.c, **/*.h, **/*.cpp, **/*.hpp, **/*.cc, **/*.cxx)")
@click.option("--exclude", "exclude_patterns", multiple=True,
              default=[],
              help="Glob patterns for files/dirs to exclude from scanning")
@click.option("--verbose", "-v", is_flag=True)
def scan(project_path: str, output: str, mode: str,
         existing: str | None,
         include_dir: tuple[str, ...],
         include_patterns: tuple[str, ...],
         exclude_patterns: tuple[str, ...],
         verbose: bool) -> None:
    """Scan PROJECT_PATH for missing external SDK dependencies.

    \b
    Walks all source files, finds every #include directive, and
    identifies headers that do NOT exist in the project tree or any
    -I directory.  Those are external SDK dependencies.

    \b
    For each missing header, the tool scans usage context to infer
    function signatures, type references, macros, enums, and structs.
    The result is a YAML file with six sections:

    \b
      headers    {path: {includes: [...]}}  — missing external headers
      types      {name: underlying_type}    — unknown type references
      macros     {name: value}              — ALL_CAPS identifiers
      enums      {name: {values: {...}}}    — typedef enum definitions
      structs    {name: {definition: ...}}  — struct definitions
      functions  {name: {return:, params:, header:}}  — inferred calls

    \b
    Type/macro/enum/struct definitions are global (not per-header).
    Each function is attributed to a header by naming convention.
    Functions that don't match any header go to source/general.c.

    \b
    Use --mode partial (default) with --existing to merge results
    into a pre-existing YAML file.  Your manual edits (custom types,
    overridden return values, added function-like macros, etc.) are
    preserved and newly discovered symbols are added.

    \b
    The --exclude pattern is passed to scan_project_symbols, so
    generated SDK directories (e.g. mock-sdk/**) can be excluded
    to prevent their types from being treated as project-internal.

    \b
    Examples:

    \b
      # First scan
      mockware scan ./my-project -o missing_apis.yml

    \b
      # Re-scan merging into existing YAML (preserves edits)
      mockware scan ./my-project \\
          --existing missing_apis.yml --mode partial \\
          --exclude "mock-sdk/**" --exclude "build/**"
    """
    from .parser.header_parser import infer_missing_apis
    from .parser.source_scanner import find_missing_deps
    from .parser.yaml_writer import merge_into_yaml, write_yaml

    click.echo(f"Scanning {project_path} for external dependencies…")
    missing_headers = find_missing_deps(
        project_path,
        extra_includes=list(include_dir),
        include_patterns=list(include_patterns),
        exclude_patterns=list(exclude_patterns),
        verbose=verbose,
    )
    if not missing_headers:
        click.echo("No missing external headers found — all includes "
                    "resolve to existing files.")
        raise click.Abort()

    click.echo(f"Found {len(missing_headers)} missing headers — "
               f"inferring usage context…")
    result = infer_missing_apis(
        project_path,
        missing_headers,
        include_patterns=list(include_patterns),
        exclude_patterns=list(exclude_patterns),
        verbose=verbose,
    )

    # Merge with existing YAML if --mode partial
    if mode == "partial" and existing:
        click.echo(f"Reading existing YAML from {existing}…")
        from .generator.yaml_reader import read_yaml
        existing_data = read_yaml(existing)
        click.echo("Merging new items into existing data…")
        result = merge_into_yaml(existing_data, result, mode="partial")

    write_yaml(result, output)
    click.echo(f"Wrote {output} ({mode} mode)")


# Register `parse` as an alias for `scan`
main.add_command(scan, name="parse")


@main.command()
@click.option("-p", "--project", required=True,
              type=click.Path(exists=True, file_okay=False),
              help="Root of your project source tree")
@click.option("-i", "--input", required=True,
              type=click.Path(exists=True, dir_okay=False),
              help="YAML knowledge base (from `scan` / `parse`)")
@click.option("-o", "--output", required=True,
              type=click.Path(file_okay=False),
              help="Output directory for the mock SDK tree")
@click.option("--custom-impl", default=None,
              type=click.Path(exists=True, file_okay=False),
              help="Directory with user-provided implementation overrides")
@click.option("--verbose", "-v", is_flag=True)
def generate(project: str, input: str, output: str,
             custom_impl: str | None, verbose: bool) -> None:
    """Generate mock SDK stubs from a YAML knowledge base.

    \b
    Scans PROJECT's source files for #include directives, looks them up
    in the YAML headers section, expands transitive includes, and writes
    a complete mock SDK tree to OUTPUT.

    \b
    Generated tree::

        OUTPUT/
        ├── CMakeLists.txt              — builds as ``mock_sdk``
        ├── include/
        │   ├── <header>.h              — stub per SDK header
        │   └── mockware/
        │       ├── types.h             — typedef definitions
        │       ├── macros.h            — #define macros
        │       ├── enums.h             — enum definitions
        │       ├── structs.h           — struct definitions
        │       └── fakes.h             — overridable function pointer
        │                                  extern declarations
        └── source/
            ├── <header>.c              — per-header implementations
            └── general.c               — untagged function impls

    \b
    Function attribution:
      * YAML ``header:`` field → source/<header>.c
      * No ``header:`` field  → source/general.c

    \b
    Each stub function exposes:
      * ``<name>_default()``    — default implementation (stub body)
      * ``<name>_mock``           — overridable function pointer
      * ``<name>()``            — delegates to ``_mock``

    \b
    Function-like macros:
      YAML macro values starting with ``(`` emit ``#define NAME(value)``
      (no space), e.g. ``pdMS_TO_TICKS: '(x) ((uint64_t)x)'`` → ``#define pdMS_TO_TICKS(x) ((uint64_t)x)``.

    \b
    Standard type includes:
      The generator scans types, functions, macros, and structs for
      standard C types (uint64_t, size_t, bool, etc.) and automatically
      adds the corresponding #include (<stdint.h>, <stddef.h>, etc.)
      to mockware/types.h.

    \b
    --custom-impl:
      Directory containing user-provided ``<name>.c`` files.  When an
      implementation file exists, the generator skips auto-generating
      it (but still generates the header and fakes pointer).

    \b
    Examples:

    \b
      mockware generate \\
          --project . \\
          --input missing_apis.yml \\
          --output mock-sdk
    """
    from .generator.cmake_gen import generate_cmake
    from .generator.defs_header_gen import generate_defs_headers
    from .generator.fakes_header_gen import generate_fakes_header
    from .generator.project_scanner import find_used_headers
    from .generator.stub_header_gen import expand_includes, generate_headers
    from .generator.stub_impl_gen import generate_implementations
    from .generator.yaml_reader import read_yaml

    click.echo(f"Reading {input}…")
    data = read_yaml(input)

    click.echo(f"Scanning project {project}…")
    used = find_used_headers(project, input, verbose)
    if not used:
        click.echo("No headers found in project sources.")
        raise click.Abort()

    click.echo(f"Found {len(used)} referenced header paths")

    headers = data.get("headers", {})
    missing = used - headers.keys()
    if missing:
        click.echo(f"Warning: {len(missing)} headers not in YAML "
                   f"(will be skipped):")
        for h in sorted(missing):
            click.echo(f"  {h}")

    # Expand to include transitive dependencies
    needed = expand_includes(headers, used & headers.keys())
    click.echo(f"Expanded to {len(needed)} headers "
               f"(including transitive deps)")

    click.echo(f"Generating mock SDK in {output}…")
    generate_defs_headers(output, data, verbose)
    generate_headers(output, data, needed, verbose)
    generate_implementations(output, data, verbose)
    generate_fakes_header(output, data, verbose)
    generate_cmake(output, data, verbose)

    click.echo(f"Done — mock SDK written to {output}")
