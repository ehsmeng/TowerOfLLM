---
slug: define-language-neutral-json-format-and-repo-layou
title: Define language-neutral JSON format and repo layout
status: done
autonomy: interactive
owner: ehsmeng
human: ehsmeng
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: build/agent-then-review
  steps:
  - name: build
    skills: []
    assignee: agent
  - name: review
    skills: []
    assignee: human
  - name: finalize
    skills: []
    assignee: agent
secrets: null
script: null
---

## Description

Define the JSON data format and repo layout every language will share, so `german/` is built once and `french/` etc. can mirror it. Output: a short spec plus a schema (JSON Schema or Python dataclasses in `tools/`) that later tickets write to and validate against.

## Context

Project: German vocabulary course for English speakers, with word frequencies from Tatoeba's German sentences (tatoeba.org, CC BY 2.0 FR; counts only, sentences are newly written). Content is CC BY 4.0, code MIT. Target: 5,000 word forms in learning order (frequency order, adjusted by at most 50 positions so early sentences can be formed) (count is a parameter; 10k possible later). Pilot: first 100 words. Layout: shared Python in `tools/`, data in `german/json/` (one JSON file per word), audio in `german/audio/`, PDF `german/first 5k german words.pdf`. Later languages (e.g. `french/json/`) mirror the same layout.

- Decided: one JSON file per word at `german/json/entries/<00001> <form>.json` (5-digit zero-padded rank, same stem as the mp3), plus `german/json/words.json` (ranked list: rank, form, count, base word) and `german/json/grammar.json` (grammar concepts and the entry that first introduces each).
- Decided: code lives in shared `tools/`; only small language-specific pieces (spelling modernization, name/foreign filters, config) live per language.
- Decided: every inflected form is its own entry (`bin`, `ist`, `war` separately), each with its own 10 sentences. An entry records its base word (e.g. `war` → `sein`, past tense) so the grammar commentary can link forms.
- Entry contents: rank, form, base word, English translation, meanings[] → each meaning has an English gloss and ≤10 sentences {de, en, grammar_notes[]}. A grammar note appears the first time a concept is used across the whole sequence. Add `notes` fields where comments would help (JSON has no comments).
- Open: filename safety for forms containing umlauts/ß (keep them in filenames or transliterate?).
- Depends on: none (first ticket).

<!-- coga:blackboard -->

## Build step — what was built (2026-11-26, claude)

Files (uncommitted):
- `tools/schema.py` — dataclasses (Entry/Meaning/Sentence, WordList, Grammar, LanguageConfig), strict loader (unknown keys / wrong types fail), `dump_json`, `stem()` + `LanguagePaths`, `validate_language()`, JSON Schema export. Stdlib only (jsonschema isn't installed).
  CLI: `python -m tools.schema validate german`, `python -m tools.schema jsonschema [entry|words|grammar]`.
- `tools/__init__.py` (empty)
- `docs/format.md` — prose spec + layout.
- `german/language.toml` — code, names, PDF title, word_count=5000, source.
- Illustrative data: `german/json/words.json` (15 invented ranks), `entries/00001 und.json` (0 sentences), `entries/00014 war.json` (6 sentences, 2 grammar intros), `grammar.json`. Validates clean; a negative test (bad POS, unknown field, unknown grammar id, double intro, form mismatch) gave 5 errors, exit 1.

Decisions agreed with the human in-session:
- Filenames keep UTF-8 umlauts/ß; all forms + filenames must be NFC (validator enforces).
- Case: fold sentence-initial capitals, keep genuine noun capitals (rule owned by frequency-list ticket; schema stores form as given).
- base + pos (UPOS) + morph live per **meaning** (homographs like sein/die in one entry); entry also has a primary `base` mirrored in words.json (`null` allowed there).
- Grammar notes: sentences carry ids; text lives once in grammar.json with `first_entry`.

Decisions I made (judge these):
1. Sentence keys are fixed `text`/`en`, not `de`/`en` (language-neutral code).
2. ≤10 sentences is **per meaning** (ticket wording), not per entry — so `die` with 3 meanings could have 30.
3. `notes` optional on every object, never rendered.
4. `schema_version: 1` and `language` in every file.
5. Per-language config as `<lang>/language.toml` (TOML for comments); PDF filename = title + ".pdf".
6. Validator = structure + cross-file consistency only; known-words rule and semantic first-use left to write-sentence-checker.
7. Example data in `german/` is placeholder — keep it in the commit (overwritten later) or move to `docs/example/`?

## Usage

{"agent":"claude","cache_creation_input_tokens":96777,"cache_read_input_tokens":1071498,"cli":"claude","input_tokens":42,"model":"claude-opus-5-5","output_tokens":51312,"provider":"anthropic","schema":1,"session_id":"71a8cb7d-e4af-4e99-8ad3-68d702f31a5f","slug":"define-language-neutral-json-format-and-repo-layou","step":"build","title":"Define language-neutral JSON format and repo layout","ts":"2026-11-26T14:33:16.633866Z","usage_status":"ok"}

## Review Feedback (2026-11-26, ehsmeng)
* For all grammar entries (german/json/grammar.json) I want a few example sentences (please target 3) where the grammar rule is used.
* The word order in words.json does not need to be strictly by count. It may be necessary to rearrange them a little bit (say max 50 positions) to be able to create sencences. E.g first word perhaps should be "ich", next "bin", thus we can form incomplete sentence "ich bin". 
* As you correctly concluded, we want modern spelling and grammar.
* In the pdf, I also want an appendix with the 20 most common verbs, in all their forms and kasus. Perhaps the verbs should be defined in json too?

## Review — agreed instructions for finalize (2026-11-26, ehsmeng + claude in a `coga chat` session)

Worked out in discussion of the feedback above. Apply all of it. If a point is ambiguous, ask; don't guess.

**A. Grammar examples.** Each concept in `grammar.json` gets `examples: [{text, en, notes?}]` with 3 sentences as the target (fewer allowed when the vocabulary up to `first_entry` can't support 3). They may only use forms with order ≤ that concept's `first_entry`; the sentence checker enforces that, not this validator. Validator: structure only (list of Sentence-like objects, ≤3, non-empty `text`/`en`). Update `docs/format.md` and the example `grammar.json`.

**B. Learning order ≠ frequency order.**
- Rename `rank` → `order` everywhere (dataclasses, JSON, `stem()`, `LanguagePaths`, docs, `grammar.json` `first_entry` semantics = an order). `order` is the learning position and drives filenames: `entries/00001 ich.json`, `audio/00001 ich.mp3`.
- `words.json` items gain `frequency_rank` (int, position in the source frequency list); keep `count`.
- `language.toml` gains `max_reorder = 50`. Validator checks `|order − frequency_rank| ≤ max_reorder` and that `frequency_rank` values are unique.
- Docs: state that learning order must be final before content and audio are generated (reordering later means renaming files). The reorder itself is done by the word-list tickets, not here.

**C. Modern spelling and grammar.** Confirmed; no schema change. Owned by the frequency-list ticket.

**D. Verbs appendix.** Define `german/json/verbs.json`: the 20 most common verbs, ranked by the summed `count` of all their forms in `words.json` (grouped by `base`: `ist`+`bin`+`war`… → `sein`). Per verb: `base`, `translation`, `total_count`, and full conjugation tables for every tense/mood (present, simple past, perfect, pluperfect, future I/II, Konjunktiv I/II, imperative) by person/number, plus participles. Keep tense/person keys as data (e.g. a list of `{tense, forms: {person: form}}`) so other languages can use their own tenses without schema changes. Verb tables are exempt from the known-words rule. This ticket defines the format, validator support, and one illustrative verb (`sein`); filling it and rendering the appendix belong to the content and PDF tickets.

**E. Source.** Frequency source is now Tatoeba (CC BY 2.0 FR), not Der Zauberberg. Update `language.toml` `source` and the example `words.json` `source`. Licensing is already handled in `README.md` (code MIT, content CC BY 4.0, Tatoeba credited).

**F. Agent's 7 decisions.**
1. `text`/`en` keys: approved.
2. Changed: an entry may have at most **20 sentences total**, and each meaning at most 10. Aim to spread them evenly across meanings (4 meanings → 5 each; 3 → 6–7; 2 → 10 each; 1 → 10), fewer when the known vocabulary doesn't permit. So some entries are longer than others. Validator enforces ≤10 per meaning and ≤20 per entry; the even spread is guidance for content generation (write it into `docs/format.md`).
3. Optional `notes`, never rendered: approved.
4. `schema_version` + `language` in every file: approved (applies to `verbs.json` too).
5. `<lang>/language.toml`: approved; add `max_reorder = 50`.
6. Validator = structure + cross-file only: approved, extended with B, A's structure, D, and the limits in F2. The `write-sentence-checker` ticket has been updated with this division of labor.
7. Move the illustrative data (`words.json`, entries, `grammar.json`, the new `verbs.json` example) to `docs/example/german/json/…` so `german/` holds no fake data. Make the validator runnable against it (e.g. `python -m tools.schema validate docs/example/german`), and keep the negative test.

Then re-run the validator (positive + negative), record what changed here, commit, and `coga mark done`.

## Finalize — what changed (2026-11-26, claude)

All of A–F applied:
- **A** `GrammarConcept.examples: [Example{text,en,notes?}]`, validator caps at 3 + non-empty. Example grammar.json has 1–3 examples per concept (fewer where vocab up to `first_entry` can't support 3, with a `notes` saying so).
- **B** `rank` → `order` everywhere (`stem(order, form)`, `ORDER_WIDTH`, `LanguagePaths.entry/audio(order, …)`, `first_entry` = an order). `WordListItem` gains `frequency_rank`. `LanguageConfig.max_reorder` (required). Validator: orders contiguous, `frequency_rank` unique and ≥1, `|order − frequency_rank| ≤ max_reorder`. Docs say order must be final before content/audio.
- **C** docs state modern standard spelling; no schema change.
- **D** new `Verbs` / `Verb{base, translation, total_count, tenses[], participles{}, notes}` / `VerbTense{tense, label, forms{person: form}}` at `json/verbs.json`. Added `dict[str,str]` support to the strict loader and JSON Schema export. Validator: unique verbs, sorted by total_count desc, unique tense ids, non-empty NFC forms, base appears in words.json. It does NOT recompute total_count (homographs like possessive `sein` make a pure base-sum wrong; docs say count only VERB/AUX forms). Added `label` per tense (PDF table heading) — not in the spec, my call. Example: `sein`, 9 tenses + participles.
- **E** source = Tatoeba in `german/language.toml` and example words.json.
- **F2** ≤10/meaning and ≤20/entry enforced; even-spread guidance in docs/format.md. **F7** example moved to `docs/example/german/` (own copy of language.toml); `german/` holds only `language.toml`. Example reordered: `00001 ich` (0 sentences), `00002 bin` ("Ich bin."), `00015 war`.
- Checks: `validate docs/example/german` and `validate german` → 0 errors. Negative runs (scratchpad copies): 14 errors (reorder > 50, dup frequency_rank, 24 > 20/entry, 12 > 10/meaning ×2, bad POS, bad filename, unknown field, unsorted verbs, dup tense, empty form, unknown verb base, no tenses) and 5 grammar errors (double intro, unknown related, 4 > 3 examples, empty en, unknown note id); exit 1 both.
