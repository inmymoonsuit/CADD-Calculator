# CADD Calculator

Open-source calculators for computer-aided drafting and design. It runs as a desktop app
on Windows, macOS, and Linux, and as a command-line tool.

It started as the Excel spreadsheets used to teach sheet-metal bend calculations in a
CADD degree program. The goal is a principled, tested, extensible home for those
calculations and for future ones: structural drafting, tolerancing, threads, and more.

> **Status: pre-alpha (0.1.0.dev0).** Sixteen calculators in three families work from
> the desktop app and the CLI, in US and British English, each field and result with a
> picker for its unit ([ADR-0024](docs/dev/decisions/0024-units-on-fields.md)). Nothing
> is packaged yet. Next: the layout contract
> ([ADR-0023](docs/dev/decisions/0023-layout-contract.md)), then installers for every
> platform ([ADR-0022](docs/dev/decisions/0022-distribution-and-signing.md)).

## What it does today

**Geometry:** every property of a shape at once.

| Calculator | Methods |
|---|---|
| Arc and sector | Radius and angle |
| Circle | From the diameter; from the radius |
| Rectangle | Length and width |
| Regular polygon | From the side; from across flats; from across corners |
| Right triangle | Two legs; a leg and the hypotenuse; a leg and its opposite angle; the hypotenuse and an angle |
| Triangle (three sides) | Three sides |

**Conversions:** a value in another unit, each with a picker for its unit.

| Calculator | Units |
|---|---|
| Angle | Degrees, degrees-minutes-seconds, minutes and seconds of arc, radians |
| Area | in², ft², mm², cm², m² |
| Decimal to fraction | A length to its nearest 1/16, 1/32 or 1/64 inch, with the fraction's error |
| Fraction to decimal | A fraction of an inch, such as 3/16, as a decimal in any length unit |
| Length | in, feet and inches, ft, mm, cm, m |
| Stress and pressure | psi, ksi, kPa, MPa, GPa |

**Sheet metal:**

| Calculator | Methods |
|---|---|
| Bend allowance & deduction | Fixed K-factor (≈ 0.41), the course's formula; K-factor |
| Flat length of a formed segment | Fixed K-factor (≈ 0.41); K-factor |
| V-die opening (air bending) | Inside-radius percentage rule, 8 × T rule of thumb |
| Truncated cone flat pattern | Course spreadsheet, mean diameter |

Every result shows its work (formula, substituted values, result), names its method and
references, and is labeled with a **verification status** (`unverified` or `verified`), plus
whether it **reproduces the legacy** course spreadsheets. Inputs take decimals, fractions,
mixed numbers, and feet and inches (`1'-4 3/16"`). See [docs/user](docs/user/index.md).

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
* **Installing:** [docs/user/installing.md](docs/user/installing.md): the downloads, and how to open
  them the first time while they're unsigned.
* **Developers:** [docs/dev/](docs/dev/README.md) covers architecture, the decision records (ADRs), known
  issues, the engineering log, the roadmap, and the legacy-workbook transcription.
* **Contributing:** [CONTRIBUTING.md](CONTRIBUTING.md).
* **Code signing policy:** [docs/user/code-signing.md](docs/user/code-signing.md): how
  downloads are built, signed, and checked, and the app's privacy statement.
* **A wrong reference value?** See
  [Reporting a wrong or rights-encumbered value](CONTRIBUTING.md#reporting-a-wrong-or-rights-encumbered-value).

## Disclaimer

Verify results and test according to your organization's policies or industry best
practice before manufacturing. The software comes with no warranty.

## License

Code: [Apache License 2.0](LICENSE.md). Third-party names and marks are not covered by
the code license. See
[ADR-0008](docs/dev/decisions/0008-licensing-and-third-party-assets.md).
