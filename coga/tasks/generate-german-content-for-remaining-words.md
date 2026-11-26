---
slug: generate-german-content-for-remaining-words
title: Generate German content for remaining words
status: draft
autonomy: interactive
owner: ehsmeng
human: ehsmeng
agent: claude
assignee: ehsmeng
contexts: []
skills: []
workflow: null
secrets: null
script: null
---

## Description

Generate content for words 101–5,000 in batches, using the approach approved in the pilot. Output: all entry JSON files plus grammar.json, every batch passing the sentence checker.

## Context

Project: German vocabulary course for English speakers, with word frequencies from Tatoeba's German sentences (tatoeba.org, CC BY 2.0 FR; counts only, sentences are newly written). Content is CC BY 4.0, code MIT. Target: 5,000 word forms in learning order (frequency order, adjusted by at most 50 positions so early sentences can be formed) (count is a parameter; 10k possible later). Pilot: first 100 words. Layout: shared Python in `tools/`, data in `german/json/` (one JSON file per word), audio in `german/audio/`, PDF `german/first 5k german words.pdf`. Later languages (e.g. `french/json/`) mirror the same layout.

- Batch in order (each batch depends on the vocabulary of all earlier ones). Run the checker per batch and fail loud on violations.
- Same per-entry rules as the pilot: ≤10 sentences per meaning, ≤20 per entry, and 3 `examples[]` per newly introduced grammar concept.
- Also fill `german/json/verbs.json` (format defined in the format ticket): the 20 most common verbs ranked by summed count of all their forms in words.json, with full conjugation tables. Exempt from the known-words rule.
- May be split into several tickets (e.g. per 500 words) if a single ticket is too large.
- Depends on: review-100-word-german-pilot.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
