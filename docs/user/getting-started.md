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

* The **welcome screen** opens first, while the app starts, and the main window appears
  behind it a moment later. Its **ⓘ** shows About: the version, the license, and the
  disclaimer. Close it with **Esc** or the **✕** at its upper right to use the
  calculators; drag its top bar to move it. In the main window, **Help > Welcome Screen**
  shows it again, **Help > About** shows About, and **File > Exit** closes the app.
* The window opens centred, sized to fit your screen, and follows Windows' text size
  (Settings > Accessibility > Text size), read when the app starts.
* Pick a calculator on the left, or pick a family, such as **Sheet Metal**, to see the
  settings its calculators share. Rest the pointer on one to see what it does; when the
  list is too narrow for a name, the tip gives the whole name too. Drag the line between
  the list and the page to widen either.
* Choose a **Method**. Its status, such as "unverified · reproduces legacy", shows
  beside it, and its list shows each method's. **Units** (`in` or `mm`) sets the unit
  the results show in.
* Type the inputs. Each input with a unit has a **unit picker** after it: the number is
  read in the unit it shows. You can type fractions, mixed numbers and arithmetic:
  `1/8`, `1-3/16`, `2 × 1 3/16`. Results update as you type, and invalid fields are
  outlined in red. A unit typed into the field, such as `3 mm`, is refused, with a
  button that moves it into the picker. See [Units and precision](units-and-precision.md).
* Switching a picker re-reads the number you typed in the new unit, so `25` stays 25,
  now in millimeters; switching back is the undo. A value you didn't type, such as a
  default, keeps its size and is shown converted. Your first switch of a length's
  picker on a calculator carries to its other lengths' pickers.
* Results show in their own fields. Click a field's copy button to copy its value, or
  **Copy all** for every result as spreadsheet rows; see
  [Results and copying](results.md) for the other forms and the keyboard.
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
default shown by `caddcalc show`. A name is matched exactly first, then in any case, but
only where it can mean one thing: a triangle's `a` is a side and `A` an angle, and since
its `B` is an angle the calculator gives, `B=30` is refused rather than read as side `b`.
An input given twice, or one the method doesn't use, is refused too, with the method's
inputs, so nothing you typed is silently dropped.

## Language and number format

The desktop app follows your system's display language and regional format, each read
when it starts, so a change applies the next time it starts. English outside the US
gets British spelling ("millimetre"). The whole window is in one language: the first of
your display languages the app has words for, or US English, with the menus and
buttons Qt provides, such as Undo and Copy, in the same one. The command line writes in the language of
`--lang`, or of `CADDCALC_LANG`, `LANGUAGE`, `LC_ALL`, `LC_MESSAGES` or `LANG`, the first
that's set; its numbers always use ".", for scripts.
