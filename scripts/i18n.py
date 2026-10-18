"""Keep the translation catalogs in step with the code (ADR-0020 §1), with Babel.

    uv run python scripts/i18n.py extract    # the template, from every marked string
    uv run python scripts/i18n.py init LANG  # a new language's .po, e.g. de or pt_BR
    uv run python scripts/i18n.py update     # each language's .po, from the template
    uv run python scripts/i18n.py compile    # each .po to its .mo, beside it
    uv run python scripts/i18n.py check      # exit 1 if any catalog is out of step

The template (``caddcalc.pot``) and each language's ``.po`` are committed; ``.mo`` files are
compiled, in the build and in the tests, and never committed. Babel is a development
dependency only: the app reads ``.mo`` files with the standard library.
"""

from __future__ import annotations

import copy
import datetime
import io
import re
import sys
from collections.abc import Iterator
from pathlib import Path
from string import Formatter

from babel.messages.catalog import Catalog, Message
from babel.messages.extract import DEFAULT_KEYWORDS, extract_from_dir
from babel.messages.mofile import write_mo
from babel.messages.pofile import read_po, write_po

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "caddcalc"
LOCALE = SOURCE / "locale"
TEMPLATE = LOCALE / "caddcalc.pot"
DOMAIN = "caddcalc"
PROJECT = "CADD Calculator"
TEMPLATE_DATE = datetime.datetime(2026, 10, 18, tzinfo=datetime.UTC)
"""The template's fixed creation date, so extracting again changes only what changed."""
HEADER = (
    "# Translations template for CADD Calculator.\n"
    "# Distributed under the project's license, Apache-2.0. See CONTRIBUTING.md,\n"
    '# "Translating", and ADR-0020.'
)
METHODS = [("**.py", "python")]
KEYWORDS = {**DEFAULT_KEYWORDS, "NP_": ((1, "c"), 2, 3)}
"""Babel's defaults: ``_``, ``N_``, ``ngettext``, ``pgettext``, ``npgettext`` and gettext's
other names (ADR-0020 §1); and ``NP_``, which marks a singular and plural pair in a
context, as ``npgettext`` takes them."""


def extract() -> Catalog:
    """Return the template: every marked string in the package, sorted, without line numbers."""
    catalog = Catalog(
        project=PROJECT,
        domain=DOMAIN,
        header_comment=HEADER,
        copyright_holder="CADD Calculator contributors",
        msgid_bugs_address="https://github.com/inmymoonsuit/CADD-Calculator/issues",
        creation_date=TEMPLATE_DATE,
    )
    for filename, lineno, message, comments, context in extract_from_dir(
        SOURCE,
        METHODS,
        keywords=KEYWORDS,
        comment_tags=("Translators:",),
        strip_comment_tags=True,
    ):
        catalog.add(
            message,
            locations=[(f"src/caddcalc/{Path(filename).as_posix()}", lineno)],
            auto_comments=comments,
            context=context,
        )
    return catalog


def po_text(catalog: Catalog) -> bytes:
    """Return ``catalog`` as .po text, sorted and without line numbers: a move isn't a change."""
    out = io.BytesIO()
    write_po(out, catalog, sort_output=True, include_lineno=False, width=100)
    return out.getvalue()


def init(language: str) -> Path:
    """Start ``language``'s .po from the template, with nothing translated; return its path.

    Raises:
        FileExistsError: The language has a .po already; ``update`` keeps it current.
    """
    path = LOCALE / language / "LC_MESSAGES" / f"{DOMAIN}.po"
    if path.exists():
        raise FileExistsError(f"{path} exists; run: python scripts/i18n.py update")
    catalog = Catalog(
        locale=language,
        domain=DOMAIN,
        project=PROJECT,
        header_comment=f"# {language} translations for {PROJECT}. See CONTRIBUTING.md.",
        copyright_holder="CADD Calculator contributors",
        msgid_bugs_address="https://github.com/inmymoonsuit/CADD-Calculator/issues",
        creation_date=TEMPLATE_DATE,
        revision_date=TEMPLATE_DATE,
        last_translator="CADD Calculator contributors",
        language_team=language,
        fuzzy=False,
    )
    catalog.update(read(TEMPLATE))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(po_text(catalog))
    return path


def languages() -> Iterator[Path]:
    """Yield each language's .po file, in ``locale/<language>/LC_MESSAGES``."""
    yield from sorted(LOCALE.glob(f"*/LC_MESSAGES/{DOMAIN}.po"))


def read(path: Path) -> Catalog:
    """Return the catalog in the .po or .pot file at ``path``."""
    with path.open("rb") as stream:
        return read_po(stream, domain=DOMAIN)


def keys(catalog: Catalog) -> set[tuple[str, str | None]]:
    """Return each message's id and context; a plural message is keyed by its singular."""
    return {(_singular(m), m.context) for m in catalog if m.id}


def _singular(message: Message) -> str:
    return message.id[0] if isinstance(message.id, tuple | list) else message.id


def placeholders(text: str) -> set[str]:
    """Return the named fields in ``text``, such as ``{value}``; a text with none, none.

    A positional ``{}`` is ``""``, and unbalanced braces are ``"<unbalanced braces>"``.
    """
    try:
        return {name for _t, name, _s, _c in Formatter().parse(text) if name is not None}
    except ValueError:
        return {"<unbalanced braces>"}


PRINTF = re.compile(r"%(?:\([^)]*\))?[-#0+]*\d*(?:\.\d+)?[sdifr]")
"""A printf-style placeholder, such as ``%s`` or ``%(name)s``. A "%" in prose, as in "10%
grade", isn't one."""


def source_problems(template: Catalog) -> list[str]:
    """Return every marked text whose placeholders aren't named fields alone.

    A translation reorders the fields, so each must be named (``{value}``): a positional
    ``{}`` has nothing to keep it in its place, and a printf-style ``%s`` isn't checked
    for at all.
    """
    problems = []
    for message in template:
        if not message.id:
            continue
        sources = message.id if isinstance(message.id, tuple | list) else (message.id,)
        for source in sources:
            if "" in placeholders(source):
                problems.append(f"{source!r} has a positional {{}}; name it")
            if PRINTF.search(source):
                problems.append(f"{source!r} has a printf-style placeholder; use {{name}}")
    return problems


def placeholder_mismatches(catalog: Catalog) -> list[str]:
    """Return every translation whose placeholders differ from its source's.

    A translation may reorder ``{value}`` and ``{limit}``, never drop, add, or rename one.
    A plural's forms are checked one by one: each has its source's fields, but where the
    language has more than one form, the first, for "one", may leave out a field, as
    "one inch" leaves out the count.
    """
    problems = []
    for message in catalog:
        if not message.id or not message.string:
            continue
        sources = message.id if isinstance(message.id, tuple | list) else (message.id,)
        strings = message.string if isinstance(message.string, tuple | list) else (message.string,)
        wanted = set().union(*(placeholders(s) for s in sources))
        for form, translated in enumerate(strings):
            if not translated:
                continue
            found = placeholders(translated)
            singular = len(strings) > 1 and form == 0
            if found != wanted and not (singular and found < wanted):
                problems.append(f"{_singular(message)!r}: {translated!r} has other placeholders")
    return problems


def _forms(message: Message) -> tuple[str, ...]:
    """Return a message's translations: one, or one per plural form."""
    string = message.string
    return tuple(string) if isinstance(string, tuple | list) else (string or "",)


def translated(catalog: Catalog) -> Catalog:
    """Return ``catalog`` with only the messages it translates, every form of each.

    An untranslated message has to fall through to the next catalog, as en_CA's do to
    en_001's. Babel would compile an untranslated plural as the source text instead.
    """
    kept = copy.deepcopy(catalog)
    for message in [m for m in catalog if m.id and not all(_forms(m))]:
        kept.delete(message.id, context=message.context)
    return kept


def compile_to(catalog: Catalog, path: Path) -> None:
    """Write the messages ``catalog`` translates as a .mo file at ``path``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as stream:
        write_mo(stream, translated(catalog))


def check() -> list[str]:
    """Return what's out of step: the template, any language, or a translation's fields."""
    problems = []
    template = extract()
    if not TEMPLATE.is_file():
        return [f"{TEMPLATE.name} is missing; run: python scripts/i18n.py extract"]
    if keys(read(TEMPLATE)) != keys(template):
        problems.append(f"{TEMPLATE.name} is out of date; run: python scripts/i18n.py extract")
    problems += source_problems(template)
    for path in languages():
        catalog = read(path)
        language = path.parents[1].name
        if keys(catalog) != keys(template):
            problems.append(f"{language} is out of date; run: python scripts/i18n.py update")
        problems += [f"{language}: {p}" for p in placeholder_mismatches(catalog)]
        # A fuzzy translation is Babel's guess after the source changed: never compiled,
        # so it must be checked and confirmed, or cleared.
        problems += [
            f"{language}: {_singular(m)!r} is fuzzy; confirm or clear its translation"
            for m in catalog
            if m.id and m.fuzzy
        ]
        problems += [
            f"{language}: {_singular(m)!r} translates only some of its plural forms"
            for m in catalog
            if m.id and any(_forms(m)) and not all(_forms(m))
        ]
        try:
            write_mo(io.BytesIO(), translated(catalog))
        except Exception as exc:  # noqa: BLE001 (report any reason a catalog won't compile)
            problems.append(f"{language} won't compile: {exc}")
    return problems


def main(argv: list[str]) -> int:
    """Run ``extract``, ``update``, ``compile`` or ``check``; return the exit code."""
    command = argv[0] if argv else ""
    if command == "extract":
        TEMPLATE.parent.mkdir(parents=True, exist_ok=True)
        TEMPLATE.write_bytes(po_text(extract()))
    elif command == "init" and len(argv) == 2:
        print(init(argv[1]).relative_to(ROOT))
    elif command == "update":
        template = read(TEMPLATE)
        for path in languages():
            catalog = read(path)
            catalog.update(template)
            path.write_bytes(po_text(catalog))
    elif command == "compile":
        for path in languages():
            compile_to(read(path), path.with_suffix(".mo"))
    elif command == "check":
        problems = check()
        for problem in problems:
            print(problem)
        return 1 if problems else 0
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
