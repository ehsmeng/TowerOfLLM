"""German hooks for tools/frequency.py (see its docstring for the contract)."""

from __future__ import annotations

from pathlib import Path

EXPORT_URL = "https://downloads.tatoeba.org/exports/per_language/deu/deu_sentences.tsv.bz2"

HERE = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Spelling: pre-1996 ß after a short vowel -> ss. Tatoeba still has many old
# forms (daß ~8.6k vs dass ~40k). ß->ss can't be decided by rule (Fuß stays,
# Fluß -> Fluss), so this is an explicit list built from every ß-form in the
# corpus whose ss-spelling also occurs, minus correct modern ß words (Maße,
# Buße, Weiß, Strauß). Keys have a lowercase first letter; the token's
# initial capital is preserved.
# ---------------------------------------------------------------------------

OLD_SS = """
daß muß mußt müßt mußte mußten mußtest mußtet müßte müßten müßtest müßtet gemußt
wußte wußten wußtest wußtet wüßte wüßten wüßtest wißt gewußt bewußt bewußtsein
unbewußt bewußtlos
laß laßt läßt verläßt verlaßt entläßt hinterläßt zuläßt überläßt überlaßt verlaß
iß ißt eßt eßbar aufißt frißt vergißt vergeßt vergiß vergeßlich
faßt faßte gefaßt verfaßt befaßt angefaßt zusammengefaßt unfaßbar
paßt paßte verpaßt anpaßt aufpaßt aufgepaßt veranlaßt
küß küßt küßte küßten geküßt küßchen kuß abschiedskuß
haß haßt haßte haßten gehaßt verhaßt häßlich häßliche häßlichen
mißt vermißt vermißte vermißten mißtrauen mißtrauisch mißverständnis
mißverstanden mißbrauch mißerfolg mißstände mißfallen
schluß schlußfolgerung abschluß entschluß anschluß beschluß
fluß einfluß beeinflußt überfluß genuß schuß schoß erschoß schloß beschloß
genoß goß floß naß klitschnaß blaß paß reisepaß laufpaß paßwort anlaß
prozeß kompromiß kompaß faß nuß streß gestreßt bißchen biß riß imbißstube
gewiß gewißheit gräßlich verläßlich verdruß tschüß täßchen
eßstörung fitneßstudio obergeschoß rußland gepißt
""".split()


def _ss(w: str) -> str:
    return w.replace("ß", "ss")


MODERN = {w: _ss(w) for w in OLD_SS if "ß" in w}


# Capitals that carry no meaning: the optional letter-style "Du/Dir/Euch",
# and interjections/pronouns capitalized after a dash or inside a quote the
# tokenizer did not see as sentence start.
FOLD_LOWER = {
    "Du", "Dich", "Dir", "Dein", "Deine", "Deinen", "Deinem", "Deiner", "Deines",
    "Euch", "Euer", "Eure", "Euren", "Eurem", "Eurer",
    "Ich", "Nein", "Ja", "Danke", "Hallo", "Ach",
}


def modernize(token: str) -> str:
    if token in FOLD_LOWER:
        return token.lower()
    low = token[:1].lower() + token[1:]
    new = MODERN.get(low)
    if new is None:
        return token
    return new[:1].upper() + new[1:] if token[:1].isupper() else new


# ---------------------------------------------------------------------------
# Clitics: geht's / gibt’s -> geht + es. Other apostrophe parts ('n, hab')
# keep only the host word.
# ---------------------------------------------------------------------------

CLITICS = {"s": "es"}


def split_clitics(token: str) -> list[str]:
    if "'" not in token and "’" not in token:
        return [token]
    head, *rest = token.replace("’", "'").split("'")
    return [head] + [CLITICS[r.lower()] for r in rest if r.lower() in CLITICS]


# ---------------------------------------------------------------------------
# Exclusions: german/names.txt, one "<form> <category>" per line, # comments.
# Categories: person, place, brand, foreign, other, country.
# Countries are kept as vocabulary; the rest is excluded. Genitive -s of an
# excluded name (Toms, Marias) is excluded too.
# ---------------------------------------------------------------------------

EXCLUDED_CATEGORIES = {"person", "place", "brand", "foreign", "other"}


def _load_names() -> dict[str, str]:
    out: dict[str, str] = {}
    for n, line in enumerate((HERE / "names.txt").read_text(encoding="utf-8").splitlines(), 1):
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        form, cat = line.split()
        if cat not in EXCLUDED_CATEGORIES | {"country"}:
            raise ValueError(f"names.txt:{n}: unknown category '{cat}'")
        if form in out:
            raise ValueError(f"names.txt:{n}: duplicate '{form}'")
        out[form] = cat
    return out


NAMES = _load_names()
EXCLUDED = {f for f, c in NAMES.items() if c in EXCLUDED_CATEGORIES}


def is_excluded(form: str) -> bool:
    if form in EXCLUDED:
        return True
    return form.endswith("s") and form[:-1] in EXCLUDED
