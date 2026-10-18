"""The catalog tooling, ``scripts/i18n.py``, for tests: it isn't a package module."""

from __future__ import annotations

import importlib.util
from functools import cache
from pathlib import Path
from types import ModuleType

SCRIPT = Path(__file__).parents[1] / "scripts" / "i18n.py"


@cache
def tooling() -> ModuleType:
    """The catalog tooling script, loaded as a module."""
    spec = importlib.util.spec_from_file_location("i18n_tooling", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def shipped(folder: Path, language: str) -> Path:
    """Compile the shipped ``language`` .po into ``folder``, as the build does.

    Returns:
        ``folder``, for ``i18n.use(..., directories=[folder])``.
    """
    tools = tooling()
    po = tools.LOCALE / language / "LC_MESSAGES" / "caddcalc.po"
    tools.compile_to(tools.read(po), folder / language / "LC_MESSAGES" / "caddcalc.mo")
    return folder
