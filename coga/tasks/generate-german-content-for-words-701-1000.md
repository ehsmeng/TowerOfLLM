---
slug: generate-german-content-for-words-701-1000
title: Generate German content for words 701-1000
status: draft
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
secrets:
- TOWER_ANTHROPIC_KEY: env:TOWER_ANTHROPIC_KEY
script: null
step: 1 (build)
---

## Description

Generate content for words 701–1,000 using the approach approved in the pilot (`tools/generate.py`, Opus 5.5 default). Output: entry JSON files `00701 …json` through `01000 …json` plus the matching grammar.json updates, every batch passing the sentence checker (`python -m tools.checker german --from 701 --to 1000` → 0 problems).

## Context

Project: German vocabulary course for English speakers, with word frequencies from Tatoeba's German sentences (tatoeba.org, CC BY 2.0 FR; counts only, sentences are newly written). Content is CC BY 4.0, code MIT. Target: 1,000 word forms in learning order (frequency order, adjusted by at most 50 positions so early sentences can be formed); a second 1,000 (words 1,001–2,000) may follow later, possibly as its own PDF. `words.json` keeps 5,000 ranked forms so the course can grow without rebuilding the list. Pilot: first 100 words. Layout: shared Python in `tools/`, data in `german/json/` (one JSON file per word), audio in `german/audio/`, PDF `german/first 1000 german words.pdf`. Later languages (e.g. `french/json/`) mirror the same layout.

- Part 3 of 3 of words 101–1,000 (split 2026-11-28 from generate-german-content-for-remaining-words).
- Batch in order (each batch depends on the vocabulary of all earlier ones). Run the checker per batch and fail loud on violations.
- Same per-entry rules as the pilot: ≤10 sentences per meaning, ≤20 per entry, and 3 `examples[]` per newly introduced grammar concept.
- The generator calls the Anthropic API with the ticket secret `TOWER_ANTHROPIC_KEY`, passed explicitly (never `ANTHROPIC_API_KEY`). Pilot cost on Opus 5.5: $4.47 per 100 words; expect more per 100 as the known vocabulary grows. The console prints a running cost, so report the total at the end.
- Resumability (decided 2026-11-28; a run may stop mid-step when credits or usage limits run out, then resume via `coga launch`):
  - Skip finished work: each batch first skips words whose entry JSON already exists and passes the checker, so a rerun only redoes missing or failing entries.
  - Note progress on the blackboard: after each batch passes the checker, record it (e.g. "batch 301–400 done, checker clean").
  - Commit after each batch, so an interruption loses at most one batch.
- Last content ticket: finish with the whole range 1–1,000 passing the checker.
- Depends on: generate-german-content-for-words-401-700.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
