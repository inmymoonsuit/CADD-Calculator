"""Hatchling's build hook: a wheel takes the compiled catalogs (ADR-0020 §1, ADR-0009).

The ``.po`` catalogs are committed, and the ``.mo`` files compiled from them never are,
so a wheel built from a checkout or from the sdist compiles them here, into a staging
folder, and takes each into ``caddcalc/locale``, where ``core.i18n`` reads it. An
editable install reads the source tree, where ``scripts/i18n.py compile`` puts them.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CatalogsHook(BuildHookInterface):  # type: ignore[type-arg]
    """Compile the catalogs into the wheel."""

    PLUGIN_NAME = "custom"

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        """Compile every language's catalog, and include each in the wheel."""
        if self.target_name != "wheel" or version == "editable":
            return
        sys.path.insert(0, str(Path(self.root) / "scripts"))
        import i18n as tools  # the project's catalog tool, which needs only Babel

        self._staging = Path(tempfile.mkdtemp(prefix="caddcalc-catalogs-"))
        for path in tools.compile_catalogs(self._staging):
            inside = path.relative_to(self._staging).as_posix()
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
