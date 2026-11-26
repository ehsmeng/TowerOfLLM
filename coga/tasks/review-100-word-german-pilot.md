---
slug: review-100-word-german-pilot
title: Review 100-word German pilot
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

Human sign-off on the 100-word pilot content and PDF design. After this the generation approach and the layout are frozen for the full run. Output: approval or a correction list.

## Context

Project: German vocabulary course for English speakers, with word frequencies from Tatoeba's German sentences (tatoeba.org, CC BY 2.0 FR; counts only, sentences are newly written). Content is CC BY 4.0, code MIT. Target: 5,000 word forms in learning order (frequency order, adjusted by at most 50 positions so early sentences can be formed) (count is a parameter; 10k possible later). Pilot: first 100 words. Layout: shared Python in `tools/`, data in `german/json/` (one JSON file per word), audio in `german/audio/`, PDF `german/first 5k german words.pdf`. Later languages (e.g. `french/json/`) mirror the same layout.

- Review: translation accuracy, how natural the sentences are, grammar-note usefulness and placement, and the PDF look.
- Corrections to the approach should go back into the generation/PDF tickets before scaling.
- Assigned to the human (sign-off step).
- Depends on: build-pdf-generator-and-render-pilot.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
