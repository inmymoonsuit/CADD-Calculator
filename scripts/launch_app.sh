#!/bin/sh
# Launch the work-in-progress desktop app from this checkout (docs/dev/launching.md).
# Usage: scripts/launch_app.sh [--branding FOLDER] [app arguments]
set -eu
PROJECT_ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)

if ! command -v uv >/dev/null 2>&1; then
    echo "uv was not found. Install it from https://docs.astral.sh/uv/ and try again." >&2
    exit 1
fi

exec uv run --project "$PROJECT_ROOT" --extra gui python "$PROJECT_ROOT/scripts/launch_app.py" "$@"
