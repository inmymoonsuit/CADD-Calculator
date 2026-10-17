"""Sheet-metal materials: the material and temper choices, and each material's cited data.

``data/materials.toml`` states each value as its source does (ADR-0014 §3): minimum bend
radii, strengths, and K-factor starting values. This module reads it: ``listed_bands``
turns a source's listed thicknesses into bands (the maintainer's decision D4),
``load_materials`` builds the cited ``ReferenceValue`` of every value and checks them, and
``MaterialResolver`` offers the materials and tempers. A material sets no value (M2).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from functools import cached_property
from itertools import pairwise
from types import MappingProxyType
from typing import Any

from caddcalc.core import (
    Band,
    Basis,
    Choice,
    DerivedValue,
    Dimension,
    Fact,
    Note,
    NoteKind,
    Option,
    Param,
    Reference,
    ReferenceTable,
    ReferenceValue,
    SpecError,
    StartingValue,
    TableSource,
    TableSpec,
    TrustLevel,
    TypedValue,
    ValueOrigin,
)
from caddcalc.core.choices import OPTION_KEY
from caddcalc.core.units import Unit, get_unit

LISTED_TOLERANCE = Fraction(2, 100)
"""A thickness within 2% of a listed one reads at that listing (the maintainer's D4)."""

ANGLES = frozenset({"90", "not_stated"})
"""The bend angles a radius source may state: 90°, or none."""

_LENGTH = Dimension.LENGTH


@dataclass(frozen=True)
class Temper:
    """One temper a material is offered in."""

    key: str
    """The option key, keyed per material, e.g. ``"temper:6061_t6"``."""
    label: str
    """How the option reads, e.g. ``"T6"``."""
    name: str
    """The material in this temper, for notes, e.g. ``"6061-T6 aluminum"``."""


@dataclass(frozen=True)
class Material:
    """A material the domain offers: its tempers and the gauge systems it's ordered by.

    Every material has at least one temper, so every value of a quantity names the same
    conditions (ADR-0014, amendments).
    """

    key: str
    """The option key, e.g. ``"al:6061"``."""
    label: str
    group: str
    tempers: tuple[Temper, ...]
    gauges: frozenset[str]
    """The ids of the gauge systems it is ordered by, e.g. ``{"awg"}``."""
    radius_note: str = ""
    """Why no minimum radius is given, when no source gives one."""

    def name_in(self, temper: str | None) -> str:
        """Return the material's name in ``temper``, e.g. ``"6061-T6 aluminum"``."""
        return next((t.name for t in self.tempers if t.key == temper), self.label)


Multiple = tuple[Fraction, Fraction]
"""A multiple of the thickness: a range's lower and upper bounds, equal for one value."""


@dataclass(frozen=True)
class RadiusValue:
    """A source's minimum inside radius over one thickness band, as the source states it."""

    band: Band
    column: str
    """The listed thickness or band it was read at, e.g. ``"0.064 in"``."""
    value: Multiple | TypedValue
    """A multiple of T, or a radius as stated, e.g. ``"0.16 in"``."""

    def minimum(self, thickness: float) -> float:
        """Return the least radius allowed at ``thickness``, both in base units.

        A range is held to its upper bound (the maintainer's decision D2).
        """
        if isinstance(self.value, TypedValue):
            return self.value.value
        return float(self.value[1]) * thickness

    @property
    def stated(self) -> str:
        """The value as its source states it, e.g. ``"½T–1T"``, ``"2T"``, or ``"0.16 in"``."""
        if isinstance(self.value, TypedValue):
            return self.value.text
        low, high = self.value
        if high == 0:
            return "0, a sharp bend"
        if low == high:
            return f"{_times(high)}T"
        return f"{_times(low)}{'' if low == 0 else 'T'}–{_times(high)}T"


def _times(value: Fraction) -> str:
    """Return a multiple as drafting text, e.g. ``"½"``, ``"1½"``, or ``"2"``."""
    whole, part = divmod(value, 1)
    if part == 0:
        return str(whole)
    if part == Fraction(1, 2):
        return f"{whole or ''}½"
    return str(value)


@dataclass(frozen=True)
class RadiusSource:
    """One source's minimum inside radii for a material in a temper, band by band."""

    material: str
    temper: str | None
    source: TableSource
    angle: str
    """The bend angle the source states, ``"90"``, or ``"not_stated"``."""
    values: tuple[RadiusValue, ...]
    listed: bool
    """Whether the values are at listed thicknesses (D4), not at bands the source states."""
    coverage: str
    """The thicknesses it lists, e.g. ``"0.016–0.258 in"``."""
    label: str = ""
    """What the row is, when it isn't the material itself, e.g. a stand-in."""
    note: str = ""
    see_also: tuple[TableSource, ...] = ()
    """Sources the note cites, which define no value."""

    def at(self, thickness: float) -> RadiusValue | None:
        """Return the value whose band holds ``thickness``, in base units, if any."""
        return next((v for v in self.values if v.band.contains(thickness)), None)


@dataclass(frozen=True)
class Practice:
    """Bending practice that applies wherever a minimum-radius check does."""

    source: TableSource
    note: str

    @property
    def reference(self) -> Reference:
        """The citation of its source."""
        return self.source.reference


@dataclass(frozen=True)
class Strength:
    """A material's tensile strengths from one source, with their basis.

    Stored for display and later use. They are minimums or allowables, so tonnage, which
    needs an upper value, can't use them (ADR-0014 §3).
    """

    material: str
    temper: str | None
    source: TableSource
    basis: Basis
    band: Band | None
    """The thicknesses the source states them for; ``None`` when it states none."""
    thicknesses: str
    """Those thicknesses as the source states them, e.g. ``"0.010–0.249 in"``; empty for
    none."""
    ultimate: tuple[TypedValue, TypedValue]
    """F_tu, longitudinal and long transverse."""
    tensile_yield: tuple[TypedValue, TypedValue]
    """F_ty, longitudinal and long transverse."""
    note: str = ""


@dataclass(frozen=True)
class KStart:
    """A cited K-factor starting value, which the user may apply (ADR-0014 M2)."""

    value: TypedValue
    source: TableSource
    materials: frozenset[str]
    """The keys of the materials it is offered for."""
    entry: ReferenceValue
    """Its table entry, which a ``ValueOrigin`` names when the value is applied."""
    note: str = ""


@dataclass(frozen=True)
class Materials:
    """Every material the table defines, and its cited values."""

    table: ReferenceTable
    materials: tuple[Material, ...]
    by_key: Mapping[str, Material]
    radii: tuple[RadiusSource, ...]
    strengths: tuple[Strength, ...]
    k_starts: tuple[KStart, ...]
    practice: Practice
    values: tuple[ReferenceValue, ...]
    """Every value the table defines, as checked (ADR-0014 §5)."""

    def radius_sources(self, material: str, temper: str | None) -> tuple[RadiusSource, ...]:
        """Return the minimum-radius sources for ``material`` in ``temper``, in table order."""
        return tuple(r for r in self.radii if (r.material, r.temper) == (material, temper))

    def strengths_of(self, material: str, temper: str | None) -> tuple[Strength, ...]:
        """Return the strengths given for ``material`` in ``temper``."""
        return tuple(s for s in self.strengths if (s.material, s.temper) == (material, temper))

    def k_starts_for(self, material: str) -> tuple[KStart, ...]:
        """Return the K-factor starting values offered for ``material``."""
        return tuple(k for k in self.k_starts if material in k.materials)


def listed_bands(thicknesses: Sequence[Fraction], unit: Unit) -> tuple[Band, ...]:
    """Return the thickness band each listed thickness covers (the maintainer's decision D4).

    A sheet within ``LISTED_TOLERANCE`` of a listed thickness reads at that listing, which
    catches 0.063 in against a listed 0.064 in. A sheet between listings reads at the next
    one up; the loader holds each row's values non-decreasing, so that is never the less
    conservative reading. Below the first listing's tolerance or above the last's, no band
    applies. Nothing is interpolated.

    Args:
        thicknesses: The listed thicknesses, exactly, in ``unit``, in increasing order.
        unit: Their unit.

    Returns:
        One band per thickness, in base units: the first ``[t₁ − 2%, t₁ + 2%]``, and each
        later one ``(tᵢ₋₁ + 2%, tᵢ + 2%]``.

    Raises:
        SpecError: There are no thicknesses, or two are so close that their tolerances
            overlap, which includes any out of order.
    """
    if not thicknesses:
        raise SpecError("A radius row needs at least one listed thickness")
    above, below = 1 + LISTED_TOLERANCE, 1 - LISTED_TOLERANCE
    bands = [
        Band(_base(thicknesses[0] * below, unit), _base(thicknesses[0] * above, unit), _LENGTH)
    ]
    for previous, thickness in pairwise(thicknesses):
        if thickness * below <= previous * above:
            raise SpecError(
                f"Listed thicknesses {previous} and {thickness} {unit.symbol} are within "
                f"{LISTED_TOLERANCE:.0%} of each other, so a sheet between them is ambiguous"
            )
        low, high = _base(previous * above, unit), _base(thickness * above, unit)
        bands.append(Band(low, high, _LENGTH, min_inclusive=False))
    return tuple(bands)


def _base(value: Fraction, unit: Unit) -> float:
    """Return ``value`` in ``unit`` in base units, as ``parse_quantity`` would read it."""
    return float(value) * unit.factor


def load_materials(table: ReferenceTable) -> Materials:
    """Build every material and its values from the materials table, and check them.

    Raises:
        SpecError: The table's content is malformed or inconsistent.
    """
    reader = _Reader(table)
    materials = tuple(reader.material(entry) for entry in reader.entries("material"))
    by_key: dict[str, Material] = {}
    tempers: dict[str, str] = {}
    for material in materials:
        if material.key in by_key:
            raise SpecError(f"{table.name}: material {material.key!r} is declared twice")
        by_key[material.key] = material
        for temper in material.tempers:
            if temper.key in tempers:
                raise SpecError(
                    f"{table.name}: temper {temper.key!r} belongs to {tempers[temper.key]!r} "
                    f"and {material.key!r}; key each temper by its material"
                )
            tempers[temper.key] = material.key
    values: list[ReferenceValue] = []
    radii = tuple(reader.radius(e, by_key, values) for e in reader.entries("min_radius"))
    strengths = tuple(reader.strength(e, by_key, values) for e in reader.entries("strength"))
    k_starts = tuple(reader.k_start(e, by_key, values) for e in reader.entries("k_start"))
    for material in materials:
        listed = any(r.material == material.key for r in radii)
        if listed == bool(material.radius_note):
            raise SpecError(
                f"{table.name}: material {material.key!r} needs minimum-radius rows or a "
                "radius_note saying why it has none, and not both"
            )
    table.check_values(values)
    return Materials(
        table,
        materials,
        MappingProxyType(by_key),
        radii,
        strengths,
        k_starts,
        reader.practice(),
        tuple(values),
    )


class _Reader:
    """Reads the materials table's entries, naming the table and entry in every error."""

    def __init__(self, table: ReferenceTable) -> None:
        self.table = table

    def entries(self, key: str) -> list[Any]:
        value = self.table.data.get(key)
        if not isinstance(value, list):
            raise SpecError(f"{self.table.name}: {key!r} must be a list of tables")
        return value

    def practice(self) -> Practice:
        entry = self.table.data.get("practice")
        where = f"{self.table.name}: practice"
        if not isinstance(entry, dict):
            raise SpecError(f"{where} must be a table")
        _check_keys(where, entry, {"source", "note"})
        return Practice(self._source(where, entry["source"]), _text(where, entry, "note"))

    def material(self, entry: Any) -> Material:
        where = self._where("material", entry, "key")
        _check_keys(where, entry, {"key", "label", "group", "gauges", "tempers"}, {"radius_note"})
        key = _key(where, entry["key"])
        listed = entry["tempers"]
        if not isinstance(listed, list) or not listed:
            raise SpecError(f"{where} needs at least one temper, each with its name")
        tempers = tuple(self._temper(where, t) for t in listed)
        if len({t.key for t in tempers}) != len(tempers):
            raise SpecError(f"{where}: a temper repeats")
        gauges = entry["gauges"]
        if (
            not isinstance(gauges, list)
            or not gauges
            or not all(isinstance(g, str) for g in gauges)
        ):
            raise SpecError(f"{where}: gauges must list gauge system ids")
        return Material(
            key,
            _text(where, entry, "label"),
            _text(where, entry, "group"),
            tempers,
            frozenset(gauges),
            str(entry.get("radius_note", "")),
        )

    def _temper(self, where: str, entry: Any) -> Temper:
        _check_keys(f"{where} temper", entry, {"key", "label", "name"})
        return Temper(
            _key(where, entry["key"]),
            _text(where, entry, "label"),
            _text(where, entry, "name"),
        )

    def radius(
        self, entry: Any, materials: Mapping[str, Material], values: list[ReferenceValue]
    ) -> RadiusSource:
        where = self._where("min_radius", entry, "material")
        _check_keys(
            where,
            entry,
            {"material", "source", "trust", "angle", "unit"},
            {"temper", "thicknesses", "bands", "times_t", "radius", "label", "note", "see_also"},
        )
        material, temper = self._case(where, entry, materials)
        source = self._source(where, entry["source"])
        trust = _enum(where, TrustLevel, entry["trust"])
        angle = entry["angle"]
        if angle not in ANGLES:
            raise SpecError(f"{where}: angle must be one of {sorted(ANGLES)}")
        unit = _unit(where, entry["unit"])
        if ("thicknesses" in entry) == ("bands" in entry):
            raise SpecError(f"{where} needs thicknesses or bands, not both")
        if "thicknesses" in entry:
            listed = [_fraction(where, t) for t in _strings(where, entry, "thicknesses")]
            bands = listed_bands(listed, unit)
            texts = _strings(where, entry, "thicknesses")
            columns = [f"{t} {unit.symbol}" for t in texts]
            coverage = f"{texts[0]}–{texts[-1]} {unit.symbol}"
        else:
            bands, columns, coverage = self._bands(where, entry["bands"], unit)
        stated = self._radii(where, entry, unit, len(bands))
        radius_values = tuple(
            RadiusValue(band, column, value)
            for band, column, value in zip(bands, columns, stated, strict=True)
        )
        _check_rising(where, radius_values)
        conditions = {"material": material.key, "angle": angle}
        if temper is not None:
            conditions["temper"] = temper
        for value in radius_values:
            values.extend(_radius_values(value, source.id, trust, conditions))
        return RadiusSource(
            material.key,
            temper,
            source,
            angle,
            radius_values,
            "thicknesses" in entry,
            coverage,
            str(entry.get("label", "")),
            str(entry.get("note", "")),
            tuple(
                self._source(where, s) for s in _strings(where, entry, "see_also", required=False)
            ),
        )

    def _bands(
        self, where: str, entries: Any, unit: Unit
    ) -> tuple[tuple[Band, ...], list[str], str]:
        if not isinstance(entries, list) or not entries:
            raise SpecError(f"{where}: bands must be a list of tables")
        bands: list[Band] = []
        columns: list[str] = []
        runs: list[list[str]] = []
        for entry in entries:
            _check_keys(f"{where} band", entry, {"min", "max"}, {"min_inclusive", "max_inclusive"})
            low, high = (_fraction(where, entry[k]) for k in ("min", "max"))
            low_in, high_in = (entry.get(k, True) for k in ("min_inclusive", "max_inclusive"))
            if not isinstance(low_in, bool) or not isinstance(high_in, bool):
                raise SpecError(f"{where}: a band's inclusivity must be true or false")
            bands.append(Band(_base(low, unit), _base(high, unit), _LENGTH, low_in, high_in))
            if low_in:
                columns.append(f"{entry['min']}–{entry['max']} {unit.symbol}")
            else:
                columns.append(f"over {entry['min']} to {entry['max']} {unit.symbol}")
            if runs and runs[-1][-1] == entry["min"]:
                runs[-1].append(entry["max"])
            else:
                runs.append([entry["min"], entry["max"]])
        coverage = " and ".join(f"{run[0]}–{run[-1]} {unit.symbol}" for run in runs)
        return tuple(bands), columns, coverage

    def _radii(
        self, where: str, entry: Mapping[str, Any], unit: Unit, count: int
    ) -> list[Multiple | TypedValue]:
        if ("times_t" in entry) == ("radius" in entry):
            raise SpecError(f"{where} needs times_t or radius, not both")
        forms: list[Multiple | TypedValue] = []
        if "radius" in entry:
            for text in _strings(where, entry, "radius"):
                _fraction(where, text)
                forms.append(TypedValue.parse(f"{text} {unit.symbol}", _LENGTH))
        else:
            ranges = entry["times_t"]
            if not isinstance(ranges, list):
                raise SpecError(f"{where}: times_t must be a list")
            for bounds in ranges:
                if not isinstance(bounds, list) or len(bounds) not in (1, 2):
                    raise SpecError(f"{where}: each times_t is [value] or [low, high]")
                low, high = _fraction(where, bounds[0]), _fraction(where, bounds[-1])
                if low > high:
                    raise SpecError(f"{where}: a range's lower bound is above its upper")
                forms.append((low, high))
        if len(forms) != count:
            raise SpecError(f"{where}: {len(forms)} values for {count} thicknesses")
        return forms

    def strength(
        self, entry: Any, materials: Mapping[str, Material], values: list[ReferenceValue]
    ) -> Strength:
        where = self._where("strength", entry, "material")
        _check_keys(
            where,
            entry,
            {"material", "source", "basis", "trust", "f_tu", "f_ty"},
            {"temper", "unit", "thickness", "note"},
        )
        material, temper = self._case(where, entry, materials)
        source = self._source(where, entry["source"])
        basis = _enum(where, Basis, entry["basis"])
        if basis not in (Basis.SPEC_MINIMUM, Basis.A_BASIS):
            raise SpecError(f"{where}: a strength's basis is a specification minimum or A-basis")
        trust = _enum(where, TrustLevel, entry["trust"])
        band, thicknesses = None, ""
        if "thickness" in entry:
            _check_keys(f"{where} thickness", entry["thickness"], {"max"}, {"min"})
            unit = _unit(where, entry.get("unit"))
            low = _fraction(where, entry["thickness"].get("min", "0"))
            high = _fraction(where, entry["thickness"]["max"])
            band = Band(_base(low, unit), _base(high, unit), _LENGTH)
            stated = entry["thickness"]
            thicknesses = (
                f"{stated['min']}–{stated['max']} {unit.symbol}"
                if "min" in stated
                else f"up to {stated['max']} {unit.symbol}"
            )
        elif "unit" in entry:
            raise SpecError(f"{where}: unit goes with thickness")
        pairs = {k: self._pair(where, entry[k]) for k in ("f_tu", "f_ty")}
        conditions = {"material": material.key}
        if temper is not None:
            conditions["temper"] = temper
        for name, pair in pairs.items():
            for direction, stated in zip(("l", "lt"), pair, strict=True):
                values.append(
                    ReferenceValue(
                        stated.value,
                        source.id,
                        basis,
                        trust,
                        stated=stated,
                        quantity=f"{name}_{direction}",
                        band=band,
                        conditions=conditions,
                    )
                )
        return Strength(
            material.key,
            temper,
            source,
            basis,
            band,
            thicknesses,
            pairs["f_tu"],
            pairs["f_ty"],
            str(entry.get("note", "")),
        )

    def _pair(self, where: str, entry: Any) -> tuple[TypedValue, TypedValue]:
        _check_keys(f"{where} strength", entry, {"l", "lt"})
        pair = tuple(
            TypedValue.parse(_string(where, entry[k]), Dimension.STRESS) for k in ("l", "lt")
        )
        return pair[0], pair[1]

    def k_start(
        self, entry: Any, materials: Mapping[str, Material], values: list[ReferenceValue]
    ) -> KStart:
        where = self._where("k_start", entry, "source")
        _check_keys(where, entry, {"value", "source", "materials"}, {"note"})
        source = self._source(where, entry["source"])
        stated = TypedValue.parse(_string(where, entry["value"]), Dimension.RATIO)
        offered = _strings(where, entry, "materials")
        unknown = sorted(set(offered) - set(materials))
        if unknown:
            raise SpecError(f"{where}: unknown materials {unknown}")
        # K is never trusted beyond a rule of thumb, whatever the table says (ADR-0014 §1).
        value = ReferenceValue(
            stated.value,
            source.id,
            Basis.RULE_OF_THUMB,
            TrustLevel.RULE_OF_THUMB,
            stated=stated,
            quantity="k_start",
        )
        values.append(value)
        return KStart(stated, source, frozenset(offered), value, str(entry.get("note", "")))

    def _case(
        self, where: str, entry: Mapping[str, Any], materials: Mapping[str, Material]
    ) -> tuple[Material, str | None]:
        material = materials.get(entry["material"])
        if material is None:
            raise SpecError(f"{where}: no material {entry['material']!r}")
        temper = entry.get("temper")
        offered = [t.key for t in material.tempers]
        if (temper is None and offered) or (temper is not None and temper not in offered):
            raise SpecError(f"{where}: {material.key!r} has tempers {offered}, not {temper!r}")
        return material, temper

    def _source(self, where: str, source: Any) -> TableSource:
        if not isinstance(source, str) or source not in self.table.sources:
            raise SpecError(f"{where} cites {source!r}, which isn't a declared source")
        return self.table.sources[source]

    def _where(self, kind: str, entry: Any, key: str) -> str:
        named = entry.get(key, "?") if isinstance(entry, dict) else "?"
        return f"{self.table.name}: {kind} {named!r}"


def _radius_values(
    value: RadiusValue, source: str, trust: TrustLevel, conditions: Mapping[str, str]
) -> Iterable[ReferenceValue]:
    """Yield the cited values one radius gives: a radius, a multiple, or a range's bounds."""
    if isinstance(value.value, TypedValue):
        forms = [("min_radius", value.value)]
    else:
        low, high = value.value
        bounds = [("min_radius_t", high)]
        if low != high:
            bounds = [("min_radius_t_low", low), ("min_radius_t_high", high)]
        forms = [(q, TypedValue.parse(str(b), Dimension.RATIO)) for q, b in bounds]
    for quantity, stated in forms:
        yield ReferenceValue(
            stated.value,
            source,
            Basis.RECOMMENDED_MINIMUM,
            trust,
            stated=stated,
            quantity=quantity,
            band=value.band,
            conditions=conditions,
        )


def _check_rising(where: str, values: Sequence[RadiusValue]) -> None:
    """Hold a row's values non-decreasing with thickness, which D4's next-up rule needs."""
    for previous, value in pairwise(values):
        if isinstance(value.value, TypedValue) and isinstance(previous.value, TypedValue):
            falls = value.value.value < previous.value.value
        elif isinstance(value.value, tuple) and isinstance(previous.value, tuple):
            falls = any(b < a for a, b in zip(previous.value, value.value, strict=True))
        else:
            raise SpecError(f"{where}: a row mixes radii and multiples of T")
        if falls:
            raise SpecError(f"{where}: the value at {value.column} is below the one before it")


def _check_keys(
    where: str, entry: Any, required: Iterable[str], optional: Iterable[str] = ()
) -> None:
    if not isinstance(entry, dict):
        raise SpecError(f"{where} must be a table")
    unknown = sorted(set(entry) - set(required) - set(optional))
    missing = sorted(set(required) - set(entry))
    if unknown or missing:
        raise SpecError(f"{where}: unknown keys {unknown}, missing {missing}")


def _key(where: str, value: Any) -> str:
    if not isinstance(value, str) or not OPTION_KEY.fullmatch(value):
        raise SpecError(f"{where}: {value!r} isn't an option key like 'group:item'")
    return value


def _text(where: str, entry: Mapping[str, Any], key: str) -> str:
    value = entry[key]
    if not isinstance(value, str) or not value.strip():
        raise SpecError(f"{where} needs a {key}")
    return value


def _string(where: str, value: Any) -> str:
    if not isinstance(value, str):
        raise SpecError(f'{where}: write {value!r} as exact text, e.g. "0.064"')
    return value


def _strings(where: str, entry: Mapping[str, Any], key: str, *, required: bool = True) -> list[str]:
    value = entry.get(key, None if required else [])
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise SpecError(f"{where}: {key} must be a list of text")
    return value


def _fraction(where: str, text: Any) -> Fraction:
    """Read exact text, e.g. ``"0.064"`` or ``"3/2"``. A TOML float is refused."""
    try:
        value = Fraction(_string(where, text))
    except (ValueError, ZeroDivisionError):
        raise SpecError(f"{where}: {text!r} isn't a number") from None
    if value < 0:
        raise SpecError(f"{where}: {text!r} must be 0 or more")
    return value


def _unit(where: str, symbol: Any) -> Unit:
    unit = get_unit(_string(where, symbol))
    if unit.dimension is not _LENGTH:
        raise SpecError(f"{where}: unit {symbol!r} isn't a length unit")
    return unit


def _enum[E: (Basis, TrustLevel)](where: str, enum: type[E], value: Any) -> E:
    try:
        return enum(value)
    except ValueError:
        raise SpecError(f"{where}: {value!r} isn't one of {[m.value for m in enum]}") from None


MATERIAL_TABLE = TableSpec(
    "caddcalc.calculators.sheet_metal",
    "data/materials.toml",
    frozenset({"material", "min_radius", "practice", "strength", "k_start"}),
    lambda table: load_materials(table).values,
    frozenset(
        {"min_radius", "min_radius_t", "min_radius_t_low", "min_radius_t_high", "k_start"}
        | {"f_tu_l", "f_tu_lt", "f_ty_l", "f_ty_lt"}
    ),
)
"""The materials table, as ``caddcalc.calculators.REFERENCE_TABLES`` lists it."""

MATERIAL = Choice(
    "material",
    "Material",
    help=(
        "The sheet's material. Bend results then check the inside radius against its cited "
        "minimum bend radius. It sets no value: the thickness and K-factor stay as you set them."
    ),
)
"""The sheet-metal domain's material choice. Its option keys, e.g. ``"al:6061"``, are public."""

TEMPER = Choice(
    "temper",
    "Temper",
    help="The material's temper. A material offered in one temper has it selected.",
    depends_on=(MATERIAL.key,),
)
"""The temper choice, which depends on the material. Its keys, e.g. ``"temper:t6"``, are public."""


class MaterialResolver:
    """The material and temper choices' options, from the materials table.

    A material derives no setting value (ADR-0014 M2): it informs result checks and offers
    cited starting values, and the user's own values stay in charge. The table loads on
    first use and is kept for the life of the process.
    """

    def __init__(self, k_setting: Param, spec: TableSpec = MATERIAL_TABLE) -> None:
        """Offer the materials of ``spec``'s table, and their K starting values for a setting."""
        self._k_setting = k_setting
        self._spec = spec

    @cached_property
    def materials(self) -> Materials:
        """Every material, loaded and checked."""
        return load_materials(self._spec.load())

    def options(self, choice: str, parents: Mapping[str, str]) -> Sequence[Option]:
        """Return the materials, grouped, or the chosen material's tempers.

        A material with one temper marks it as the default, so choosing the material
        selects it.
        """
        if choice == MATERIAL.key:
            return tuple(Option(m.key, m.label, m.group) for m in self.materials.materials)
        if choice != TEMPER.key or MATERIAL.key not in parents:
            return ()
        tempers = self.materials.by_key[parents[MATERIAL.key]].tempers
        return tuple(Option(t.key, t.label, default=len(tempers) == 1) for t in tempers)

    def derive(self, _selections: Mapping[str, str]) -> Mapping[str, DerivedValue]:
        """Return nothing: a material sets no value (ADR-0014 M2)."""
        return MappingProxyType({})

    def facts(self, selections: Mapping[str, str]) -> Sequence[Fact]:
        """Return the chosen material's facts: its minimum-radius rule, practice, strengths.

        Bending practice shows here whenever a referenced check applies to the material,
        though results carry it only beside a limit-exceeded note (ADR-0014, amendments).
        """
        if MATERIAL.key not in selections:
            return ()
        data = self.materials
        material = data.by_key[selections[MATERIAL.key]]
        temper = selections.get(TEMPER.key)
        name = material.name_in(temper)
        facts: list[Fact] = []
        sources = data.radius_sources(material.key, temper)
        if material.radius_note:
            facts.append(Fact("Minimum inside radius", material.radius_note))
        elif sources:
            facts.append(_radius_fact(name, sources))
            facts.append(
                Fact("Bending practice", data.practice.note, references=(data.practice.reference,))
            )
        facts.extend(
            _strength_fact(strength) for strength in data.strengths_of(material.key, temper)
        )
        return tuple(facts)

    def starting_values(self, selections: Mapping[str, str]) -> Sequence[StartingValue]:
        """Return the K-factor starting values cited for the chosen material."""
        if MATERIAL.key not in selections:
            return ()
        table = self.materials.table
        return tuple(
            StartingValue(
                self._k_setting.key,
                k.value,
                ValueOrigin.of(table, k.entry, starting_value_note(k)),
                f"{k.value.text}, {short(k.source)}",
            )
            for k in self.materials.k_starts_for(selections[MATERIAL.key])
        )


def short(source: TableSource) -> str:
    """Return how labels and note texts name a source's publication, e.g. ``"AC 43.13-1B"``."""
    return source.publication.short_title or source.publication.title


def and_list(items: Iterable[str]) -> str:
    """Join phrases as prose: ``"a"``, ``"a and b"``, or ``"a, b, and c"``."""
    words = list(items)
    if len(words) < 3:
        return " and ".join(words)
    return f"{', '.join(words[:-1])}, and {words[-1]}"


def starting_value_note(k: KStart) -> Note:
    """Return the prompt results carry while an applied K starting value is in use (M2)."""
    return Note(
        NoteKind.WARNING,
        f"K = {k.value.text} is a starting value from {short(k.source)}. Confirm it with a "
        "test bend in your material and tooling before production.",
        references=(k.source.reference,),
    )


def _radius_fact(name: str, sources: Sequence[RadiusSource]) -> Fact:
    """Say how a material's bends are checked, and what each source lists."""
    cited = and_list(short(s.source) for s in sources)
    rule = f"Bends up to 90° in {name} are checked against {cited}"
    if len(sources) > 1:
        rule += "; where they differ, the larger governs"
    parts = [f"{rule}."]
    if any(
        isinstance(v.value, tuple) and v.value[0] != v.value[1] for s in sources for v in s.values
    ):
        parts.append("A range is checked at its upper bound.")
    for source in sources:
        label = f" ({source.label})" if source.label else ""
        parts.append(f"{short(source.source)} lists {source.coverage}{label}.")
        if source.note:
            parts.append(source.note)
    references = [s.source.reference for s in sources]
    references += [extra.reference for s in sources for extra in s.see_also]
    return Fact("Minimum inside radius", " ".join(parts), references=tuple(references))


_BASIS_WORDS = {Basis.SPEC_MINIMUM: "specification minimums", Basis.A_BASIS: "A-basis allowables"}


def _strength_fact(strength: Strength) -> Fact:
    """State a material's strengths with their basis, in the display's stress unit."""
    where = f", for sheet {strength.thicknesses}" if strength.thicknesses else ""
    text = (
        "F_tu {} (L) and {} (LT); F_ty {} (L) and {} (LT): "
        f"{_BASIS_WORDS[strength.basis]}, {short(strength.source)}{where}."
    )
    if strength.note:
        text += f" {strength.note}"
    quantities = tuple(
        (value.value, Dimension.STRESS) for value in (*strength.ultimate, *strength.tensile_yield)
    )
    return Fact("Strength", text, quantities, (strength.source.reference,))
