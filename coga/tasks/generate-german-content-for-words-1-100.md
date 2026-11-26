---
slug: generate-german-content-for-words-1-100
title: Generate German content for words 1-100
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

Generate the full content for the first 100 words: English translation, meanings, up to 10 example sentences per meaning and at most 20 per entry (spread evenly across meanings) using only forms introduced so far, English translations, and grammar notes the first time a concept appears. This pilot shows whether the approach and quality hold up before scaling.

## Context

Project: German vocabulary course for English speakers, with word frequencies from Tatoeba's German sentences (tatoeba.org, CC BY 2.0 FR; counts only, sentences are newly written). Content is CC BY 4.0, code MIT. Target: 5,000 word forms in learning order (frequency order, adjusted by at most 50 positions so early sentences can be formed) (count is a parameter; 10k possible later). Pilot: first 100 words. Layout: shared Python in `tools/`, data in `german/json/` (one JSON file per word), audio in `german/audio/`, PDF `german/first 5k german words.pdf`. Later languages (e.g. `french/json/`) mirror the same layout.

- Writes `german/json/entries/00001 …json` through `00100 …json` and updates `german/json/grammar.json`. All entries must pass the sentence checker.
- Each grammar concept introduced here also gets its `examples[]` in grammar.json (target 3, only forms with order ≤ its `first_entry`).
- Expected: the very first words in learning order have almost no prior vocabulary, so early entries will have fewer than 10 sentences. That is acceptable ("if the current body of words permits").
- Open, decide at the start: who generates the content. Coga agent sessions working batch by batch need no setup. A script calling an LLM API is cheaper and repeatable at 5k scale but needs an API key. The choice carries into the remaining-words ticket.
- Depends on: review-german-word-list, write-sentence-checker.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
