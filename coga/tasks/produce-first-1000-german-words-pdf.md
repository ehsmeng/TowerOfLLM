---
slug: produce-first-1000-german-words-pdf
title: Produce first 1000 german words PDF
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

Render the final `german/first 1000 german words.pdf` from the full data set with the approved generator. Output: the finished PDF.

## Context

Project: German vocabulary course for English speakers, with word frequencies from Tatoeba's German sentences (tatoeba.org, CC BY 2.0 FR; counts only, sentences are newly written). Content is CC BY 4.0, code MIT. Target: 1,000 word forms in learning order (frequency order, adjusted by at most 50 positions so early sentences can be formed); a second 1,000 (words 1,001–2,000) may follow later, possibly as its own PDF. `words.json` keeps 5,000 ranked forms so the course can grow without rebuilding the list. Pilot: first 100 words. Layout: shared Python in `tools/`, data in `german/json/` (one JSON file per word), audio in `german/audio/`, PDF `german/first 1000 german words.pdf`. Later languages (e.g. `french/json/`) mirror the same layout.

- File name follows the 1,000 target (originally "first 10k german words.pdf", then "first 5k german words.pdf"; renamed 2026-11-28 when the target dropped to 1,000).
- Check build time and file size at ~1,000+ pages.
- Depends on: generate-german-content-for-remaining-words.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
