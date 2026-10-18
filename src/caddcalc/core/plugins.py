"""Loading plugins: what installed packages advertise through entry points (ADR-0006).

The calculator registry and the units registry both load plugins this way, so one bad
plugin is recorded and skipped in each, never stopping the app from starting.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any, Protocol


class PluginEntryPoint(Protocol):
    """The parts of an installed package's entry point that a registry uses."""

    @property
    def name(self) -> str:
        """The entry point's name."""

    @property
    def value(self) -> str:
        """The object reference, e.g. ``"acme.tools:CALCULATORS"``."""

    def load(self) -> Any:
        """Import and return the object the entry point names."""


class EntryPointSource(Protocol):
    """Lists entry points by group, as ``importlib.metadata.entry_points`` does."""

    def __call__(self, *, group: str) -> Iterable[PluginEntryPoint]:
        """Return the entry points in ``group``."""


@dataclass
class PluginError:
    """A plugin that failed to load, and the reason."""

    source: str
    """The entry point, as ``name = value``. An item of an iterable adds its index: ``name[1]``."""
    message: str


def load_group(
    entry_points: EntryPointSource,
    group: str,
    single: type,
    register: Callable[[object], None],
) -> list[PluginError]:
    """Register what each entry point in ``group`` names, one item at a time.

    An entry point names one item, an instance of ``single``, or an iterable of items.
    Return what failed, each with its reason.
    """
    errors: list[PluginError] = []
    for ep in entry_points(group=group):
        source = f"{ep.name} = {ep.value}"
        try:
            loaded = ep.load()
            if isinstance(loaded, single):
                items = [(source, loaded)]
            else:
                items = [(f"{ep.name}[{i}] = {ep.value}", x) for i, x in enumerate(loaded)]
        except Exception as exc:  # noqa: BLE001 (isolation boundary: a plugin must never crash the app)
            errors.append(PluginError(source, str(exc)))
            continue
        for item_source, item in items:
            try:
                register(item)
            except Exception as exc:  # noqa: BLE001 (isolation boundary: one bad item must not drop the rest)
                errors.append(PluginError(item_source, str(exc)))
    return errors
