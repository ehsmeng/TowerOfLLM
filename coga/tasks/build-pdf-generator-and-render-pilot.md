---
slug: build-pdf-generator-and-render-pilot
title: Build PDF generator and render pilot
status: active
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

Build the PDF generator in `tools/` and render the 100-word pilot, so the page design can be reviewed on real content. Output: generator code plus a pilot PDF.

## Context

Project: German vocabulary course for English speakers, with word frequencies from Tatoeba's German sentences (tatoeba.org, CC BY 2.0 FR; counts only, sentences are newly written). Content is CC BY 4.0, code MIT. Target: 1,000 word forms in learning order (frequency order, adjusted by at most 50 positions so early sentences can be formed); a second 1,000 (words 1,001–2,000) may follow later, possibly as its own PDF. `words.json` keeps 5,000 ranked forms so the course can grow without rebuilding the list. Pilot: first 100 words. Layout: shared Python in `tools/`, data in `german/json/` (one JSON file per word), audio in `german/audio/`, PDF `german/first 1000 german words.pdf`. Later languages (e.g. `french/json/`) mirror the same layout.

- Layout (from the human): one word per page (more pages if needed). The header shows the learning-order number and the word, with the English translation near it, followed by the grammar commentary and all example sentences with their translations. Aim for a "magnificent" typographic result.
- Grammar commentary shows the concept's explanation plus its `examples[]` on first use.
- Appendix: the 20 most common verbs from `verbs.json`, with full conjugation tables for every tense.
- Front/back matter: CC BY 4.0 notice and credit to Tatoeba as the frequency source.
- Sentence and grammar-example `review` comments (reviewer concerns, see generate-german-content-for-words-1-100) are printed right after the sentence, in both the pilot and the final PDF. `notes` are never printed.
- Grammar-placement warnings from the pilot review (e.g. 74 werden: future note on the wrong sentence; 54 da: subordinate clause with no note) were deferred to this stage by the human (2026-11-28). Decide here how to handle them in the rendered PDF.
- Concept grain (human, 2026-11-28): `grammar.json` is a fine-grained superset (70 concepts in entries 1–100, e.g. separate `negation.noch_nicht`, `negation.nicht_mehr`, `verb.modal.plural_forms`). Each concept is already introduced exactly once. The PDF step may merge, group or skip concepts in post-processing so that each explanation appears once; the JSON is not regenerated for this.
- Generator must be language-neutral: language name, title and paths come from config.
- Open: PDF toolchain (e.g. Typst, LaTeX, WeasyPrint/HTML→PDF, ReportLab). Choose for typography quality and how well it scales to ~1,000+ pages per book.
- The generator takes a word range (e.g. 1–1,000, later 1,001–2,000) so a second 1,000 can be rendered as its own PDF. `german/language.toml` `word_count` (5000) sizes the word list, not the book; add a per-book range/title setting here.
- Depends on: generate-german-content-for-words-1-100.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
