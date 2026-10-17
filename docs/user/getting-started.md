# Getting started

> Installers for Windows, macOS, and Linux are planned (roadmap 0.3). Until then, run
> from source as described below.

## Run from source

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/).
2. Get the code and start the app:

```bash
git clone https://github.com/inmymoonsuit/CADD-Calculator.git
cd CADD-Calculator
uv sync --extra gui
uv run caddcalc-gui
```

## The desktop app

* Pick a calculator on the left, or pick a family, such as **Sheet Metal**, to see the
  settings its calculators share.
* Choose a **Method** (the status shows in brackets) and **Units** (`in` or `mm`).
* Type the inputs. Results update as you type, and invalid fields are outlined in red.
  You can type units and fractions: `1/8`, `1-1/2"`, `3 mm`.
* Switching units re-expresses the values you've entered. The part doesn't change, and
  what you typed comes back exactly when you switch back.
* **Load course example** fills a calculator's inputs with the course's example values.
* Family settings, such as Sheet Metal thickness, fill the fields that share them until
  you type over them; see [Family settings](calculators/sheet-metal.md#family-settings).

## The command line

```bash
uv run caddcalc list                                   # all calculators
uv run caddcalc show sheet_metal.bend_allowance         # inputs, outputs, methods
uv run caddcalc run sheet_metal.bend_allowance T=0.1046 R=0.156 A=90 --method course
uv run caddcalc run sheet_metal.segment_flat_length T=3mm R=4mm FVD=50mm A1=90 A2=90 --units mm
uv run caddcalc run sheet_metal.bend_allowance A=45 --fraction 64   # also show nearest 1/64"
uv run caddcalc run sheet_metal.truncated_cone_layout --json        # machine-readable
```

Inputs can be given by symbol (`T`) or key (`thickness`). Anything you leave out uses the
default shown by `caddcalc show`.
