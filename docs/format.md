# Data format and repo layout

Every language uses the same layout and file format, so the code in `tools/`
works for any of them. `tools/schema.py` is the source of truth for field
names. This page explains them. Validate with:

```
python -m tools.schema validate german                 # exit 1 + one line per error
python -m tools.schema validate docs/example/german    # the illustrative data set
python -m tools.schema jsonschema [entry|words|grammar|verbs]   # JSON Schema export
```

## Layout

```
tools/                         shared Python (language-neutral)
  schema.py                    dataclasses, load/dump, validator
  frequency.py                 corpus download + count + rank -> words.json
cache/                         raw corpus downloads (gitignored)
docs/format.md                 this file
docs/example/german/           illustrative data set (same shape as german/)
german/
  language.toml                code, names, PDF title, word_count, max_reorder, source
  wordlist.py                  German hooks for tools/frequency.py (spelling, clitics, exclusions)
  names.txt                    proper names excluded from the word list
  json/
    words.json                 word forms in learning order
    grammar.json               grammar concepts, each with the entry that introduces it
    verbs.json                 the 20 most common verbs, fully conjugated (PDF appendix)
    entries/00001 ich.json     one file per word form
  audio/00001 ich.mp3          one file per entry, same stem as its JSON
  first 5k german words.pdf    filename = language.toml `title` + .pdf
french/ …                      same shape
```

Small language-specific code (spelling modernization, name/foreign-word
filters) goes in `<lang>/` next to `language.toml`. Shared logic stays in
`tools/`.

## Learning order vs. frequency rank

Words are taught in **learning order** (`order`), which is frequency order
with small changes so that early sentences can be formed. For example, `ich`
and `bin` are moved to the front so that "Ich bin." is possible at order 2.
Each word also records its `frequency_rank` (its position in the source
frequency list). `language.toml` `max_reorder` (50 for German) limits how far
a word may move: `|order − frequency_rank| ≤ max_reorder`.

`order` drives the filenames. **The learning order must be final before
content and audio are generated.** Reordering later means renaming every
entry and mp3 after the moved word and rechecking the known-words rule. The
reordering itself is done by the word-list tickets.

## Filenames

- The stem is `<order, zero-padded to 5 digits> <form>`, e.g. `00002 bin`,
  `00016 für`. JSON and mp3 use the same stem (`schema.stem()`).
- Umlauts and ß are kept as UTF-8. Filenames and all text are **NFC**
  (composed characters), and the validator rejects anything else. This matters
  on macOS, which can hand back NFD names.
- The order prefix makes names unique, even on case-insensitive filesystems
  (`Sie` vs `sie`).

## Word forms, case, spelling

The `form` field holds a word form exactly as it is taught. Following the
frequency-list ticket, sentence-initial capitals are folded to lowercase. A
capitalized form stays capitalized only when it is really a noun, so `Essen`
and `essen` can be two different words. The schema stores whatever form it is
given; the frequency-list ticket owns the folding rule. All spelling and
grammar is modern standard German (reformed spelling, 1996/2006).

Every inflected form is its own entry (`bin`, `ist`, `war`).

## Entry (`json/entries/NNNNN <form>.json`)

| field | meaning |
|---|---|
| `schema_version` | currently `1` |
| `language` | ISO 639-1, must match `language.toml` `code` |
| `order`, `form` | must match `words.json` and the filename |
| `base` | primary lemma (what `words.json` shows) |
| `translation` | headline English translation for the page header |
| `meanings[]` | one or more, in teaching order |
| `notes` | optional free text, allowed on every object; never rendered |

**Meaning:** `gloss` (short English), `base` (lemma for *this* meaning),
`pos` (UPOS tag: NOUN, VERB, AUX, DET, PRON, …), optional `morph`
(free-text morphology, e.g. "simple past, 1st/3rd person singular"), and
`sentences[]`. Base and POS are stored per meaning so that homographs fit in
one entry: `sein` = "to be" (VERB, base `sein`) and "his" (DET, base `sein`);
`die` = article and relative pronoun.

**Sentence limits:** at most **10 per meaning** and **20 per entry** (the
validator enforces both). When writing content, spread the sentences evenly
across meanings: 1 meaning → 10, 2 → 10 each, 3 → 6–7 each, 4 → 5 each.
Write fewer when the known vocabulary doesn't allow more. So entries with
several meanings are longer than others.

**Sentence:** `text` (target language), `en` (English), and `grammar_notes[]`
(ids of grammar concepts this sentence *introduces*). The keys are fixed
(`text`/`en`), not language codes, so the same code reads every language.

Early entries may have zero sentences (order 1 has no prior vocabulary).

## Word list (`json/words.json`)

Has `schema_version`, `language`, `source`, and `words[]`. Each item in
`words[]` has `order`, `form`, `frequency_rank`, `count` and `base`. The
validator checks that:

- orders are contiguous from 1 in array order;
- forms are unique, and `frequency_rank` values are unique;
- `|order − frequency_rank| ≤ max_reorder`.

`base` may be `null` while the list is being built, or when the form's
meanings have different lemmas (`sie`). When `base` is set, it must equal the
entry's `base`.

## Grammar (`json/grammar.json`)

Has `schema_version`, `language`, and `concepts[]`. Each concept has:

- `id`: dotted lowercase, e.g. `verb.sein.praeteritum`
- `title`
- `explanation`: English, shown in the PDF on first use
- `first_entry`: the order of the entry that introduces the concept
- `related[]`: ids of other concepts
- `examples[]`: sentences that use the concept, each `{text, en, notes?}`.
  The target is 3. Use fewer when the vocabulary up to `first_entry` can't
  support 3 natural sentences. Examples may only use forms with
  order ≤ `first_entry`.

The explanation text lives only here. A sentence just lists the id. The
validator checks that:

- every id used in a sentence exists in `grammar.json`;
- each concept is introduced in exactly one sentence, and that sentence is in
  the entry at `first_entry` (this is checked once that entry exists);
- every id in `related` exists;
- `examples` has at most 3 items, each with non-empty `text`/`en`.

The validator does **not** check *semantic* first use, such as whether
`Präteritum` really appeared earlier without a note. It also skips the
known-words rule, both for entry sentences and for grammar examples. These
belong to the sentence checker (`write-sentence-checker`).

## Verbs (`json/verbs.json`)

Source data for the PDF appendix. Has `schema_version`, `language`, and
`verbs[]`: the 20 most common verbs, sorted by `total_count` descending.
`total_count` is the summed `count` of all the verb's forms in `words.json`,
grouped by `base` (`bin` + `ist` + `war` + … → `sein`). Count only forms whose
entry has a VERB/AUX meaning with that base, so possessive `sein` is not
counted.

Each verb has:

- `base` (infinitive), `translation` ("to be"), `total_count`
- `tenses[]`: each item is `{tense, label, forms}`. `tense` is an id
  (`praesens`, `praeteritum`, `perfekt`, `plusquamperfekt`, `futur_i`,
  `futur_ii`, `konjunktiv_i`, `konjunktiv_ii`, `imperativ` for German).
  `label` is the table heading. `forms` maps person/number labels to forms, in
  display order (`"ich": "bin"`, …; the imperative has only `du`/`ihr`/`Sie`).
  Tense ids and person labels are data, so other languages use their own
  without schema changes. Compound tenses store the full phrase
  (`"bin gewesen"`).
- `participles`: e.g. `{"present": "seiend", "past": "gewesen"}`

The validator checks structure (unique verbs, unique tense ids per verb,
non-empty NFC forms), the sort order, and that each `base` occurs in
`words.json`. It does not recompute `total_count`. Verb tables are exempt from
the known-words rule.

## Example

`docs/example/german/` is an **illustrative** set, not real data:
`language.toml` (copy of German's), `words.json` with invented counts and
ranks showing a reorder (`ich`, `bin` first), entries `00001 ich` (zero
sentences), `00002 bin` (one sentence) and `00015 war` (six sentences, two
grammar introductions), a matching `grammar.json` with examples, and
`verbs.json` with `sein` fully conjugated. `german/json/words.json` is real
data, built by `python -m tools.frequency german` (method in its `notes` and
in the `tools/frequency.py` docstring).
