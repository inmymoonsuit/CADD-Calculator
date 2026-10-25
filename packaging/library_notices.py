"""Every native binary a packaged build bundles, and the notices that cover it (KI-016).

``build.py`` lists each shared library, extension module, and executable in a build by
its file's magic bytes, matches it to a component below by its path, and fails the build
on one that no component matches, or on a component whose texts aren't in ``licenses/``.
The list goes in the build's ``.build.json``, so what a release ships is on record per
platform. THIRD_PARTY_NOTICES.md is the index for the texts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

INTERPRETER_LICENSE = "Python-interpreter-LICENSE.txt"
"""The build's own interpreter's LICENSE.txt, copied at build time (python-build-standalone
on every platform; on Windows it carries the licenses of what it bundles too)."""

PYTHON_TEXTS = (
    INTERPRETER_LICENSE,
    "Python-LICENSE.txt",
    "Python-incorporated-software.rst",
    "OpenSSL-LICENSE.txt",
    "expat-COPYING.txt",
    "zlib-LICENSE.txt",
    "bzip2-LICENSE.txt",
    "xz-5.2-COPYING.txt",
    "xz-COPYING.0BSD.txt",
    "libffi-LICENSE.txt",
    "libuuid-COPYING.txt",
    "libedit-LICENSE.txt",
    "ncurses-COPYING.txt",
)
"""The interpreter and what python-build-standalone links into it: on Linux and macOS,
OpenSSL, expat, zlib, bzip2, liblzma, libffi, libmpdec, libuuid, libedit, ncurses, and
SQLite (public domain) are all inside ``libpython``."""

QT_TEXTS = ("LGPL-3.0.txt", "GPL-3.0.txt", "Qt-third-party.txt")

_LIB = r"(\.dll|\.pyd|\.so(\.\d+)*|\.dylib|\.abi3\.so(\.\d+)*|\.abi3(\.\d+)*\.dylib)"


@dataclass(frozen=True)
class Component:
    """What covers some of a build's binaries: a name, path patterns, and its texts."""

    name: str
    patterns: tuple[str, ...]
    texts: tuple[str, ...]

    def matches(self, relative: str) -> bool:
        """Whether ``relative`` (a build-relative POSIX path, any case) is one of ours."""
        return any(re.fullmatch(p, relative, re.IGNORECASE) for p in self.patterns)


COMPONENTS = (
    # First, so its libraries aren't taken for Qt's: they sit beside Qt's in Linux wheels.
    Component(
        "ICU (Linux: Qt Core's Unicode support)",
        (r"(.*/)?libicu(data|i18n|uc)\.so(\.\d+)*",),
        ("ICU-LICENSE.txt",),
    ),
    Component(
        "Qt and PySide6, Shiboken6",
        (
            rf"(.*/)?(lib)?qt6\w*{_LIB}",
            rf"(.*/)?(lib)?(pyside6|shiboken6)[\w.]*{_LIB}",
            rf"(.*/)?pyside6/qt\w*{_LIB}",
            rf"(.*/)?shiboken6/\w+{_LIB}",
            rf"(.*/)?(qt-plugins|plugins)/[\w-]+/(lib)?[\w-]+{_LIB}",
            r"(.*/)?qt\w+\.framework/(versions/\w+/)?qt\w+",
            # macOS: Nuitka flattens each framework's binary into Contents/MacOS as QtCore.
            r"contents/macos/qt[a-z]\w*",
        ),
        QT_TEXTS,
    ),
    Component(
        "Python (python-build-standalone) and its extension modules",
        (
            rf"(.*/)?(lib)?python3(\.?\d+)?{_LIB}",
            r"(.*/)?_?\w+\.(pyd|cpython-3\d+-[\w-]+\.so|abi3\.so)",
            # macOS: libpython becomes Contents/MacOS/Python, and the extension modules
            # sit beside it with a plain .so.
            r"contents/macos/python",
            r"contents/macos/_?\w+\.so",
        ),
        PYTHON_TEXTS,
    ),
    Component(
        "OpenSSL 3",
        (rf"(.*/)?lib(crypto|ssl)([-.]\d+)*(-x64|-arm64)?{_LIB}",),
        ("OpenSSL-LICENSE.txt",),
    ),
    Component("libffi", (rf"(.*/)?libffi([-.]\d+)*{_LIB}",), ("libffi-LICENSE.txt",)),
    Component(
        "Microsoft Visual C++ runtime (Windows)",
        (
            r"(.*/)?(vcruntime140(_1)?|msvcp140(_\w+)?|concrt140|ucrtbase)\.dll",
            r"(.*/)?api-ms-win-[\w-]+\.dll",
        ),
        ("Microsoft-Visual-C++-runtime.txt",),
    ),
    Component(
        "CADD Calculator, compiled by Nuitka",
        (r"(.*/)?caddcalculator(\.exe|\.bin)?",),
        ("Nuitka-LICENSE.txt", *PYTHON_TEXTS),
    ),
)

_MAGIC = (
    b"MZ",  # Windows PE: .exe, .dll, .pyd
    b"\x7fELF",  # Linux
    b"\xfe\xed\xfa\xce",  # Mach-O, 32- and 64-bit, both byte orders, and universal
    b"\xfe\xed\xfa\xcf",
    b"\xce\xfa\xed\xfe",
    b"\xcf\xfa\xed\xfe",
    b"\xca\xfe\xba\xbe",
)


def is_native_binary(path: Path) -> bool:
    """Whether ``path`` is an executable or shared library, by its first bytes."""
    with path.open("rb") as fh:
        head = fh.read(4)
    return any(head.startswith(magic) for magic in _MAGIC)


def component_of(relative: str) -> Component | None:
    """Return the first component that covers ``relative``, or ``None``."""
    return next((c for c in COMPONENTS if c.matches(relative)), None)


def bundled_libraries(output: Path) -> dict[str, str | None]:
    """Return each native binary in ``output``, by relative path, with its component's name.

    A binary no component covers maps to ``None``.
    """
    found: dict[str, str | None] = {}
    for path in sorted(output.rglob("*")):
        if path.is_file() and not path.is_symlink() and is_native_binary(path):
            relative = path.relative_to(output).as_posix()
            component = component_of(relative)
            found[relative] = component.name if component else None
    return found


def uncovered(libraries: dict[str, str | None]) -> list[str]:
    """Return the binaries no component covers."""
    return [path for path, component in libraries.items() if component is None]


def texts_needed(libraries: dict[str, str | None]) -> list[str]:
    """Return the license texts the components of ``libraries`` need, each once."""
    names = set(libraries.values())
    return sorted({text for c in COMPONENTS if c.name in names for text in c.texts})
