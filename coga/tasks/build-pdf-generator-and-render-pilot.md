---
slug: build-pdf-generator-and-render-pilot
title: Build PDF generator and render pilot
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

Build the PDF generator in `tools/` and render the 100-word pilot, so the page design can be reviewed on real content. Output: generator code plus a pilot PDF.

## Context

Project: German vocabulary course for English speakers, with word frequencies from Tatoeba's German sentences (tatoeba.org, CC BY 2.0 FR; counts only, sentences are newly written). Content is CC BY 4.0, code MIT. Target: 5,000 word forms in learning order (frequency order, adjusted by at most 50 positions so early sentences can be formed) (count is a parameter; 10k possible later). Pilot: first 100 words. Layout: shared Python in `tools/`, data in `german/json/` (one JSON file per word), audio in `german/audio/`, PDF `german/first 5k german words.pdf`. Later languages (e.g. `french/json/`) mirror the same layout.

- Layout (from the human): one word per page (more pages if needed). The header shows the learning-order number and the word, with the English translation near it, followed by the grammar commentary and all example sentences with their translations. Aim for a "magnificent" typographic result.
- Grammar commentary shows the concept's explanation plus its `examples[]` on first use.
- Appendix: the 20 most common verbs from `verbs.json`, with full conjugation tables for every tense.
- Front/back matter: CC BY 4.0 notice and credit to Tatoeba as the frequency source.
- Generator must be language-neutral: language name, title and paths come from config.
- Open: PDF toolchain (e.g. Typst, LaTeX, WeasyPrint/HTML→PDF, ReportLab). Choose for typography quality and how well it scales to 5k+ pages.
- Depends on: generate-german-content-for-words-1-100.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
