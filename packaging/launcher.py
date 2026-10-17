"""Entry script for packaged builds of the desktop app (ADR-0009).

pyside6-deploy compiles a script rather than an entry point, so ``packaging/build.py``
copies this file into its work folder as ``CADDCalculator.py`` and compiles that.
"""

import sys

from caddcalc.gui.app import main

raise SystemExit(main(sys.argv[1:]))
