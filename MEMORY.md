# check-saldo Project Memory

This file records the project assumptions, constraints, and operational knowledge for both agents and maintainers.

## Scope

- `core.py` is the source of truth for DATEV CSV parsing, validation, balance
  calculation, file discovery, and folder saldo aggregation.
- `ui.py` contains Tkinter-specific presentation and the GUI entry point.
- `main.py` contains CLI argument handling, terminal output, exit codes, and
  lazy GUI dispatch for `--gui`.
- `data/` contains local business CSVs used during development. They are intentionally ignored by Git.
- Tests use generated temporary CSVs and must not depend on private business data.

## User constraints

- Use `uv` for execution and build dependency management.
- Do not install packages globally.
- Keep runtime dependencies to the Python standard library.
- PyInstaller is a build-time dependency only; it is not a runtime application dependency.
- Do not add custom classes, Python type annotations, or triple-quoted comments/docstrings unless the user explicitly changes this requirement.
- Preserve unrelated FANZTOOL documents and assets outside this project.

## DATEV assumptions

- The current files are German DATEV `EXTF` `Buchungsstapel` CSV files.
- They use a metadata row followed by a header row, semicolon delimiters, and Latin-1-compatible text encoding.
- The normal columns used by this project are:
  - `Umsatz (ohne Soll/Haben-Kz)` for the amount;
  - `Soll/Haben-Kennzeichen` for the side of `Konto`;
  - `Konto` for the account whose balance is checked;
  - `Gegenkonto (ohne BU-Schlüssel)` for the opposite account.
- These names are valid for this DATEV Buchungsstapel format, not for every possible DATEV export category.
- The GUI can select alternative column names, but every file in one recursive run must expose the selected columns.

## Balance semantics

- `Saldo` is the movement of the account represented by the rows: S total minus H total.
- A file must contain exactly one value in the selected `Konto` column; mixing
  different accounts into one saldo is an error.
- For a row marked `S`, the amount is debit on `Konto` and credit on `Gegenkonto`.
- For a row marked `H`, the amount is credit on `Konto` and debit on `Gegenkonto`.
- Missing `Konto` or `Gegenkonto` and values other than S/H are errors.
- DATEV amounts must be positive, non-zero, use a comma and two decimal places,
  and omit thousands separators.
- `Decimal` is required for all money calculations; do not replace it with binary floating point.

## Input and GUI behavior

- A command-line input can be one file or a directory.
- Directory input is recursive and processes files whose suffix is `.csv`, case-insensitively.
- The GUI can select a file or directory, load column names from the first CSV, and run the same calculation for all discovered CSV files.
- The default local input is under `data/`; it is not expected to exist in a clean clone.

## Packaging

- The GUI release entry point is `ui.py`.
- The CLI release entry point is `main.py`.
- `build_release.py` invokes PyInstaller through the Python environment created by `uv`.
- macOS releases support Apple Silicon only and use PyInstaller `arm64` on the
  GitHub-hosted `macos-15` runner.
- Windows and Linux cannot share a native executable with macOS. The workflow
  builds a Windows x86 package and a Linux x64 package; Windows x64 is not released.
- No private CSV from `data/` may be included in a release artifact.

## CI/CD

- `.github/workflows/build-release.yml` runs tests first, builds GUI packages on macOS, Windows, and Linux, and uploads archives as workflow artifacts.
- Pushes to `main` create a GitHub release using the repository `GITHUB_TOKEN`.
- The workflow must not require credentials stored in the repository.
- Release artifacts should be checked for platform and architecture names before distribution.

## Verification commands

From this directory:

```text
uv run python tests/test_check_saldo.py
uv run main.py data
uv run main.py --gui
uv run --group build python build_release.py --target gui
```

The first command is the minimum logic gate. The build command is platform-native: run it on the target operating system or let GitHub Actions run it on the matching runner.
