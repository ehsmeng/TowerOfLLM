"""Shared data format for every language in this repo.

One language lives in one top-level directory (``german/``, ``french/`` ...):

    <lang>/language.toml              language config (code, names, title, source, word count, max_reorder)
    <lang>/json/words.json            word forms in learning order (WordList)
    <lang>/json/grammar.json          grammar concepts + entry that introduces each (Grammar)
    <lang>/json/verbs.json            most common verbs with full conjugation tables (Verbs)
    <lang>/json/entries/NNNNN <form>.json   one Entry per word form, NNNNN = learning order
    <lang>/audio/NNNNN <form>.mp3     one audio file per entry (same stem as the JSON)
    <lang>/<pdf title>.pdf            rendered course

See docs/format.md for the prose spec. This module is the source of truth for
field names; it uses only the standard library.

CLI:
    python -m tools.schema validate german               # structural + cross-file checks
    python -m tools.schema validate docs/example/german  # the illustrative data set
    python -m tools.schema jsonschema [entry|words|grammar|verbs]
"""

from __future__ import annotations

import dataclasses
import json
import re
import sys
import tomllib
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, get_args, get_origin, get_type_hints

SCHEMA_VERSION = 1
MAX_SENTENCES_PER_MEANING = 10
MAX_SENTENCES_PER_ENTRY = 20
MAX_GRAMMAR_EXAMPLES = 3
ORDER_WIDTH = 5

# Coarse, language-neutral part-of-speech tags (Universal Dependencies UPOS).
POS_TAGS = {
    "ADJ", "ADP", "ADV", "AUX", "CCONJ", "DET", "INTJ", "NOUN", "NUM",
    "PART", "PRON", "PROPN", "SCONJ", "VERB", "X",
}

GRAMMAR_ID_RE = re.compile(r"^[a-z0-9_]+(\.[a-z0-9_]+)*$")


class SchemaError(ValueError):
    pass


# ---------------------------------------------------------------------------
# Data classes. Field order here is the field order written to disk.
# Every class accepts an optional `notes` string: JSON has no comments, so
# human/agent remarks go there. Notes are never rendered in the PDF.
# ---------------------------------------------------------------------------


@dataclass
class Sentence:
    text: str                                  # target-language sentence
    en: str                                    # English translation
    grammar_notes: list[str] = field(default_factory=list)  # grammar.json ids introduced here
    notes: str | None = None


@dataclass
class Meaning:
    gloss: str                                 # short English gloss, e.g. "the (fem./plural)"
    base: str                                  # lemma / dictionary form, e.g. "sein" for "war"
    pos: str                                   # UPOS tag, see POS_TAGS
    morph: str | None = None                   # free-text morphology, e.g. "past, 1st/3rd sg."
    sentences: list[Sentence] = field(default_factory=list)
    notes: str | None = None


@dataclass
class Entry:
    schema_version: int
    language: str                              # ISO 639-1 code, e.g. "de"
    order: int                                 # 1-based learning position (drives filenames)
    form: str                                  # the word form exactly as taught (NFC)
    base: str                                  # primary lemma (= meanings[0].base usually)
    translation: str                           # headline English translation
    meanings: list[Meaning]
    notes: str | None = None


@dataclass
class WordListItem:
    order: int                                 # learning position, 1..N contiguous in array order
    form: str
    frequency_rank: int                        # position in the source frequency list
    count: int                                 # occurrences in the source corpus
    base: str | None = None                    # filled once known; may be null at list-build time
    notes: str | None = None


@dataclass
class WordList:
    schema_version: int
    language: str
    source: str                                # human-readable source description
    words: list[WordListItem]
    notes: str | None = None


@dataclass
class Example:
    text: str                                  # target-language sentence using the concept
    en: str                                    # English translation
    notes: str | None = None


@dataclass
class GrammarConcept:
    id: str                                    # dotted id, e.g. "article.definite.fem"
    title: str                                 # short heading for the PDF
    explanation: str                           # English explanation shown on first use
    first_entry: int                           # order of the entry whose sentence introduces it
    related: list[str] = field(default_factory=list)  # other concept ids worth cross-referencing
    examples: list[Example] = field(default_factory=list)  # target 3; only forms with order <= first_entry
    notes: str | None = None


@dataclass
class Grammar:
    schema_version: int
    language: str
    concepts: list[GrammarConcept]
    notes: str | None = None


@dataclass
class VerbTense:
    tense: str                                 # language-defined id, e.g. "praesens", "konjunktiv_ii"
    label: str                                 # heading for the PDF table, e.g. "Präsens (present)"
    forms: dict[str, str]                      # person/number label -> form, in display order


@dataclass
class Verb:
    base: str                                  # infinitive / lemma, as in words.json `base`
    translation: str                           # e.g. "to be"
    total_count: int                           # summed count of all its forms in words.json
    tenses: list[VerbTense]
    participles: dict[str, str] = field(default_factory=dict)  # e.g. {"present": "seiend", "past": "gewesen"}
    notes: str | None = None


@dataclass
class Verbs:
    schema_version: int
    language: str
    verbs: list[Verb]                          # sorted by total_count, descending
    notes: str | None = None


# ---------------------------------------------------------------------------
# Generic strict (de)serialisation: unknown keys and wrong types fail loud.
# ---------------------------------------------------------------------------


def _check_type(value: Any, tp: Any, where: str) -> Any:
    origin = get_origin(tp)
    if origin is list:
        (inner,) = get_args(tp)
        if not isinstance(value, list):
            raise SchemaError(f"{where}: expected list, got {type(value).__name__}")
        return [_check_type(v, inner, f"{where}[{i}]") for i, v in enumerate(value)]
    if origin is dict:
        kt, vt = get_args(tp)
        if not isinstance(value, dict):
            raise SchemaError(f"{where}: expected object, got {type(value).__name__}")
        return {_check_type(k, kt, f"{where} key"): _check_type(v, vt, f"{where}.{k}")
                for k, v in value.items()}
    if origin is not None and type(None) in get_args(tp):  # Optional[X]
        if value is None:
            return None
        (inner,) = [a for a in get_args(tp) if a is not type(None)]
        return _check_type(value, inner, where)
    if dataclasses.is_dataclass(tp):
        return from_dict(tp, value, where)
    if tp is int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise SchemaError(f"{where}: expected int, got {value!r}")
        return value
    if tp is str:
        if not isinstance(value, str):
            raise SchemaError(f"{where}: expected string, got {value!r}")
        return value
    raise TypeError(f"unsupported type {tp!r}")


def from_dict(cls: type, data: Any, where: str = "$") -> Any:
    if not isinstance(data, dict):
        raise SchemaError(f"{where}: expected object, got {type(data).__name__}")
    hints = get_type_hints(cls)
    fields = {f.name: f for f in dataclasses.fields(cls)}
    unknown = set(data) - set(fields)
    if unknown:
        raise SchemaError(f"{where}: unknown field(s) {sorted(unknown)}")
    kwargs = {}
    for name, f in fields.items():
        if name not in data:
            required = f.default is dataclasses.MISSING and f.default_factory is dataclasses.MISSING
            if required:
                raise SchemaError(f"{where}: missing required field '{name}'")
            continue
        kwargs[name] = _check_type(data[name], hints[name], f"{where}.{name}")
    return cls(**kwargs)


def to_dict(obj: Any) -> Any:
    """Dataclass -> plain dict, dropping None-valued optional fields and empty `related`."""
    if dataclasses.is_dataclass(obj):
        out = {}
        for f in dataclasses.fields(obj):
            v = getattr(obj, f.name)
            if v is None:
                continue
            out[f.name] = to_dict(v)
        return out
    if isinstance(obj, list):
        return [to_dict(v) for v in obj]
    if isinstance(obj, dict):
        return {k: to_dict(v) for k, v in obj.items()}
    return obj


def dump_json(obj: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_dict(obj), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_json(cls: type, path: Path) -> Any:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SchemaError(f"{path}: invalid JSON: {e}") from e
    return from_dict(cls, data, str(path))


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------


def stem(order: int, form: str) -> str:
    """Shared filename stem for entry JSON and audio: '00001 ich' (learning order, not frequency rank)."""
    return f"{order:0{ORDER_WIDTH}d} {unicodedata.normalize('NFC', form)}"


@dataclass
class LanguagePaths:
    root: Path

    @property
    def config(self) -> Path: return self.root / "language.toml"
    @property
    def json_dir(self) -> Path: return self.root / "json"
    @property
    def words(self) -> Path: return self.json_dir / "words.json"
    @property
    def grammar(self) -> Path: return self.json_dir / "grammar.json"
    @property
    def verbs(self) -> Path: return self.json_dir / "verbs.json"
    @property
    def entries_dir(self) -> Path: return self.json_dir / "entries"
    @property
    def audio_dir(self) -> Path: return self.root / "audio"

    def entry(self, order: int, form: str) -> Path:
        return self.entries_dir / f"{stem(order, form)}.json"

    def audio(self, order: int, form: str) -> Path:
        return self.audio_dir / f"{stem(order, form)}.mp3"


@dataclass
class LanguageConfig:
    code: str            # "de"
    name: str            # "German"
    native_name: str     # "Deutsch"
    title: str           # PDF title / filename stem, e.g. "first 5k german words"
    word_count: int      # how many word forms the course covers (5000; 10000 later)
    max_reorder: int     # max |order - frequency_rank| allowed in words.json
    source: str          # human-readable source description
    source_url: str | None = None
    notes: str | None = None


def load_config(root: Path) -> LanguageConfig:
    p = LanguagePaths(root).config
    with p.open("rb") as fh:
        return from_dict(LanguageConfig, tomllib.load(fh), str(p))


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _nfc(s: str) -> bool:
    return unicodedata.normalize("NFC", s) == s


def validate_entry(e: Entry, where: str) -> list[str]:
    errs = []
    if e.schema_version != SCHEMA_VERSION:
        errs.append(f"{where}: schema_version {e.schema_version} != {SCHEMA_VERSION}")
    if e.order < 1:
        errs.append(f"{where}: order must be >= 1")
    if not e.form or e.form != e.form.strip() or not _nfc(e.form):
        errs.append(f"{where}: form must be non-empty, trimmed, NFC")
    if not e.meanings:
        errs.append(f"{where}: at least one meaning required")
    total = sum(len(m.sentences) for m in e.meanings)
    if total > MAX_SENTENCES_PER_ENTRY:
        errs.append(f"{where}: {total} sentences in entry > {MAX_SENTENCES_PER_ENTRY}")
    for i, m in enumerate(e.meanings):
        mw = f"{where}.meanings[{i}]"
        if m.pos not in POS_TAGS:
            errs.append(f"{mw}.pos: '{m.pos}' not a UPOS tag")
        if len(m.sentences) > MAX_SENTENCES_PER_MEANING:
            errs.append(f"{mw}: {len(m.sentences)} sentences > {MAX_SENTENCES_PER_MEANING}")
        for j, s in enumerate(m.sentences):
            sw = f"{mw}.sentences[{j}]"
            errs += _check_text_en(s.text, s.en, sw)
            for g in s.grammar_notes:
                if not GRAMMAR_ID_RE.match(g):
                    errs.append(f"{sw}.grammar_notes: bad id '{g}'")
    return errs


def _check_text_en(text: str, en: str, where: str) -> list[str]:
    errs = []
    if not text.strip() or not en.strip():
        errs.append(f"{where}: text and en must be non-empty")
    if not _nfc(text):
        errs.append(f"{where}.text: not NFC")
    return errs


def _check_header(obj: Any, path: Path, lang: str | None) -> list[str]:
    errs = []
    if obj.schema_version != SCHEMA_VERSION:
        errs.append(f"{path}: schema_version {obj.schema_version} != {SCHEMA_VERSION}")
    if lang and obj.language != lang:
        errs.append(f"{path}: language '{obj.language}' != config '{lang}'")
    return errs


def validate_language(root: Path) -> list[str]:
    """Structural + cross-file consistency. Does NOT do the known-words check or
    semantic first use (that is tools/checker, ticket write-sentence-checker)."""
    paths = LanguagePaths(root)
    errs: list[str] = []

    def load(cls, p):
        try:
            return load_json(cls, p)
        except (SchemaError, OSError) as ex:
            errs.append(str(ex))
            return None

    cfg = None
    if paths.config.exists():
        try:
            cfg = load_config(root)
        except (SchemaError, tomllib.TOMLDecodeError) as ex:
            errs.append(f"{paths.config}: {ex}")
    else:
        errs.append(f"{paths.config}: missing")
    lang = cfg.code if cfg else None

    # Word list
    words = load(WordList, paths.words) if paths.words.exists() else None
    by_order: dict[int, WordListItem] = {}
    if words:
        errs += _check_header(words, paths.words, lang)
        for i, w in enumerate(words.words, 1):
            if w.order != i:
                errs.append(f"{paths.words}: words[{i-1}] has order {w.order}, expected {i}")
            if not _nfc(w.form):
                errs.append(f"{paths.words}: order {w.order} form not NFC")
            if w.frequency_rank < 1:
                errs.append(f"{paths.words}: order {w.order} frequency_rank must be >= 1")
            if cfg and abs(w.order - w.frequency_rank) > cfg.max_reorder:
                errs.append(f"{paths.words}: '{w.form}' order {w.order} is "
                            f"{abs(w.order - w.frequency_rank)} from frequency_rank "
                            f"{w.frequency_rank} (max_reorder {cfg.max_reorder})")
            by_order[w.order] = w
        forms = [w.form for w in words.words]
        dups = {f for f in forms if forms.count(f) > 1}
        if dups:
            errs.append(f"{paths.words}: duplicate forms {sorted(dups)[:10]}")
        franks = [w.frequency_rank for w in words.words]
        fdups = {r for r in franks if franks.count(r) > 1}
        if fdups:
            errs.append(f"{paths.words}: duplicate frequency_rank {sorted(fdups)[:10]}")

    # Entries
    introduced: dict[str, list[int]] = {}
    entries: dict[int, Entry] = {}
    if paths.entries_dir.exists():
        for p in sorted(paths.entries_dir.glob("*.json")):
            e = load(Entry, p)
            if e is None:
                continue
            where = str(p)
            errs += validate_entry(e, where)
            if lang and e.language != lang:
                errs.append(f"{where}: language '{e.language}' != config '{lang}'")
            if p.name != f"{stem(e.order, e.form)}.json" or not _nfc(p.name):
                errs.append(f"{where}: filename should be '{stem(e.order, e.form)}.json'")
            if e.order in entries:
                errs.append(f"{where}: duplicate order {e.order}")
            entries[e.order] = e
            w = by_order.get(e.order)
            if words and w is None:
                errs.append(f"{where}: order {e.order} not in words.json")
            elif w is not None:
                if w.form != e.form:
                    errs.append(f"{where}: form '{e.form}' != words.json '{w.form}'")
                if w.base is not None and w.base != e.base:
                    errs.append(f"{where}: base '{e.base}' != words.json '{w.base}'")
            for m in e.meanings:
                for s in m.sentences:
                    for g in s.grammar_notes:
                        introduced.setdefault(g, []).append(e.order)

    # Grammar
    if paths.grammar.exists():
        g = load(Grammar, paths.grammar)
        if g:
            errs += _check_header(g, paths.grammar, lang)
            ids = [c.id for c in g.concepts]
            for dup in {i for i in ids if ids.count(i) > 1}:
                errs.append(f"{paths.grammar}: duplicate id '{dup}'")
            known = set(ids)
            for c in g.concepts:
                cw = f"{paths.grammar}: '{c.id}'"
                if not GRAMMAR_ID_RE.match(c.id):
                    errs.append(f"{paths.grammar}: bad id '{c.id}'")
                for r in c.related:
                    if r not in known:
                        errs.append(f"{cw}.related -> unknown '{r}'")
                if len(c.examples) > MAX_GRAMMAR_EXAMPLES:
                    errs.append(f"{cw}: {len(c.examples)} examples > {MAX_GRAMMAR_EXAMPLES}")
                for j, ex in enumerate(c.examples):
                    errs += _check_text_en(ex.text, ex.en, f"{cw}.examples[{j}]")
                orders = introduced.get(c.id, [])
                if c.first_entry in entries and orders != [c.first_entry]:
                    errs.append(
                        f"{cw} first_entry={c.first_entry}, but introduced in entries "
                        f"{orders or 'none'} (must be exactly once, there)")
            for gid, orders in introduced.items():
                if gid not in known:
                    errs.append(f"grammar note '{gid}' (entries {orders}) missing from grammar.json")
    elif introduced:
        errs.append(f"{paths.grammar}: missing but entries reference grammar notes")

    # Verbs (appendix). Structure only; tables are exempt from the known-words rule.
    if paths.verbs.exists():
        v = load(Verbs, paths.verbs)
        if v:
            errs += _check_header(v, paths.verbs, lang)
            bases = [x.base for x in v.verbs]
            for dup in {b for b in bases if bases.count(b) > 1}:
                errs.append(f"{paths.verbs}: duplicate verb '{dup}'")
            counts = [x.total_count for x in v.verbs]
            if counts != sorted(counts, reverse=True):
                errs.append(f"{paths.verbs}: verbs not sorted by total_count descending")
            list_bases = {w.base for w in words.words} if words else None
            for x in v.verbs:
                vw = f"{paths.verbs}: '{x.base}'"
                if not x.base.strip() or not _nfc(x.base):
                    errs.append(f"{vw}: base must be non-empty, NFC")
                if list_bases is not None and x.base not in list_bases:
                    errs.append(f"{vw}: no form in words.json has this base")
                if not x.tenses:
                    errs.append(f"{vw}: no tenses")
                tids = [t.tense for t in x.tenses]
                for dup in {t for t in tids if tids.count(t) > 1}:
                    errs.append(f"{vw}: duplicate tense '{dup}'")
                for t in x.tenses:
                    if not GRAMMAR_ID_RE.match(t.tense):
                        errs.append(f"{vw}: bad tense id '{t.tense}'")
                    if not t.forms:
                        errs.append(f"{vw}.{t.tense}: no forms")
                    for person, form in t.forms.items():
                        if not person.strip() or not form.strip() or not _nfc(form):
                            errs.append(f"{vw}.{t.tense}.{person!r}: person and form must be non-empty, NFC")
                for kind, form in x.participles.items():
                    if not form.strip() or not _nfc(form):
                        errs.append(f"{vw}.participles.{kind}: must be non-empty, NFC")

    return errs


# ---------------------------------------------------------------------------
# JSON Schema export (for editors / external tools; validation above is canonical)
# ---------------------------------------------------------------------------


def json_schema(cls: type) -> dict:
    defs: dict[str, dict] = {}

    def conv(tp: Any) -> dict:
        origin = get_origin(tp)
        if origin is list:
            return {"type": "array", "items": conv(get_args(tp)[0])}
        if origin is dict:
            return {"type": "object", "additionalProperties": conv(get_args(tp)[1])}
        if origin is not None and type(None) in get_args(tp):
            (inner,) = [a for a in get_args(tp) if a is not type(None)]
            return {"anyOf": [conv(inner), {"type": "null"}]}
        if dataclasses.is_dataclass(tp):
            name = tp.__name__
            if name not in defs:
                defs[name] = {}
                hints = get_type_hints(tp)
                req = [f.name for f in dataclasses.fields(tp)
                       if f.default is dataclasses.MISSING and f.default_factory is dataclasses.MISSING]
                defs[name] = {
                    "type": "object",
                    "additionalProperties": False,
                    "required": req,
                    "properties": {f.name: conv(hints[f.name]) for f in dataclasses.fields(tp)},
                }
            return {"$ref": f"#/$defs/{name}"}
        return {int: {"type": "integer"}, str: {"type": "string"}}[tp]

    root = conv(cls)
    if "Meaning" in defs:
        defs["Meaning"]["properties"]["pos"] = {"enum": sorted(POS_TAGS)}
        defs["Meaning"]["properties"]["sentences"]["maxItems"] = MAX_SENTENCES_PER_MEANING
    if "GrammarConcept" in defs:
        defs["GrammarConcept"]["properties"]["examples"]["maxItems"] = MAX_GRAMMAR_EXAMPLES
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", **root, "$defs": defs}


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[0] == "validate":
        errs = validate_language(Path(argv[1]))
        for e in errs:
            print(e, file=sys.stderr)
        print(f"{len(errs)} error(s)", file=sys.stderr)
        return 1 if errs else 0
    if len(argv) >= 1 and argv[0] == "jsonschema":
        cls = {"entry": Entry, "words": WordList, "grammar": Grammar, "verbs": Verbs}[argv[1] if len(argv) > 1 else "entry"]
        print(json.dumps(json_schema(cls), indent=2))
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
