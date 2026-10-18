"""The wheel's build hook, ``hatch_build.py`` (ADR-0020's i5 and i5b).

It loads the catalog tool by its path, names Babel when it's missing, and fails rather
than build a wheel with no catalogs. Hatchling is the build backend, not a test
dependency, so these tests give the hook the part of its interface it uses.
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
INTERFACE = "hatchling.builders.hooks.plugin.interface"


class _Interface:
    """``BuildHookInterface``, as far as the hook uses it."""

    def __init__(self, root: Path, target_name: str = "wheel") -> None:
        self.root = str(root)
        self.target_name = target_name


@pytest.fixture
def hook(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """``hatch_build.py``, loaded over the stand-in interface."""
    parts = INTERFACE.split(".")
    for depth in range(1, len(parts) + 1):
        name = ".".join(parts[:depth])
        monkeypatch.setitem(sys.modules, name, ModuleType(name))
    sys.modules[INTERFACE].BuildHookInterface = _Interface  # type: ignore[attr-defined]
    spec = importlib.util.spec_from_file_location("hatch_build_under_test", ROOT / "hatch_build.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_tool_loads_by_its_path_under_its_own_name(
    hook: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """S&R's i5 note: an installed ``i18n``, as python-i18n has, can't stand in for it."""
    other = ModuleType("i18n")
    monkeypatch.setitem(sys.modules, "i18n", other)
    tool = hook.catalog_tool(ROOT)
    assert tool.__name__ == hook.TOOL_NAME
    assert callable(tool.compile_catalogs)
    assert sys.modules["i18n"] is other


def test_a_missing_babel_is_named(hook: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """Built without isolation and without Babel, the hook says what it needs."""
    for name in [n for n in sys.modules if n == "babel" or n.startswith("babel.")]:
        monkeypatch.setitem(sys.modules, name, None)
    monkeypatch.setitem(sys.modules, "babel", None)
    with pytest.raises(RuntimeError, match="needs Babel"):
        hook.catalog_tool(ROOT)


def test_a_wheel_takes_each_compiled_catalog(hook: ModuleType) -> None:
    """Each language's .mo goes into ``caddcalc/locale``; the staging folder goes after."""
    for target, version in (("sdist", "standard"), ("wheel", "editable")):
        skipped: dict[str, dict[str, str]] = {"force_include": {}}
        hook.CatalogsHook(ROOT, target).initialize(version, skipped)
        assert skipped == {"force_include": {}}, (target, version)
    build = hook.CatalogsHook(ROOT)
    data: dict[str, dict[str, str]] = {"force_include": {}}
    build.initialize("standard", data)
    assert sorted(data["force_include"].values()) == [
        "caddcalc/locale/en_001/LC_MESSAGES/caddcalc.mo",
        "caddcalc/locale/en_CA/LC_MESSAGES/caddcalc.mo",
    ]
    assert all(Path(path).is_file() for path in data["force_include"])
    build.finalize("standard", data, "unused.whl")
    assert not build._staging.exists()


def test_no_catalog_fails_the_wheel(
    hook: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """S&R's i5 L2: with no .po, the wheel fails, rather than ship with no catalogs."""
    (tmp_path / "scripts").mkdir()
    shutil.copy2(ROOT / "scripts" / "i18n.py", tmp_path / "scripts" / "i18n.py")
    (tmp_path / "src" / "caddcalc" / "locale").mkdir(parents=True)
    staging = tmp_path / "staging"
    staging.mkdir()
    monkeypatch.setattr(hook.tempfile, "mkdtemp", lambda **_: str(staging))
    with pytest.raises(Exception, match="no catalog to compile"):
        hook.CatalogsHook(tmp_path).initialize("standard", {"force_include": {}})
    assert not staging.exists(), "a failed build never finalizes, so it cleans up"
