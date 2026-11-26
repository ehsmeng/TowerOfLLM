"""Build a language's ranked word-form list (``<lang>/json/words.json``) from a
sentence corpus. Language-neutral; the language plugs in through a small module
``<lang>/wordlist.py`` (see ``german/wordlist.py``) that defines:

    EXPORT_URL: str                       # Tatoeba-style TSV export (id \\t lang \\t text), .bz2
    modernize(token: str) -> str          # spelling normalization (e.g. daß -> dass)
    split_clitics(token: str) -> list[str]  # e.g. "geht's" -> ["geht", "es"]
    is_excluded(form: str) -> bool        # proper names and other non-vocabulary

Pipeline (each step is documented in the words.json `notes` it writes):

1. Download the export into ``cache/`` (gitignored); record date + sha256.
2. NFC-normalize; drop near-duplicate sentences (same text after lowercasing and
   removing everything except letters), keeping the first by sentence id.
3. Tokenize: runs of letters with internal hyphens/apostrophes. Digits and
   punctuation are never part of a token. Tokens must be all Latin script and at
   least 2 letters.
4. Case folding. A token is *ambiguous* when it opens the sentence or follows
   . ! ? : ; or an opening quote/dash, because a capital there says nothing.
   Unambiguous tokens are counted as written. Each capitalized ambiguous token is
   split between its capitalized and lowercased form in proportion to how often
   each appears unambiguously (``Sie``/``sie``, ``Essen``/``essen``); if neither
   appears unambiguously it goes to the lowercased form. Counts are rounded to
   integers at the end.
5. Drop excluded forms, rank by count descending, ties alphabetically
   (casefolded, then exact form), and keep the top ``word_count`` forms.
   In this file ``order == frequency_rank``.

CLI:
    python -m tools.frequency german            # uses cached download if present
    python -m tools.frequency german --refresh  # re-download the export
"""

from __future__ import annotations

import argparse
import bz2
import datetime as dt
import hashlib
import importlib.util
import json
import re
import sys
import unicodedata
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Iterable, Iterator

from tools.schema import (SCHEMA_VERSION, LanguagePaths, WordList, WordListItem,
                          dump_json, load_config, validate_language)

REPO = Path(__file__).resolve().parent.parent
CACHE = REPO / "cache"

TOKEN_RE = re.compile(r"[^\W\d_]+(?:[-'’][^\W\d_]+)*")
# A capital after any of these (or at sentence start) carries no information.
AMBIGUOUS_GAP_RE = re.compile(r"[.!?:;„“”\"«»‹›‚‘–—(\[]")


# ---------------------------------------------------------------------------
# Download / read
# ---------------------------------------------------------------------------


@dataclass
class Download:
    path: Path
    url: str
    sha256: str
    date: str  # ISO date the file was downloaded


def fetch(url: str, refresh: bool = False) -> Download:
    """Download `url` into cache/ unless already there. A sidecar .meta.json
    records the download date, so a cached file keeps its original date."""
    CACHE.mkdir(exist_ok=True)
    path = CACHE / url.rsplit("/", 1)[-1]
    meta = path.with_name(path.name + ".meta.json")
    if refresh or not path.exists() or not meta.exists():
        tmp = path.with_name(path.name + ".part")
        print(f"downloading {url}", file=sys.stderr)
        with urllib.request.urlopen(url) as r, tmp.open("wb") as fh:
            while chunk := r.read(1 << 20):
                fh.write(chunk)
        tmp.replace(path)
        meta.write_text(json.dumps({"url": url, "date": dt.date.today().isoformat()}) + "\n")
    info = json.loads(meta.read_text())
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    return Download(path, info["url"], sha, info["date"])


def read_tatoeba(path: Path) -> Iterator[tuple[int, str]]:
    """Yield (sentence id, NFC text) from a Tatoeba per-language TSV(.bz2) export."""
    opener = bz2.open if path.suffix == ".bz2" else open
    with opener(path, "rt", encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            parts = line.rstrip("\n").split("\t")
            if len(parts) != 3:
                raise ValueError(f"{path}:{n}: expected 3 tab-separated fields, got {len(parts)}")
            yield int(parts[0]), unicodedata.normalize("NFC", parts[2])


def dedupe(sentences: Iterable[tuple[int, str]]) -> tuple[list[str], int]:
    """Drop sentences equal to an earlier one (by id) after lowercasing and
    keeping only letters. Returns (kept texts, number dropped)."""
    seen: set[str] = set()
    kept: list[str] = []
    dropped = 0
    for _, text in sorted(sentences):
        key = "".join(ch for ch in text.casefold() if ch.isalpha())
        if key in seen:
            dropped += 1
            continue
        seen.add(key)
        kept.append(text)
    return kept, dropped


# ---------------------------------------------------------------------------
# Counting
# ---------------------------------------------------------------------------


def _is_latin_word(tok: str) -> bool:
    letters = [ch for ch in tok if ch.isalpha()]
    return len(letters) >= 2 and all("LATIN" in unicodedata.name(ch, "") for ch in letters)


def _lower_first(tok: str) -> str:
    return tok[:1].lower() + tok[1:]


def tokens(text: str, lang: ModuleType) -> Iterator[tuple[str, bool]]:
    """Yield (token, ambiguous_case) for one sentence, after clitic splitting
    and spelling modernization."""
    prev_end = None
    for m in TOKEN_RE.finditer(text):
        gap = text[prev_end:m.start()] if prev_end is not None else ""
        ambiguous = prev_end is None or bool(AMBIGUOUS_GAP_RE.search(gap))
        prev_end = m.end()
        for k, part in enumerate(lang.split_clitics(m.group())):
            part = lang.modernize(part)
            if _is_latin_word(part):
                yield part, ambiguous and k == 0


@dataclass
class Counts:
    forms: Counter            # final integer counts per form, before exclusion
    sentences: int
    tokens: int
    ambiguous: int            # capitalized tokens in ambiguous position
    excluded: Counter         # excluded forms with their counts


def count_forms(texts: Iterable[str], lang: ModuleType) -> Counts:
    sure: Counter = Counter()        # tokens whose case is informative
    amb: Counter = Counter()         # capitalized tokens in ambiguous position
    n_sent = n_tok = 0
    for text in texts:
        n_sent += 1
        for tok, ambiguous in tokens(text, lang):
            n_tok += 1
            if ambiguous and tok[:1].isupper() and not tok.isupper():
                amb[tok] += 1
            else:
                sure[tok] += 1

    frac: defaultdict[str, float] = defaultdict(float, sure)
    for tok, c in amb.items():
        lo = _lower_first(tok)
        up_n, lo_n = sure.get(tok, 0), sure.get(lo, 0)
        if up_n + lo_n == 0:
            frac[lo] += c
        else:
            frac[tok] += c * up_n / (up_n + lo_n)
            frac[lo] += c * lo_n / (up_n + lo_n)

    forms: Counter = Counter()
    excluded: Counter = Counter()
    for f, c in frac.items():
        n = round(c)
        if n < 1:
            continue
        (excluded if lang.is_excluded(f) else forms)[f] = n
    return Counts(forms, n_sent, n_tok, sum(amb.values()), excluded)


def rank(forms: Counter) -> list[tuple[str, int]]:
    """Descending count; ties alphabetical (casefolded, then exact form)."""
    return sorted(forms.items(), key=lambda fc: (-fc[1], fc[0].casefold(), fc[0]))


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def load_language_module(root: Path) -> ModuleType:
    path = root / "wordlist.py"
    spec = importlib.util.spec_from_file_location(f"{root.name}_wordlist", path)
    if spec is None or spec.loader is None:
        raise FileNotFoundError(path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for name in ("EXPORT_URL", "modernize", "split_clitics", "is_excluded"):
        if not hasattr(mod, name):
            raise AttributeError(f"{path}: missing required '{name}'")
    return mod


def build(root: Path, refresh: bool = False) -> WordList:
    cfg = load_config(root)
    lang = load_language_module(root)
    dl = fetch(lang.EXPORT_URL, refresh)
    texts, dropped = dedupe(read_tatoeba(dl.path))
    counts = count_forms(texts, lang)
    ranked = rank(counts.forms)[: cfg.word_count]
    words = [WordListItem(order=i, form=f, frequency_rank=i, count=c, base=None)
             for i, (f, c) in enumerate(ranked, 1)]
    top_excl = ", ".join(f"{f} {c}" for f, c in counts.excluded.most_common(10))
    notes = (
        f"Built by `python -m tools.frequency {root.name}`. "
        f"Export {dl.url} downloaded {dl.date}, sha256 {dl.sha256}. "
        f"{counts.sentences + dropped} sentences, {dropped} near-duplicates dropped "
        f"(same letters after lowercasing), {counts.sentences} counted, {counts.tokens} tokens, "
        f"{len(counts.forms)} candidate forms; top {cfg.word_count} kept. "
        f"Case: {counts.ambiguous} capitalized tokens at sentence start or after . ! ? : ; quotes "
        f"were split between capitalized and lowercase form by their mid-sentence ratio "
        f"(lowercase if never seen mid-sentence). Spelling modernized ({root.name}/wordlist.py). "
        f"Excluded {len(counts.excluded)} forms as proper names/non-vocabulary "
        f"({root.name}/names.txt), largest: {top_excl}. "
        f"Ties broken alphabetically. order = frequency_rank; reordering happens in review."
    )
    return WordList(schema_version=SCHEMA_VERSION, language=cfg.code, source=cfg.source,
                    words=words, notes=notes)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tools.frequency")
    ap.add_argument("language", type=Path, help="language directory, e.g. german")
    ap.add_argument("--refresh", action="store_true", help="re-download the export")
    args = ap.parse_args(argv)
    wl = build(args.language, args.refresh)
    out = LanguagePaths(args.language).words
    dump_json(wl, out)
    print(f"wrote {out} ({len(wl.words)} forms)", file=sys.stderr)
    errs = validate_language(args.language)
    for e in errs:
        print(e, file=sys.stderr)
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
