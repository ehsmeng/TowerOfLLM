---
slug: define-language-neutral-json-format-and-repo-layou
title: Define language-neutral JSON format and repo layout
status: in_progress
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
step: 1 (build)
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

The blackboard is a notepad to be written to often as the human and agent works through a task.
