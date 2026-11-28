"""Generate <lang>/json/verbs.json: the most common verbs with full conjugation tables.

Pipeline (German; other languages need their own tense/person tables below):

1. **Index** the kaikki.org Wiktionary extract (English Wiktionary, German
   entries; ``cache/kaikki/``, gitignored, downloaded once) into
   ``cache/kaikki/verb-index.json``: per verb, its single-word forms and its
   conjugation table by (tense, person).
2. **Readings.** For every form in ``words.json``: if it has an entry (1-100
   for the pilot), its VERB/AUX ``meanings[].base`` give the verbs; otherwise
   ``simplemma`` gives the lemma and the kaikki index gives every verb whose
   paradigm contains the form. A form is *unambiguous* when exactly one verb
   claims it and nothing else does (entry: only verb meanings of that base;
   no entry: simplemma's lemma is that verb and no other paradigm has the
   form). simplemma is checked against the entries' bases; disagreements are
   reported.
3. **Rank.** ``lower[v]`` sums unambiguous counts, ``upper[v]`` adds every
   ambiguous form that could be ``v``. Every verb whose upper bound reaches the
   N-th largest lower bound is a candidate, so no verb outside the candidates
   can make the top N. The model estimates, for each ambiguous form of a
   candidate, the share of its count per reading (each verb, plus "other",
   i.e. non-verb uses). ``total_count = lower + sum(round(count * share))``,
   and partly counted forms are stored as ``count_splits``.
4. **Generate** each of the top N verbs (one structured-output call): every
   tense, participles, and one minimal example sentence per form. Checked
   in-process (all tenses and persons present, each example uses its form) and
   cross-checked against kaikki. Problems get ``--retries`` repair rounds; any
   kaikki mismatch still left is reported, never silently dropped.
5. **Review and repair** (default on): a second call flags problems in forms
   or examples. A repair call then acts on every flag: it fixes the example or
   translation (or a form, which must still pass the checks and the kaikki
   cross-check), or dismisses the flag when it is not a real error. The
   repaired verb is reviewed again, up to ``--repair-rounds`` times. Flags are
   never written to verbs.json (human review 2026-11-28: no reviewer comments
   in the appendix); any flag still open after the last round is listed in
   ``cache/verbs/report.md`` and printed to stderr for a human.

Model output is cached per step under ``cache/verbs/`` (shares, generated,
reviewed and repaired verbs), so a re-run resumes; ``--force`` regenerates the verbs (shares
stay cached unless ``--reshare``). The API key is read from
``TOWER_ANTHROPIC_KEY`` only. A report of the ranking, the simplemma check and
all kaikki mismatches is written to ``cache/verbs/report.md``.

CLI:
    python -m tools.verbs german                     # rank + generate + review -> german/json/verbs.json
    python -m tools.verbs german --rank-only         # print the ranking (needs the share call)
    python -m tools.verbs german --only sein,haben --force
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from pydantic import BaseModel

from tools.schema import (SCHEMA_VERSION, CountSplit, Entry, Example, LanguagePaths, Verb,
                          Verbs, VerbTense, WordList, dump_json, load_config, load_json,
                          validate_language)

REPO = Path(__file__).resolve().parent.parent
KAIKKI_URL = "https://kaikki.org/dictionary/German/kaikki.org-dictionary-German.jsonl"
KAIKKI_DIR = REPO / "cache" / "kaikki"
KAIKKI_PATH = KAIKKI_DIR / "kaikki.org-dictionary-German.jsonl"
INDEX_PATH = KAIKKI_DIR / "verb-index.json"
CACHE = REPO / "cache" / "verbs"
DEFAULT_TOP = 20
VERB_POS = {"VERB", "AUX"}
OTHER = "other"

PERSONS = {  # label -> English, display order (human review 2026-11-28)
    "ich": "I",
    "du": "you (informal, one person)",
    "er/sie/es": "he / she / it",
    "wir": "we",
    "ihr": "you (informal, several)",
    "sie/Sie": "they / you (formal)",
    "Sie": "you (formal)",
}
FINITE_PERSONS = ["ich", "du", "er/sie/es", "wir", "ihr", "sie/Sie"]
IMPERATIVE_PERSONS = ["du", "ihr", "Sie"]
TENSES = [  # id, label (same as the illustrative docs/example verbs.json)
    ("praesens", "Präsens (present)"),
    ("praeteritum", "Präteritum (simple past)"),
    ("perfekt", "Perfekt (present perfect)"),
    ("plusquamperfekt", "Plusquamperfekt (past perfect)"),
    ("futur_i", "Futur I (future)"),
    ("futur_ii", "Futur II (future perfect)"),
    ("konjunktiv_i", "Konjunktiv I (reported speech)"),
    ("konjunktiv_ii", "Konjunktiv II (would be)"),
    ("imperativ", "Imperativ (command)"),
]
TENSE_IDS = [t for t, _ in TENSES]
LABELS = dict(TENSES)
OPTIONAL_TENSES = {"imperativ"}   # e.g. modal verbs have no proper imperative


def persons_of(tense: str) -> list[str]:
    return IMPERATIVE_PERSONS if tense == "imperativ" else FINITE_PERSONS


# ---------------------------------------------------------------------------
# kaikki index
# ---------------------------------------------------------------------------

_PERSON_TAGS = {("first-person", "singular"): "ich", ("second-person", "singular"): "du",
                ("third-person", "singular"): "er/sie/es", ("first-person", "plural"): "wir",
                ("second-person", "plural"): "ihr", ("third-person", "plural"): "sie/Sie"}
WORD_RE = re.compile(r"^[^\W\d_]+$")


def kaikki_cell(tags: set[str]) -> tuple[str, str] | None:
    """Map one kaikki form's tags to (tense id, person label), or None."""
    multi = "multiword-construction" in tags
    if "imperative" in tags:
        if "second-person" not in tags:
            return None
        return ("imperativ", "du" if "singular" in tags else "ihr" if "plural" in tags else None) \
            if ("singular" in tags or "plural" in tags) else None
    person = next((p for (a, b), p in _PERSON_TAGS.items() if a in tags and b in tags), None)
    if person is None or "infinitive" in tags or "participle" in tags:
        return None
    if "indicative" in tags:
        for tag, tid in (("present", "praesens"), ("preterite", "praeteritum"),
                         ("perfect", "perfekt"), ("pluperfect", "plusquamperfekt"),
                         ("future-i", "futur_i"), ("future-ii", "futur_ii")):
            if tag in tags:
                if tid in ("praesens", "praeteritum") and multi:
                    return None
                return tid, person
        return None
    if "subjunctive" in tags and not multi and not tags & {"perfect", "pluperfect", "future"}:
        if "subjunctive-i" in tags:
            return "konjunktiv_i", person
        if "subjunctive-ii" in tags:
            return "konjunktiv_ii", person
    return None


def paradigm(forms: list[dict]) -> dict:
    """{"forms": [single-word forms], "table": {tense: {person: [variants]}}, "participles": {...}}"""
    single: set[str] = set()
    table: dict[str, dict[str, list[str]]] = {}
    parts: dict[str, list[str]] = {}
    for f in forms:
        form, tags = (f.get("form") or "").strip(), set(f.get("tags") or [])
        if not form or tags & {"table-tags", "inflection-template", "auxiliary", "romanization"}:
            continue
        form = unicodedata.normalize("NFC", form)
        if "participle" in tags and "multiword-construction" not in tags:
            kind = "present" if "present" in tags else "past" if "past" in tags else None
            if kind and form not in parts.setdefault(kind, []):
                parts[kind].append(form)
        if WORD_RE.match(form) and "multiword-construction" not in tags:
            single.add(form)
        cell = kaikki_cell(tags)
        if cell:
            variants = table.setdefault(cell[0], {}).setdefault(cell[1], [])
            if form not in variants:
                variants.append(form)
    return {"forms": sorted(single), "table": table, "participles": parts}


def merge_paradigm(a: dict, b: dict) -> dict:
    out = {"forms": sorted(set(a["forms"]) | set(b["forms"])), "table": {}, "participles": {}}
    for key in ("table",):
        for src in (a[key], b[key]):
            for t, cells in src.items():
                for p, vs in cells.items():
                    dst = out[key].setdefault(t, {}).setdefault(p, [])
                    dst += [v for v in vs if v not in dst]
    for src in (a["participles"], b["participles"]):
        for k, vs in src.items():
            dst = out["participles"].setdefault(k, [])
            dst += [v for v in vs if v not in dst]
    return out


def build_index(src: Path = KAIKKI_PATH, dst: Path = INDEX_PATH) -> dict:
    if not src.exists():
        sys.exit(f"error: {src} missing. Download it once (gitignored, ~1.1 GB):\n"
                 f"  curl -L -o '{src}' {KAIKKI_URL}")
    print(f"indexing {src.name} (verbs only) ...", file=sys.stderr)
    sha = hashlib.sha256()
    verbs: dict[str, dict] = {}
    nonverb: set[str] = set()
    with src.open("rb") as fh:
        for raw in fh:
            sha.update(raw)
            rec = json.loads(raw)
            if rec.get("lang_code") != "de":
                continue
            if rec.get("pos") != "verb":
                if rec.get("pos") not in ("name", "character", "symbol", "suffix", "prefix"):
                    for f in [rec.get("word", "")] + [x.get("form", "") for x in rec.get("forms") or []]:
                        f = unicodedata.normalize("NFC", f.strip())
                        if WORD_RE.match(f):
                            nonverb.add(f)
                continue
            senses = rec.get("senses") or []
            if senses and all(x.get("form_of") or "form-of" in (x.get("tags") or []) for x in senses):
                continue                     # an inflected form's own page ("wurde"), not a verb
            word = unicodedata.normalize("NFC", rec["word"])
            p = paradigm(rec.get("forms") or [])
            if WORD_RE.match(word):
                p["forms"] = sorted(set(p["forms"]) | {word})
            verbs[word] = merge_paradigm(verbs[word], p) if word in verbs else p
    index = {"source": KAIKKI_URL, "file": src.name, "sha256": sha.hexdigest(),
             "built": dt.date.today().isoformat(), "verbs": verbs, "nonverb": sorted(nonverb)}
    dst.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    print(f"  {len(verbs)} verbs -> {dst}", file=sys.stderr)
    return index


def load_index(rebuild: bool = False) -> dict:
    if INDEX_PATH.exists() and not rebuild:
        return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    return build_index()


# ---------------------------------------------------------------------------
# Readings and ranking
# ---------------------------------------------------------------------------


@dataclass
class Reading:
    form: str
    count: int
    verbs: set[str]                  # verbs this form can be a form of
    ambiguous: bool                  # needs a model share estimate
    glosses: list[str] = field(default_factory=list)   # entry meanings, for the share prompt


@dataclass
class Ranked:
    base: str
    total: int
    forms: list[tuple[str, int]]     # unambiguous forms with full count
    splits: list[CountSplit]         # partly counted forms


def readings(words: WordList, entries: dict[int, Entry], verbs: dict[str, dict],
             lemmatize: Callable[[str], str],
             nonverb: set[str] = frozenset()) -> tuple[dict[str, Reading], list[str]]:
    """Verb readings per words.json form, plus simplemma-vs-entry disagreements.
    `nonverb`: forms that kaikki also lists for a non-verb word (possessive "sein")."""
    by_form: dict[str, set[str]] = {}
    for v, p in verbs.items():
        for f in p["forms"]:
            by_form.setdefault(f, set()).add(v)
    out: dict[str, Reading] = {}
    disagree: list[str] = []
    for w in words.words:
        claims = by_form.get(w.form, set())
        e = entries.get(w.order)
        if e is not None and e.form == w.form:
            vb = {mn.base for mn in e.meanings if mn.pos in VERB_POS}
            lem = lemmatize(w.form)
            if vb and lem not in vb:
                disagree.append(f"{w.form}: entry bases {sorted(vb)}, simplemma '{lem}'")
            if not vb:
                continue
            other = any(mn.pos not in VERB_POS for mn in e.meanings)
            glosses = [f"{mn.pos} {mn.base}: {mn.gloss}" for mn in e.meanings]
            out[w.form] = Reading(w.form, w.count, vb, other or len(vb) > 1, glosses)
            continue
        lem = lemmatize(w.form)
        # simplemma maps possessive "seinen" to "sein": trust it only inside the paradigm
        vb = set(claims) | ({lem} if lem in verbs and w.form in verbs[lem]["forms"] else set())
        if not vb:
            continue
        unambiguous = vb == {lem} and w.form not in nonverb
        out[w.form] = Reading(w.form, w.count, vb, not unambiguous)
    return out, disagree


def bounds(rs: dict[str, Reading]) -> tuple[dict[str, int], dict[str, int]]:
    lower: dict[str, int] = {}
    upper: dict[str, int] = {}
    for r in rs.values():
        for v in r.verbs:
            upper[v] = upper.get(v, 0) + r.count
            if not r.ambiguous:
                lower[v] = lower.get(v, 0) + r.count
    return lower, upper


def candidates(rs: dict[str, Reading], top: int) -> list[str]:
    """Every verb that could still make the top `top`: upper bound >= top-th lower bound."""
    lower, upper = bounds(rs)
    ranked = sorted(lower.values(), reverse=True)
    threshold = ranked[top - 1] if len(ranked) >= top else 0
    return sorted((v for v, u in upper.items() if u >= threshold), key=lambda v: -upper[v])


def rank(rs: dict[str, Reading], shares: dict[str, dict[str, float]], top: int) -> list[Ranked]:
    """Final ranking. `shares[form][reading]` for ambiguous forms (missing -> not counted)."""
    acc: dict[str, Ranked] = {}
    for r in sorted(rs.values(), key=lambda r: -r.count):
        for v in r.verbs:
            rk = acc.setdefault(v, Ranked(v, 0, [], []))
            if not r.ambiguous:
                rk.total += r.count
                rk.forms.append((r.form, r.count))
                continue
            share = shares.get(r.form, {}).get(v, 0.0)
            if share >= 1.0 or round(r.count * share) >= r.count or round(share * 100) >= 100:
                rk.total += r.count
                rk.forms.append((r.form, r.count))
            elif share > 0 and round(r.count * share) > 0:
                rk.total += round(r.count * share)
                rest = {k: s for k, s in shares[r.form].items() if k != v and s > 0}
                note = "rest: " + ", ".join(
                    (f"non-verb {round(s * 100)}%" if k == OTHER else f"'{k}' {round(s * 100)}%")
                    for k, s in sorted(rest.items(), key=lambda kv: -kv[1])) if rest else None
                rk.splits.append(CountSplit(r.form, r.count, round(share, 3), note))
    return sorted(acc.values(), key=lambda x: (-x.total, x.base))[:top]


# ---------------------------------------------------------------------------
# Model I/O
# ---------------------------------------------------------------------------


class GenShare(BaseModel):
    reading: str                     # a verb infinitive from the offered list, or "other"
    share: float


class GenFormShares(BaseModel):
    form: str
    shares: list[GenShare]
    reason: str


class GenShares(BaseModel):
    forms: list[GenFormShares]


class GenForm(BaseModel):
    person: str
    form: str


class GenExample(BaseModel):
    person: str
    text: str
    en: str


class GenTense(BaseModel):
    tense: str
    forms: list[GenForm]
    examples: list[GenExample]


class GenVerb(BaseModel):
    base: str
    translation: str
    present_participle: str
    past_participle: str
    tenses: list[GenTense]


class ReviewIssue(BaseModel):
    tense: str
    person: str
    severity: str                    # "error" | "warning"
    comment: str


class VerbReview(BaseModel):
    issues: list[ReviewIssue]


class RepairAction(BaseModel):
    tense: str
    person: str
    action: str                      # "fixed" | "dismissed"
    reason: str


class GenRepair(BaseModel):
    verb: GenVerb
    actions: list[RepairAction]


SHARES_SYSTEM = """\
You estimate how a German word form's corpus count splits between its readings.
The corpus is Tatoeba: short everyday sentences (many questions, dialogue, first
and second person). Counts are per exact token, case-sensitive.

For each form you get its count and the readings to split between: one or more
verb infinitives (the form is a form of that verb) and "other" (every non-verb
use: article, pronoun, possessive, adjective, noun, adverb, interjection, ...,
and any verb not offered). Give a share per offered reading, summing to 1.
Estimate realistically from your knowledge of German usage; a reading that is
technically possible but archaic or very rare (e.g. "einen" = "to unite",
"mal" = imperative of "malen" next to the particle "mal") gets ~0. Auxiliary
and modal uses count for the verb (e.g. "wird" in the passive or future counts
for "werden"). Give a one-line reason."""

GEN_SYSTEM = """\
You write conjugation tables for a German vocabulary book for English speakers.

For the given verb produce:
- `translation`: English infinitive gloss, e.g. "to be", "to have"; for a verb
  with several senses, the main one(s) in a few words.
- `present_participle`, `past_participle`.
- `tenses`, in this order, with these ids: praesens, praeteritum, perfekt,
  plusquamperfekt, futur_i, futur_ii, konjunktiv_i, konjunktiv_ii, imperativ.
  Persons for all but imperativ, in order: ich, du, er/sie/es, wir, ihr, sie/Sie.
  Imperativ persons: du, ihr, Sie. If the verb has no proper imperative (e.g.
  modal verbs), omit the imperativ tense; omit any person the verb lacks.
- Forms are standard modern German: the full phrase for compound tenses
  ("bin gewesen", "hatte gemacht", "werde gemacht haben"), the correct
  auxiliary (haben/sein) for Perfekt, Plusquamperfekt and Futur II, separable
  prefixes split off in main-clause word order ("fange an", "fing an", "habe
  angefangen"), the Konjunktiv II as the synthetic one-word form ("wäre",
  "hätte", "machte"), never "würde + infinitive". Imperativ du without -e
  where usual ("komm", "sei"), Sie as "<Konjunktiv I 3rd plural> Sie"
  ("seien Sie", "kommen Sie", "fangen Sie an"). One form per cell (the most
  common variant).
- `examples`: for every tense and person, exactly one minimal, natural German
  example sentence using exactly that form, plus its English translation.
  Short (3-8 words), everyday words, the subject pronoun of that person
  (for sie/Sie choose plural "sie" or formal "Sie"; for er/sie/es any of the
  three). Each sentence must contain every word of the form (compound tenses
  may split around other words, as German word order requires; for modal
  verbs a double infinitive like "habe kommen können" is fine). Konjunktiv I
  examples are reported speech ("Er sagt, ...") and Konjunktiv II examples are
  wishes or conditions. Vary the sentences; don't repeat the same frame across
  persons. English translations natural, not word-for-word."""

REVIEW_SYSTEM = """\
You review a German conjugation table and its example sentences for a book
for English speakers. Flag only real problems: a wrong or non-standard form,
wrong auxiliary, an example that does not use the form of its row, a German
sentence that is ungrammatical or unnatural, or an English translation that
is wrong. Severity "error" for wrong, "warning" for doubtful. `comment` is one
short sentence saying what to change. No issues -> empty list. Never praise.

Do not flag (these are settled decisions for this book):
- a correct form only because it is rare, bookish or archaic in speech, or
  because a Konjunktiv I form equals the indicative and speakers would switch
  to Konjunktiv II or "würde" (the table shows the standard forms);
- an auxiliary or modal use of the verb (e.g. "würde" + infinitive for
  werden, a modal with a dependent infinitive): it is a use of that form;
- "add a note": the book prints no notes on rows."""

REPAIR_SYSTEM = """\
You repair a German conjugation table for a vocabulary book for English
speakers. You get the verb (forms, participles, one example sentence per
tense and person) and a reviewer's issues. Act on every issue:
- If it points to a real error or a clearly unnatural sentence or translation,
  fix it: rewrite that example (German and/or English) so the problem is gone.
  Keep the rules for examples: short (3-8 words), everyday words, the subject
  pronoun of that person, every word of the row's form in the sentence
  (compound tenses may split; a modal may use the double infinitive),
  Konjunktiv I in reported speech, Konjunktiv II in wishes or conditions, and
  a natural English translation that matches the German exactly.
  Change a *form* only if it is wrong for standard modern German; the table is
  checked against Wiktionary afterwards.
- If it is not a real error (a correct but bookish form, a Konjunktiv I form
  that equals the indicative, a request to add a note, a matter of taste),
  dismiss it and leave the text unchanged.
Return the complete verb (every tense, form and example, unchanged where no
issue applies) and one action per issue: "fixed" or "dismissed" with a short
reason."""


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

TOKEN_RE = re.compile(r"[^\W\d_]+(?:-[^\W\d_]+)*")


def tokens(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text)]


def uses_form(text: str, form: str, base: str, past_participle: str) -> bool:
    """Every word of `form` occurs in `text`; a past participle may be replaced by
    the infinitive (Ersatzinfinitiv: "habe kommen können")."""
    have = tokens(text)
    for w in tokens(form):
        if w in have:
            continue
        if w == past_participle.lower() and base.lower() in have:
            continue
        return False
    return True


def check_verb(g: GenVerb, base: str) -> list[str]:
    errs: list[str] = []
    if g.base != base:
        errs.append(f"base is '{g.base}', expected '{base}'")
    got = [t.tense for t in g.tenses]
    want = [t for t in TENSE_IDS if t in got or t not in OPTIONAL_TENSES]
    if got != want:
        errs.append(f"tenses must be {want} in that order, got {got}")
    for t in g.tenses:
        if t.tense not in TENSE_IDS:
            continue
        allowed = persons_of(t.tense)
        ps = [f.person for f in t.forms]
        if [p for p in allowed if p in ps] != ps or not ps:
            errs.append(f"{t.tense}: persons must be a non-empty, in-order subset of {allowed}, got {ps}")
        if t.tense != "imperativ" and len(ps) != len(allowed):
            errs.append(f"{t.tense}: missing persons {[p for p in allowed if p not in ps]}")
        forms = {f.person: f.form for f in t.forms}
        exs = [e.person for e in t.examples]
        if sorted(exs) != sorted(ps):
            errs.append(f"{t.tense}: need exactly one example per person {ps}, got {exs}")
        for e in t.examples:
            f = forms.get(e.person)
            if f and not uses_form(e.text, f, base, g.past_participle):
                errs.append(f"{t.tense}.{e.person}: example '{e.text}' does not use the form '{f}'")
            if not e.text.strip() or not e.en.strip():
                errs.append(f"{t.tense}.{e.person}: empty example or translation")
    return errs


def _norm(s: str) -> str:
    return " ".join(unicodedata.normalize("NFC", s).split())


def expected_cells(p: dict) -> dict[str, dict[str, list[str]]]:
    """kaikki table plus a derived imperative Sie, only where kaikki has an imperative.
    Sie takes the 3rd plural present ("tun Sie", "fangen Sie an"), except sein, which
    takes Konjunktiv I ("seien Sie"); both are accepted."""
    table = {t: dict(c) for t, c in p.get("table", {}).items()}
    if not table.get("imperativ"):
        return table
    sie = []
    for f in table.get("praesens", {}).get("sie/Sie", []) + table.get("konjunktiv_i", {}).get("sie/Sie", []):
        head, *rest = f.split()
        if (v := " ".join([head, "Sie", *rest])) not in sie:
            sie.append(v)
    if sie:
        table["imperativ"]["Sie"] = sie
    return table


def crosscheck(g: GenVerb, p: dict | None) -> tuple[list[str], int, int]:
    """(mismatches, cells checked, cells without kaikki data)."""
    if p is None:
        return [f"'{g.base}' not in the kaikki index: nothing cross-checked"], 0, 0
    exp = expected_cells(p)
    bad, checked, missing = [], 0, 0
    for t in g.tenses:
        for f in t.forms:
            variants = exp.get(t.tense, {}).get(f.person)
            if not variants:
                missing += 1
                continue
            checked += 1
            if _norm(f.form) not in {_norm(v) for v in variants}:
                bad.append(f"{t.tense}.{f.person}: '{f.form}' vs kaikki {variants}")
    if t_missing := [t for t in exp if t in TENSE_IDS and t not in {x.tense for x in g.tenses}]:
        bad.append(f"tenses omitted but in kaikki: {t_missing}")
    for kind, mine in (("present", g.present_participle), ("past", g.past_participle)):
        theirs = p.get("participles", {}).get(kind)
        if theirs:
            checked += 1
            if _norm(mine) not in {_norm(v) for v in theirs}:
                bad.append(f"participle.{kind}: '{mine}' vs kaikki {theirs}")
    return bad, checked, missing


# ---------------------------------------------------------------------------
# Conversion
# ---------------------------------------------------------------------------


def to_verb(g: GenVerb, rk: Ranked, notes: str) -> Verb:
    """Reviewer flags are acted on by repair_verb, never stored (no `review`)."""
    tenses = []
    for t in g.tenses:
        ex = {e.person: e for e in t.examples}
        tenses.append(VerbTense(
            tense=t.tense, label=LABELS[t.tense],
            forms={f.person: unicodedata.normalize("NFC", f.form) for f in t.forms},
            examples={f.person: Example(unicodedata.normalize("NFC", ex[f.person].text),
                                        ex[f.person].en)
                      for f in t.forms if f.person in ex}))
    return Verb(base=rk.base, translation=g.translation, total_count=rk.total, tenses=tenses,
                participles={"present": g.present_participle, "past": g.past_participle},
                count_splits=rk.splits, notes=notes)


def count_note(rk: Ranked) -> str:
    full = ", ".join(f"{f} {c}" for f, c in rk.forms)
    split = ", ".join(f"{s.form} {round(s.count * s.verb_share)} of {s.count}" for s in rk.splits)
    return f"total_count {rk.total} = {full}" + (f"; split: {split}" if split else "")


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def _read_json(p: Path, default):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def _write_json(p: Path, data) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def share_prompt(batch: list[Reading]) -> str:
    lines = []
    for r in batch:
        g = f"; course entry meanings: {' | '.join(r.glosses)}" if r.glosses else ""
        lines.append(f"- {r.form} (count {r.count}): readings {sorted(r.verbs) + [OTHER]}{g}")
    return "Estimate the shares for these forms:\n" + "\n".join(lines)


def estimate_shares(gen, rs: dict[str, Reading], cands: list[str], cache: Path,
                    reshare: bool, batch_size: int = 60) -> dict[str, dict[str, float]]:
    cached = {} if reshare else _read_json(cache, {})
    cset = set(cands)
    todo = [r for r in sorted(rs.values(), key=lambda r: -r.count)
            if r.ambiguous and r.verbs & cset
            and sorted(cached.get(r.form, {}).get("readings", [])) != sorted(r.verbs | {OTHER})]
    for i in range(0, len(todo), batch_size):
        batch = todo[i:i + batch_size]
        out: GenShares = gen.call(SHARES_SYSTEM, share_prompt(batch), GenShares,
                                  f"shares {i + 1}-{i + len(batch)}/{len(todo)}")
        want = {r.form: r for r in batch}
        for fs in out.forms:
            r = want.get(fs.form)
            if r is None:
                continue
            raw = {s.reading: max(0.0, s.share) for s in fs.shares if s.reading in r.verbs | {OTHER}}
            tot = sum(raw.values())
            if tot <= 0:
                continue
            cached[fs.form] = {"readings": sorted(r.verbs | {OTHER}), "count": r.count,
                               "shares": {k: round(v / tot, 3) for k, v in raw.items()},
                               "reason": fs.reason, "model": gen.model}
        missing = [f for f in want if f not in cached]
        if missing:
            raise RuntimeError(f"share estimate missing for {missing}")
        _write_json(cache, cached)
    return {f: d["shares"] for f, d in cached.items()}


def gen_prompt(rk: Ranked) -> str:
    seen = ", ".join(f for f, _ in rk.forms[:12])
    return (f"Verb: {rk.base}\nIts most frequent forms in the corpus: {seen}.\n"
            f"Write the full table with examples.")


def retry_prompt(prev: GenVerb, problems: list[str]) -> str:
    return ("Your previous answer:\n" + prev.model_dump_json() + "\n\nFix these problems and "
            "return the complete corrected verb. A note 'vs kaikki' quotes the Wiktionary table: "
            "use its form unless you are sure it is wrong for standard modern German.\n- "
            + "\n- ".join(problems))


def generate_verb(gen, rk: Ranked, p: dict | None, retries: int) -> tuple[GenVerb, list[str], tuple[int, int]]:
    g: GenVerb = gen.call(GEN_SYSTEM, gen_prompt(rk), GenVerb, f"verb {rk.base}")
    for attempt in range(retries + 1):
        problems = check_verb(g, rk.base)
        mismatch, checked, missing = crosscheck(g, p)
        if not problems and not mismatch:
            break
        if attempt == retries:
            if problems:
                raise RuntimeError(f"{rk.base}: still failing after {retries} retries: {problems}")
            break
        g = gen.call(GEN_SYSTEM, retry_prompt(g, problems + mismatch), GenVerb,
                     f"verb {rk.base} retry {attempt + 1}")
    return g, mismatch, (checked, missing)


def review_verb(gen, g: GenVerb, label: str = "") -> VerbReview:
    return gen.call(REVIEW_SYSTEM, "Review this verb:\n" + g.model_dump_json(indent=1),
                    VerbReview, f"review {g.base}{label}")


def repair_prompt(g: GenVerb, issues: list[ReviewIssue], problems: list[str]) -> str:
    out = ("Verb:\n" + g.model_dump_json(indent=1) + "\n\nReviewer issues:\n- "
           + "\n- ".join(f"{i.tense}.{i.person} ({i.severity}): {i.comment}" for i in issues))
    if problems:
        out += ("\n\nYour previous repair failed these checks; fix them too (a note 'vs kaikki' "
                "quotes the Wiktionary table):\n- " + "\n- ".join(problems))
    return out


@dataclass
class Repair:
    """Outcome of review + repair for one verb (cached as cache/verbs/repair/<base>.json)."""
    verb: GenVerb
    rounds: list[dict]               # per round: issues found, actions taken
    open: list[ReviewIssue]          # issues the last review still raised

    def to_json(self) -> str:
        return json.dumps({"verb": self.verb.model_dump(), "rounds": self.rounds,
                           "open": [i.model_dump() for i in self.open]},
                          ensure_ascii=False, indent=1)

    @classmethod
    def from_json(cls, text: str) -> "Repair":
        d = json.loads(text)
        return cls(GenVerb.model_validate(d["verb"]), d["rounds"],
                   [ReviewIssue.model_validate(i) for i in d["open"]])


def repair_verb(gen, g: GenVerb, first: VerbReview, p: dict | None, rounds: int,
                retries: int) -> Repair:
    """Act on review issues: repair, re-review, up to `rounds` times. A repair that
    breaks the checks or adds a kaikki mismatch gets `retries` more tries, else it
    is discarded and the issues stay open."""
    log: list[dict] = []
    issues = list(first.issues)
    for n in range(1, rounds + 1):
        if not issues:
            break
        base_mismatch = set(crosscheck(g, p)[0])
        problems: list[str] = []
        for attempt in range(retries + 1):
            out: GenRepair = gen.call(REPAIR_SYSTEM, repair_prompt(g, issues, problems), GenRepair,
                                      f"repair {g.base} r{n}" + (f" retry {attempt}" if attempt else ""))
            problems = check_verb(out.verb, g.base) + [
                m for m in crosscheck(out.verb, p)[0] if m not in base_mismatch]
            if not problems:
                break
        log.append({"issues": [i.model_dump() for i in issues],
                    "actions": [a.model_dump() for a in out.actions],
                    "rejected": problems})
        if problems:            # keep the last good verb; its issues stay open
            break
        g = out.verb
        issues = review_verb(gen, g, f" r{n}").issues
    return Repair(g, log, issues)


def load_entries(paths: LanguagePaths) -> dict[int, Entry]:
    out = {}
    if paths.entries_dir.exists():
        for f in sorted(paths.entries_dir.glob("*.json")):
            e = load_json(Entry, f)
            out[e.order] = e
    return out


def simplemma_lemmatizer(code: str) -> Callable[[str], str]:
    import simplemma
    return lambda w: simplemma.lemmatize(w, lang=code)


def run(root: Path, top: int, model: str, effort: str, retries: int, review: bool,
        force: bool, reshare: bool, only: set[str] | None, rank_only: bool,
        repair_rounds: int = 2) -> int:
    from tools.generate import Generator
    import simplemma
    cfg = load_config(root)
    paths = LanguagePaths(root)
    words = load_json(WordList, paths.words)
    entries = load_entries(paths)
    index = load_index()
    verbs_idx = index["verbs"]
    rs, disagree = readings(words, entries, verbs_idx, simplemma_lemmatizer(cfg.code),
                            set(index.get("nonverb", ())))
    cands = candidates(rs, top)
    lower, upper = bounds(rs)
    print(f"{len(rs)} forms with a verb reading, {sum(r.ambiguous for r in rs.values())} ambiguous; "
          f"{len(cands)} candidates", file=sys.stderr)

    gen = Generator(model, effort, CACHE / "api.jsonl")
    shares = estimate_shares(gen, rs, cands, CACHE / "shares.json", reshare)
    ranked = rank(rs, shares, top)
    report = [f"# verbs.py report ({dt.date.today().isoformat()}, {model})", "",
              f"kaikki: {index['file']} sha256 {index['sha256'][:16]}..., simplemma "
              f"{simplemma.__version__ if hasattr(simplemma, '__version__') else '?'}", "",
              "## Ranking", "", "| # | verb | total | lower | upper | splits |", "|--|--|--|--|--|--|"]
    for i, rk in enumerate(ranked, 1):
        report.append(f"| {i} | {rk.base} | {rk.total} | {lower.get(rk.base, 0)} | {upper.get(rk.base, 0)} | "
                      + ", ".join(f"{s.form} {s.verb_share:.0%}" for s in rk.splits) + " |")
    nxt = rank(rs, shares, top + 5)[top:]
    report += ["", "Next: " + ", ".join(f"{r.base} {r.total}" for r in nxt), "",
               f"## simplemma vs entries ({len(disagree)} disagreements)", ""] + [f"- {d}" for d in disagree]
    print("\n".join(report), file=sys.stderr)
    if rank_only:
        _write_json(CACHE / "ranking.json", [{"base": r.base, "total": r.total} for r in ranked])
        print(f"{gen.usage} ~${gen.usage.cost(model):.2f}", file=sys.stderr)
        return 0

    report += ["", "## kaikki cross-check", ""]
    out: list[Verb] = []
    today = dt.date.today().isoformat()
    for rk in ranked:
        gpath, rpath = CACHE / "gen" / f"{rk.base}.json", CACHE / "review" / f"{rk.base}.json"
        fpath = CACHE / "repair" / f"{rk.base}.json"
        p = verbs_idx.get(rk.base)
        redo = force and (only is None or rk.base in only)
        if gpath.exists() and not redo:
            g = GenVerb.model_validate_json(gpath.read_text(encoding="utf-8"))
            mismatch, checked, missing = crosscheck(g, p)
            if problems := check_verb(g, rk.base):
                raise RuntimeError(f"cached {gpath} fails checks: {problems} (use --force)")
        else:
            g, mismatch, (checked, missing) = generate_verb(gen, rk, p, retries)
            gpath.parent.mkdir(parents=True, exist_ok=True)
            gpath.write_text(g.model_dump_json(indent=1), encoding="utf-8")
            for old in (rpath, fpath):
                if old.exists():
                    old.unlink()
        rv = None
        if review:
            if rpath.exists():
                rv = VerbReview.model_validate_json(rpath.read_text(encoding="utf-8"))
            else:
                rv = review_verb(gen, g)
                rpath.parent.mkdir(parents=True, exist_ok=True)
                rpath.write_text(rv.model_dump_json(indent=1), encoding="utf-8")
            if fpath.exists():
                fx = Repair.from_json(fpath.read_text(encoding="utf-8"))
            else:
                fx = repair_verb(gen, g, rv, p, repair_rounds, retries)
                fpath.parent.mkdir(parents=True, exist_ok=True)
                fpath.write_text(fx.to_json() + "\n", encoding="utf-8")
            g = fx.verb
            mismatch, checked, missing = crosscheck(g, p)
            if problems := check_verb(g, rk.base):
                raise RuntimeError(f"{fpath} fails checks: {problems} (use --force)")
        report.append(f"- **{rk.base}**: {checked} cells checked, {missing} without kaikki data, "
                      f"{len(mismatch)} mismatches" + "".join(f"\n  - {m}" for m in mismatch))
        if rv and rv.issues:
            acts = [a for r in fx.rounds for a in r["actions"]]
            report.append(f"  - reviewer: {len(rv.issues)} flags; repair: "
                          f"{sum(a['action'] == 'fixed' for a in acts)} fixed, "
                          f"{sum(a['action'] == 'dismissed' for a in acts)} dismissed, "
                          f"{len(fx.rounds)} round(s), {len(fx.open)} still open"
                          + "".join(f"\n    - OPEN {i.tense}.{i.person}: {i.comment}" for i in fx.open)
                          + "".join(f"\n    - REJECTED repair: {x}" for r in fx.rounds for x in r["rejected"]))
            for i in fx.open:
                print(f"open review flag: {rk.base} {i.tense}.{i.person}: {i.comment}", file=sys.stderr)
        out.append(to_verb(g, rk, f"{count_note(rk)} | generated by {model} "
                                  f"(tools/verbs.py, {today})"))

    data = Verbs(schema_version=SCHEMA_VERSION, language=cfg.code, verbs=out, persons=PERSONS, notes=(
        f"Top {top} verbs by total_count, built by `python -m tools.verbs {root.name}` on {today}. "
        "Ranking: words.json has no `base`, so each form's verb(s) come from its entry "
        "(VERB/AUX meanings[].base, orders 1-100) or, without an entry, from simplemma "
        f"({getattr(simplemma, '__version__', '2.x')}, lang '{cfg.code}') plus every verb whose kaikki "
        "paradigm contains the form. Forms claimed by more than one reading (another verb, or a "
        f"non-verb use like possessive 'sein'/'meine') get model-estimated shares ({model}); only "
        "the verb's share is counted and listed in `count_splits`. Auxiliary and modal uses count. "
        f"Forms and examples generated by {model}; forms cross-checked against the kaikki.org "
        f"English-Wiktionary German extract ({index['file']}, sha256 {index['sha256'][:16]}..., "
        f"downloaded {index['built']}); mismatches are reviewed by a human. "
        + ("Reviewer pass by the same model; every flag was acted on by a repair pass (example "
           "fixed, or flag dismissed as not an error) and re-reviewed; flags are not stored. "
           if review else "")
        + "Tables and examples are exempt from the known-words rule."))
    dump_json(data, paths.verbs)
    (CACHE / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    errs = [e for e in validate_language(root) if "verbs.json" in e]
    print(f"wrote {paths.verbs} ({len(out)} verbs); report {CACHE / 'report.md'}; "
          f"{gen.usage} ~${gen.usage.cost(model):.2f}", file=sys.stderr)
    for e in errs:
        print(f"error: {e}", file=sys.stderr)
    return 1 if errs else 0


def main(argv: list[str] | None = None) -> int:
    from tools.generate import DEFAULT_MODEL, PRICES
    ap = argparse.ArgumentParser(prog="python -m tools.verbs", description=__doc__.split("\n\n")[0])
    ap.add_argument("lang", type=Path, help="language directory, e.g. german")
    ap.add_argument("--top", type=int, default=DEFAULT_TOP)
    ap.add_argument("--model", default=DEFAULT_MODEL, choices=sorted(PRICES))
    ap.add_argument("--effort", default="high", choices=["low", "medium", "high", "xhigh", "max"])
    ap.add_argument("--retries", type=int, default=2)
    ap.add_argument("--no-review", dest="review", action="store_false")
    ap.add_argument("--repair-rounds", type=int, default=2,
                    help="review -> repair -> re-review rounds per verb")
    ap.add_argument("--force", action="store_true", help="regenerate cached verbs (see --only)")
    ap.add_argument("--only", type=lambda s: set(s.split(",")), help="with --force: only these bases")
    ap.add_argument("--reshare", action="store_true", help="re-estimate the cached count shares")
    ap.add_argument("--rank-only", action="store_true")
    ap.add_argument("--reindex", action="store_true", help="rebuild cache/kaikki/verb-index.json")
    a = ap.parse_args(argv)
    if a.reindex:
        build_index()
    return run(a.lang, a.top, a.model, a.effort, a.retries, a.review, a.force, a.reshare,
               a.only, a.rank_only, a.repair_rounds)


if __name__ == "__main__":
    sys.exit(main())
