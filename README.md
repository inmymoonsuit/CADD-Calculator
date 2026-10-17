# CADD Calculator

Open-source calculators for computer-aided drafting and design. It runs as a desktop app
on Windows, macOS, and Linux, and as a command-line tool.

It started as the Excel spreadsheets used to teach sheet-metal bend calculations in a
CADD degree program. The goal is a principled, tested, extensible home for those
calculations and for future ones: structural drafting, tolerancing, threads, and more.

> **Status: pre-alpha skeleton (0.1.0.dev0).** The architecture is in place and four
> sheet-metal calculators work from the CLI and a basic GUI. Nothing is packaged yet.

## What it does today

| Calculator | Methods |
|---|---|
| Bend allowance & deduction | Course formula (0.64T + 1.57R), K-factor |
| Flat length of a formed segment | Course formula, K-factor |
| V-die opening (air bending) | Inside-radius percentage rule, 8 × T rule of thumb |
| Truncated cone flat pattern | Course spreadsheet, mean diameter |

Every result shows its work (formula, substituted values, result), names its method and
references, and is labeled with a **verification status** (`unverified` or `verified`), plus
whether it **reproduces the legacy** course spreadsheets. See [docs/user](docs/user/index.md).

```text
$ caddcalc run sheet_metal.bend_allowance T=0.1046 R=0.156 A=90 --method course
...
Work
  BA = (0.64·T + 1.57·R)·A/90
     = (0.64·0.1046 + 1.57·0.1560)·90.00°/90
     = 0.3119 in
```

## Quick start (from source)

You need [uv](https://docs.astral.sh/uv/). It installs a suitable Python for you.

```bash
git clone https://github.com/inmymoonsuit/CADD-Calculator.git
cd CADD-Calculator
uv sync --extra gui          # create .venv with the GUI toolkit (PySide6)
uv run caddcalc list         # CLI
uv run caddcalc-gui          # desktop app
uv run pytest                # tests
```

## Documentation

* **Users:** [docs/user/](docs/user/index.md) covers getting started, each calculator, the glossary, and units.
* **Developers:** [docs/dev/](docs/dev/README.md) covers architecture, the decision records (ADRs), known
  issues, the engineering log, the roadmap, and the legacy-workbook transcription.
* **Contributing:** [CONTRIBUTING.md](CONTRIBUTING.md).
* **A wrong reference value?** See
  [Reporting a wrong or rights-encumbered value](CONTRIBUTING.md#reporting-a-wrong-or-rights-encumbered-value).

## Disclaimer

Results are for drafting and education. Real bend allowances depend on tooling, material
lot, grain direction, and the bending method. Verify against your shop's data and test
bends before manufacturing. The software comes with no warranty.

## License

Code: [Apache License 2.0](LICENSE.md). Third-party names and marks are not covered by
the code license. See
[ADR-0008](docs/dev/decisions/0008-licensing-and-third-party-assets.md).
