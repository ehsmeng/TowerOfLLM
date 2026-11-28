"""Sentence checker: the known-words rule, enforced by code.

Every sentence in entry N may use only word forms 1..N (learning order, from
``<lang>/json/words.json``). Every example of a grammar concept may use only
forms with order <= that concept's ``first_entry``. ``verbs.json`` conjugation
tables are exempt.

Structure and cross-file consistency are checked by ``tools.schema``; this
checker runs that first and stops if it fails, so it never reasons about
malformed data.

Tokenization (same as the frequency build in tools/frequency.py, so a token
here is the same thing that was counted there):

- Tokens are runs of letters with internal hyphens/apostrophes (``E-Mail``).
  Punctuation is stripped. Digits are forbidden (``3``, ``2026`` are
  violations): numbers are written as words, and those (``drei``) must be
  known forms like any other.
- Clitics are split by the language hook ``split_clitics`` (``geht's`` ->
  ``geht`` + ``es``). An apostrophe part the hook would drop (``wie'n``) is a
  violation: write it out. (A trailing ``hab'`` is caught anyway, as ``hab``
  is not a form.)
- Spelling is modernized by the language hook ``modernize`` before matching
  (``daß`` -> ``dass``), the same normalization the frequency count used.
- Case: a token must match a form exactly. In an *ambiguous* position (sentence
  start, or after ``. ! ? : ;``, a quote or a dash) a capitalized token also
  matches its lowercased form, since the capital there only marks position.
  So mid-sentence ``Essen`` needs the noun entry, ``Ich bin hier.`` needs ``ich``.
- Contractions (``im``, ``zum``) and separable-verb particles (``auf``) are
  plain tokens: known only once that exact form has been introduced.
- Entries: with an explicit ``--to``, every order in the range must have an
  entry file; a missing one is a violation, not silently skipped.
- Proper names: forms that the language module lists in ``NAMES`` with category
  ``person`` or ``place`` (``<lang>/names.txt`` for German) always pass.

CLI:
    python -m tools.checker german                  # all entries
    python -m tools.checker german --from 1 --to 100
Exit 0 = clean, 1 = schema errors or violations (one line each on stderr).
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Iterator

from tools.frequency import AMBIGUOUS_GAP_RE, TOKEN_RE, load_language_module
from tools.schema import (Entry, Grammar, LanguagePaths, WordList, load_json,
                          stem, validate_language)

ALLOWED_NAME_CATEGORIES = {"person", "place"}
APOSTROPHE_RE = re.compile(r"['’]")
DIGITS_RE = re.compile(r"\d+")


@dataclass
class Token:
    text: str
    ambiguous: bool       # capital carries no information here
    elided: bool = False  # whole raw token; split_clitics dropped part of it


@dataclass
class Violation:
    where: str        # e.g. "00015 war meanings[0].sentences[2]"
    sentence: str
    token: str
    reason: str

    def __str__(self) -> str:
        return f"{self.where}: {self.token!r} {self.reason} -- {self.sentence!r}"


def tokenize(text: str, lang: ModuleType | None = None) -> Iterator[Token]:
    prev_end = None
    for m in TOKEN_RE.finditer(text):
        gap = text[prev_end:m.start()] if prev_end is not None else ""
        ambiguous = prev_end is None or bool(AMBIGUOUS_GAP_RE.search(gap))
        prev_end = m.end()
        raw = m.group()
        split = getattr(lang, "split_clitics", None)
        modernize = getattr(lang, "modernize", None)
        parts = split(raw) if split else [raw]
        if len(parts) < len(APOSTROPHE_RE.split(raw)):
            yield Token(raw, ambiguous, elided=True)
        for k, part in enumerate(parts):
            yield Token(modernize(part) if modernize else part, ambiguous and k == 0)


class Vocabulary:
    """Word forms with their learning order, plus always-allowed names."""

    def __init__(self, words: WordList, names: set[str]):
        self.order = {w.form: w.order for w in words.words}
        self.names = names

    def first_order(self, tok: Token) -> int | None:
        """Earliest order at which `tok` becomes usable; 0 for names; None if never."""
        if tok.text in self.names:
            return 0
        cands = [self.order.get(tok.text)]
        if tok.ambiguous and tok.text[:1].isupper():
            cands.append(self.order.get(tok.text[:1].lower() + tok.text[1:]))
        cands = [c for c in cands if c is not None]
        return min(cands) if cands else None

    def check(self, text: str, upto: int, where: str, lang: ModuleType | None) -> list[Violation]:
        out = [Violation(where, text, d, "digits not allowed (write the number as a known word)")
               for d in DIGITS_RE.findall(text)]
        for tok in tokenize(text, lang):
            if tok.elided:
                out.append(Violation(where, text, tok.text, "drops an apostrophe part (write it out)"))
                continue
            first = self.first_order(tok)
            if first is None:
                out.append(Violation(where, text, tok.text, "not in word list"))
            elif first > upto:
                out.append(Violation(where, text, tok.text, f"not known until order {first} (limit {upto})"))
        return out


def _names(lang: ModuleType | None) -> set[str]:
    names = getattr(lang, "NAMES", {}) if lang else {}
    return {f for f, cat in names.items() if cat in ALLOWED_NAME_CATEGORIES}


def check_language(root: Path, lo: int = 1, hi: int | None = None) -> list[str]:
    """Return schema errors (if any, nothing else is checked) or violations
    for entries and grammar concepts whose order / first_entry is in [lo, hi]."""
    errs = validate_language(root)
    if errs:
        return [f"schema: {e}" for e in errs]

    paths = LanguagePaths(root)
    lang = load_language_module(root) if (root / "wordlist.py").exists() else None
    vocab = Vocabulary(load_json(WordList, paths.words), _names(lang))
    in_range = lambda n: n >= lo and (hi is None or n <= hi)

    out: list[str] = []
    seen: set[int] = set()
    if paths.entries_dir.exists():
        for p in sorted(paths.entries_dir.glob("*.json")):
            e = load_json(Entry, p)
            if not in_range(e.order):
                continue
            seen.add(e.order)
            for i, m in enumerate(e.meanings):
                for j, s in enumerate(m.sentences):
                    where = f"{stem(e.order, e.form)} meanings[{i}].sentences[{j}]"
                    out += map(str, vocab.check(s.text, e.order, where, lang))

    if hi is not None:
        forms = {o: f for f, o in vocab.order.items()}
        for n in range(lo, hi + 1):
            if n not in seen:
                label = stem(n, forms[n]) if n in forms else f"{n:05d}"
                out.append(f"{label}: entry missing (range {lo}..{hi})")

    if paths.grammar.exists():
        for c in load_json(Grammar, paths.grammar).concepts:
            if not in_range(c.first_entry):
                continue
            for j, ex in enumerate(c.examples):
                where = f"grammar '{c.id}' (first_entry {c.first_entry}) examples[{j}]"
                out += map(str, vocab.check(ex.text, c.first_entry, where, lang))

    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tools.checker", description=__doc__.split("\n\n")[0])
    ap.add_argument("lang", type=Path, help="language directory, e.g. german")
    ap.add_argument("--from", dest="lo", type=int, default=1, help="first entry order (default 1)")
    ap.add_argument("--to", dest="hi", type=int, default=None, help="last entry order (default: all)")
    a = ap.parse_args(argv)
    problems = check_language(a.lang, a.lo, a.hi)
    for line in problems:
        print(line, file=sys.stderr)
    rng = f"{a.lo}..{a.hi if a.hi is not None else 'end'}"
    print(f"{a.lang}: {len(problems)} problem(s) in entries {rng}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
