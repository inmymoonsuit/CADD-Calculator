r"""Launch the work-in-progress desktop app from this checkout.

Start it through a wrapper, which makes uv bring the environment up to date first::

    scripts\launch_app.cmd [--branding FOLDER] [app arguments]    (Windows)
    scripts/launch_app.sh [--branding FOLDER] [app arguments]      (macOS, Linux)

Arguments the launcher doesn't recognize go to the app, e.g. ``--smoke-test``. See
docs/dev/launching.md.
"""

from __future__ import annotations

import argparse
import faulthandler
import os
import sys
import warnings
from pathlib import Path

from caddcalc import __version__
from caddcalc.gui.app import main as app_main
from caddcalc.gui.branding import ENV_VAR, BrandingError, load_branding

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    """Parse the launcher's options, then run the app with the remaining arguments.

    Returns:
        The app's exit status, or 2 if the launcher's own options are invalid.
    """
    parser = argparse.ArgumentParser(
        description="Launch the work-in-progress CADD Calculator from this checkout.",
        allow_abbrev=False,
    )
    parser.add_argument(
        "--branding",
        type=Path,
        metavar="FOLDER",
        help="run with the branding pack in FOLDER (default: the unbranded app)",
    )
    args, app_args = parser.parse_known_args(argv)

    if args.branding is None:
        # An inherited CADDCALC_BRANDING would brand the app without the user asking.
        os.environ.pop(ENV_VAR, None)
        edition = "unbranded"
    else:
        try:
            branding = load_branding(args.branding)
        except BrandingError as exc:
            print(f"launch_app: {exc}", file=sys.stderr)
            return 2
        os.environ[ENV_VAR] = str(args.branding.resolve())
        edition = f"edition: {branding.edition}"

    print(f"CADD Calculator {__version__}, work in progress ({edition})")
    print(f"Source: {PROJECT_ROOT}")
    faulthandler.enable()  # a hard crash inside Qt still prints a Python traceback
    warnings.filterwarnings("default", module=r"caddcalc(\.|$)")
    return app_main(app_args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
