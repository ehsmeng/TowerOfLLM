---
slug: define-language-neutral-json-format-and-repo-layou
title: Define language-neutral JSON format and repo layout
status: in_progress
autonomy: interactive
owner: ehsmeng
human: ehsmeng
agent: claude
assignee: ehsmeng
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
step: 2 (review)
---

## Description

Define the JSON data format and repo layout every language will share, so `german/` is built once and `french/` etc. can mirror it. Output: a short spec plus a schema (JSON Schema or Python dataclasses in `tools/`) that later tickets write to and validate against.

## Context

Project: German vocabulary course for English speakers, built from *Der Zauberberg* (Thomas Mann, vol. 1, Project Gutenberg #65661). Target: 5,000 word forms in frequency order (count is a parameter; 10k possible later). Pilot: first 100 words. Layout: shared Python in `tools/`, data in `german/json/` (one JSON file per word), audio in `german/audio/`, PDF `german/first 5k german words.pdf`. Later languages (e.g. `french/json/`) mirror the same layout.

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
