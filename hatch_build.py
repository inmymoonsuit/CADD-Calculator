"""Hatchling's build hook: a wheel takes the compiled catalogs (ADR-0020 §1, ADR-0009).

The ``.po`` catalogs are committed, and the ``.mo`` files compiled from them never are,
so a wheel built from a checkout or from the sdist compiles them here, into a staging
folder, and takes each into ``caddcalc/locale``, where ``core.i18n`` reads it. An
editable install reads the source tree, where ``scripts/i18n.py compile`` puts them.
"""

from __future__ import annotations

import importlib.util
import shutil
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

TOOL_NAME = "caddcalc_i18n_tool"
"""The catalog tool's module name here: its own, so no installed ``i18n`` stands in."""


def catalog_tool(root: Path) -> ModuleType:
    """Load the project's catalog tool, ``scripts/i18n.py``, by its path.

    Raises:
        RuntimeError: Babel, which the tool compiles with, isn't installed.
    """
    path = root / "scripts" / "i18n.py"
    spec = importlib.util.spec_from_file_location(TOOL_NAME, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"can't load the catalog tool, {path}")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except ModuleNotFoundError as exc:
        if (exc.name or "").partition(".")[0] != "babel":
            raise
        raise RuntimeError(
            "compiling the catalogs needs Babel, a build requirement in pyproject.toml: "
            "build with isolation, the default, or install babel first"
        ) from exc
    return module


class CatalogsHook(BuildHookInterface):  # type: ignore[type-arg]
    """Compile the catalogs into the wheel."""

    PLUGIN_NAME = "custom"

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        """Compile every language's catalog, and include each in the wheel.

        The tool fails when there's no ``.po`` to compile, so a wheel never ships
        without its catalogs.
        """
        if self.target_name != "wheel" or version == "editable":
            return
        tool = catalog_tool(Path(self.root))
        staging = Path(tempfile.mkdtemp(prefix="caddcalc-catalogs-"))
        try:
            written = tool.compile_catalogs(staging)
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)  # a failed build never finalizes
            raise
        self._staging = staging
        for path in written:
            inside = path.relative_to(staging).as_posix()
            build_data["force_include"][str(path)] = f"caddcalc/locale/{inside}"

    def finalize(
        self,
        version: str,  # noqa: ARG002 (hatchling's signature)
        build_data: dict[str, Any],  # noqa: ARG002
        artifact_path: str,  # noqa: ARG002
    ) -> None:
        """Remove the staging folder, once the wheel holds its files."""
        staging = getattr(self, "_staging", None)
        if staging is not None:
            shutil.rmtree(staging, ignore_errors=True)
