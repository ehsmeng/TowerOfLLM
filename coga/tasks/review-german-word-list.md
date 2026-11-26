---
slug: review-german-word-list
title: Review German word list
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

Human sign-off on the ranked word list before any content is generated, because every later step inherits the order and the filters. Output: approval or a list of corrections fed back to the frequency-list ticket.

## Context

Project: German vocabulary course for English speakers, with word frequencies from Tatoeba's German sentences (tatoeba.org, CC BY 2.0 FR; counts only, sentences are newly written). Content is CC BY 4.0, code MIT. Target: 5,000 word forms in learning order (frequency order, adjusted by at most 50 positions so early sentences can be formed) (count is a parameter; 10k possible later). Pilot: first 100 words. Layout: shared Python in `tools/`, data in `german/json/` (one JSON file per word), audio in `german/audio/`, PDF `german/first 5k german words.pdf`. Later languages (e.g. `french/json/`) mirror the same layout.

- Check: the top few hundred forms look right; names and junk tokens are gone; spelling is modern; case folding and tie-breaking make sense.
- Set the learning order here: reorder forms (at most `max_reorder` = 50 positions from `frequency_rank`) so early entries can form sentences (e.g. `ich` then `bin`). The order must be final before content is generated, since it sets the filenames.
- Target length is already decided at 5,000. No need to revisit unless the list shows a problem.
- Assigned to the human (sign-off step).
- Depends on: build-german-frequency-list-from-zauberberg.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
