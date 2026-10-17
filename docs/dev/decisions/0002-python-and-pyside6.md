# ADR-0002: Python 3.12+ with PySide6 (Qt) for the desktop app

* **Status:** Accepted
* **Date:** 2026-10-16

## Context

Requirements:

* An installable desktop app for **Windows, macOS, and Linux**.
* The core value is **engineering formulas**. They must be easy to read, review, and test,
  and easy for drafters and engineers (not only software developers) to contribute.
* It should be **extensible** with new domains: structural, tolerancing, threads, piping.
* The calculation core should be reusable in other tools (scripts, a future web version,
  the maintainer's other CAD projects, which are also Python).
* It is maintained by one person to start, so tooling cost matters.

## Decision

* **Language:** Python, minimum 3.12, tested on 3.12 and the newest release. The 3.12
  floor also lets the core run inside Blender, whose 5.2.2 release bundles Python 3.13.
* **GUI toolkit:** PySide6, the official Qt for Python (LGPL-3.0), installed as the
  lighter `PySide6-Essentials` wheel. The GUI is an optional extra (`cadd-calculator[gui]`).
* **Tooling:** `uv` for environments and the lockfile, `hatchling` as the build backend,
  `pytest`, `ruff` (lint and format), and `mypy --strict`.
* **"Compiled" distribution:** handled by packaging (ADR-0009). Nuitka compiles Python to C
  and is what Qt's own `pyside6-deploy` uses.

## Consequences

* Formulas read almost like the textbook. The engineering community knows Python well,
  and FreeCAD, for example, uses Python with Qt.
* The calculation library can be used without the GUI, from scripts, notebooks, or other apps.
* Installers are larger (roughly 60 to 120 MB) and start more slowly than a native C++/C# binary.
  This is acceptable for a calculator.
* Python is dynamically typed. We compensate with `mypy --strict` and tests.
* Code signing and notarization are still needed per platform (ADR-0009).

## Alternatives considered

* **C# / .NET with Avalonia UI**: compiled, smaller and faster binaries, and strong typing.
  It was rejected because of the smaller engineering and scripting community, its core is
  less reusable from Python-based CAD tools, and the .NET SDK isn't set up on the
  development machine. It's a reasonable choice, and this ADR could be revisited.
* **C++ with Qt**: the best performance, but by far the hardest for contributors.
  Calculators don't need the speed.
* **Rust with Tauri, egui, or Slint**: small binaries, but a steep learning curve and a small
  engineering-formula ecosystem.
* **Electron or Tauri with a TypeScript UI**: good UI tooling and a natural path to a web
  version, but floating-point engineering code in JavaScript has a weaker testing and
  units ecosystem, and Electron bundles are heavy.
* **Tkinter**: built into Python, but dated widgets and weak high-DPI and theming support.
* **Excel/VBA (the 2024 approach)**: Windows and Excel only, hard to test, version, or
  distribute as open source.

## Revisit when

* Startup time or installer size becomes a real user complaint.
* A web or mobile version becomes the priority. The pure-Python core can then run in the
  browser via Pyodide, or be ported.
