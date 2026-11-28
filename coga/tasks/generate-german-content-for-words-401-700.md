---
slug: generate-german-content-for-words-401-700
title: Generate German content for words 401-700
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
secrets:
- TOWER_ANTHROPIC_KEY: env:TOWER_ANTHROPIC_KEY
script: null
step: 1 (build)
---

## Description

Generate content for words 401–700 using the approach approved in the pilot (`tools/generate.py`, Opus 5.5 default). Output: entry JSON files `00401 …json` through `00700 …json` plus the matching grammar.json updates, every batch passing the sentence checker (`python -m tools.checker german --from 401 --to 700` → 0 problems).

## Context

Project: German vocabulary course for English speakers, with word frequencies from Tatoeba's German sentences (tatoeba.org, CC BY 2.0 FR; counts only, sentences are newly written). Content is CC BY 4.0, code MIT. Target: 1,000 word forms in learning order (frequency order, adjusted by at most 50 positions so early sentences can be formed); a second 1,000 (words 1,001–2,000) may follow later, possibly as its own PDF. `words.json` keeps 5,000 ranked forms so the course can grow without rebuilding the list. Pilot: first 100 words. Layout: shared Python in `tools/`, data in `german/json/` (one JSON file per word), audio in `german/audio/`, PDF `german/first 1000 german words.pdf`. Later languages (e.g. `french/json/`) mirror the same layout.

- Part 2 of 3 of words 101–1,000 (split 2026-11-28 from generate-german-content-for-remaining-words).
- Batch in order (each batch depends on the vocabulary of all earlier ones). Run the checker per batch and fail loud on violations.
- Same per-entry rules as the pilot: ≤10 sentences per meaning, ≤20 per entry, and 3 `examples[]` per newly introduced grammar concept.
- The generator calls the Anthropic API with the ticket secret `TOWER_ANTHROPIC_KEY`, passed explicitly (never `ANTHROPIC_API_KEY`). Pilot cost on Opus 5.5: $4.47 per 100 words; expect more per 100 as the known vocabulary grows. The console prints a running cost, so report the total at the end.
- Resumability (decided 2026-11-28; a run may stop mid-step when credits or usage limits run out, then resume via `coga launch`):
  - Skip finished work: each batch first skips words whose entry JSON already exists and passes the checker, so a rerun only redoes missing or failing entries.
  - Note progress on the blackboard: after each batch passes the checker, record it (e.g. "batch 301–400 done, checker clean").
  - Commit after each batch, so an interruption loses at most one batch.
- Depends on: generate-german-content-for-words-101-400.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Plan (build, 2026-11-28)

- Same pipeline as 101-400: `tools/generate.py` unchanged (Opus 5.5, effort high), batches of 10 in order.
- Driver `cache/run-401-700.sh` (gitignored; copy of the 101-400 driver with range/ticket changed): per batch generate -> checker 1..hi -> line here -> commit `Content: german entries lo-hi`. Resume: rerun it (finished batches are skipped; optional arg = start lo).
- Projection: 101-400 averaged $0.57/10 words -> ~$17-20 for 401-700.

## Full run 401-700 (effort high)

- batch 401-410 done, checker clean, $0.46, 0 item(s) dropped
- batch 411-420 done, checker clean, $0.58, 0 item(s) dropped
- batch 421-430 done, checker clean, $0.65, 0 item(s) dropped
- batch 431-440 done, checker clean, $0.58, 0 item(s) dropped
- batch 441-450 done, checker clean, $0.67, 0 item(s) dropped
- batch 451-460 done, checker clean, $0.54, 0 item(s) dropped
- batch 461-470 done, checker clean, $0.45, 0 item(s) dropped
- batch 471-480 done, checker clean, $0.45, 0 item(s) dropped
- batch 481-490 done, checker clean, $0.62, 0 item(s) dropped
- batch 491-500 done, checker clean, $0.57, 0 item(s) dropped
- batch 501-510 done, checker clean, $0.74, 0 item(s) dropped
- batch 511-520 done, checker clean, $0.61, 0 item(s) dropped
- batch 521-530 done, checker clean, $0.57, 0 item(s) dropped
- batch 531-540 done, checker clean, $0.61, 0 item(s) dropped
- batch 541-550 done, checker clean, $0.42, 0 item(s) dropped
- batch 551-560 done, checker clean, $0.56, 0 item(s) dropped
- batch 561-570 done, checker clean, $0.48, 0 item(s) dropped
- batch 571-580 done, checker clean, $0.63, 0 item(s) dropped
- batch 581-590 done, checker clean, $0.57, 0 item(s) dropped
- batch 591-600 done, checker clean, $0.57, 0 item(s) dropped
- batch 601-610 done, checker clean, $0.45, 0 item(s) dropped
- batch 611-620 done, checker clean, $0.47, 0 item(s) dropped
- batch 621-630 done, checker clean, $0.59, 0 item(s) dropped
