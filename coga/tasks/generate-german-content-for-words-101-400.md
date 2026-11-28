---
slug: generate-german-content-for-words-101-400
title: Generate German content for words 101-400
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
step: 3 (finalize)
---

## Description

Generate content for words 101–400 using the approach approved in the pilot (`tools/generate.py`, Opus 5.5 default). Output: entry JSON files `00101 …json` through `00400 …json` plus the matching grammar.json updates, every batch passing the sentence checker (`python -m tools.checker german --from 101 --to 400` → 0 problems).

## Context

Project: German vocabulary course for English speakers, with word frequencies from Tatoeba's German sentences (tatoeba.org, CC BY 2.0 FR; counts only, sentences are newly written). Content is CC BY 4.0, code MIT. Target: 1,000 word forms in learning order (frequency order, adjusted by at most 50 positions so early sentences can be formed); a second 1,000 (words 1,001–2,000) may follow later, possibly as its own PDF. `words.json` keeps 5,000 ranked forms so the course can grow without rebuilding the list. Pilot: first 100 words. Layout: shared Python in `tools/`, data in `german/json/` (one JSON file per word), audio in `german/audio/`, PDF `german/first 1000 german words.pdf`. Later languages (e.g. `french/json/`) mirror the same layout.

- Part 1 of 3 of words 101–1,000 (split 2026-11-28 from generate-german-content-for-remaining-words).
- Batch in order (each batch depends on the vocabulary of all earlier ones). Run the checker per batch and fail loud on violations.
- Same per-entry rules as the pilot: ≤10 sentences per meaning, ≤20 per entry, and 3 `examples[]` per newly introduced grammar concept.
- The generator calls the Anthropic API with the ticket secret `TOWER_ANTHROPIC_KEY`, passed explicitly (never `ANTHROPIC_API_KEY`). Pilot cost on Opus 5.5: $4.47 per 100 words; expect more per 100 as the known vocabulary grows. The console prints a running cost, so report the total at the end.
- Resumability (decided 2026-11-28; a run may stop mid-step when credits or usage limits run out, then resume via `coga launch`):
  - Skip finished work: each batch first skips words whose entry JSON already exists and passes the checker, so a rerun only redoes missing or failing entries.
  - Note progress on the blackboard: after each batch passes the checker, record it (e.g. "batch 301–400 done, checker clean").
  - Commit after each batch, so an interruption loses at most one batch.
- One-time before the first batch (deferred from the pilot): the cost savings in `tools/generate.py` (per-entry retries, compact output, precomputed per-entry vocab, effort=medium A/B; est. 40–50%). Get the human's OK on the A/B result before the full run.
- Depends on: generate-german-content-for-words-1-100 (done; pilot reviewed and approved).

<!-- coga:blackboard -->

## Cost analysis of pilot (Opus, 1-100, $4.47 + ahead backfill $0.83)

- Output tokens = 85% of cost (190k out x $20/M). Per gen batch ~14k out, of which the JSON is only ~5k tokens -> **~2/3 of output is adaptive thinking**.
- Split: first-attempt gen $3.15, retries $0.54 (2 batches, full batch re-emitted), review $0.79. Input is minor (<$0.7).
- JSON padding (null notes/morph, empty grammar_notes): ~80-100 nulls + ~80 empty lists per batch -> ~5% of output at most.
- Inline ahead pass: system prompt carries all 5,000 forms (~39k tok, cached) -> ~$0.05/batch.
- Projection 101-400 unchanged: ~$6/100 rising -> ~$18-20.

## Plan (human OK 2026-11-28)

"Precomputed per-entry vocab" (human): Python computes allowed forms per entry; no tokens spent on it.

## Built (tools/generate.py, uncommitted; 71 tests green)

- Prompt: KNOWN FORMS (orders < first target, plain list, no orders) + per target line the extra forms allowed there. Review prompt uses the plain list too.
- Compact output: optional Gen* fields have defaults (schema `required` drops them); prompt says omit empty fields.
- Per-entry retries: `Problems.bad_orders`; `split_batch` keeps passing entries + concepts introduced only in them; retry asks only for failing orders (kept ones as context, kept concepts as "already introduced"); `merge_retry` merges; full batch re-checked. Wrong entries on attempt 1 -> full retry.
- Resume per entry: `entry_ok` (schema + known-words); batch regenerates only missing/failing orders; grammar write replaces only concepts with first_entry in the regenerated set. Pilot 1-100 all pass entry_ok.
- `--effort` default still `high` pending A/B.

## A/B effort (101-110, scratch copies cache/ab/eff-{medium,high}/german)

- Both checker-clean, 0 dropped. Side-by-side: `cache/ab/eff-compare.txt`.
- Output tokens (the cost driver): medium 14.4k (gen 10.8k + 1-entry retry 0.8k, review 2.1k) vs high 18.7k (gen 15.0k, review 3.1k) -> medium -23%. Raw $ ($0.65 vs $0.48) misleading: concurrent runs, medium paid the 39k ahead-prompt cache write.
- Per-entry retry worked live: medium retried only [106], 770 out tokens (vs ~14k for a full-batch retry in the pilot).
- Quality: high richer - 110 vs 99 sentences, 9 vs 7 concepts (adds case.dative.indirect_object, noun.gender; medium folded gender into capitalization), real sentences for werde=become (medium: ahead only), cleaner meaning split for gehen. Medium had one confusing sentence (105 "Nicht dieses, das hier.").
- Agent recommendation: keep effort=high; medium saves ~$3 over 300 words.
- **Human 2026-11-28: effort=high; commit per batch (ticket rule overrides build step's "don't commit"); fix stale notes** (done: SYSTEM prompt forbids "no sentences" notes).
- Projection 101-400 at high: ~$0.45-0.6/batch -> ~$15-18.
- Nits seen: stale entry notes "meaning has no sentences" after ahead pass fills it (reviewer flags them); concurrent runs share one log filename (seconds timestamp).

## Full run 101-400 (effort high)

Driver: one `tools.generate` process per batch, then checker 1..hi, then a commit and a line here. Resume: rerun the driver; finished batches are skipped.

- batch 101-110 done, checker clean, $0.71, 0 item(s) dropped
- batch 111-120 done, checker clean, $0.64, 0 item(s) dropped
- batch 121-130 done, checker clean, $0.73, 0 item(s) dropped
- batch 131-140 done, checker clean, $0.56, 0 item(s) dropped
- batch 141-150 done, checker clean, $0.70, 0 item(s) dropped
- batch 151-160 done, checker clean, $0.74, 0 item(s) dropped
- batch 161-170 done, checker clean, $0.54, 0 item(s) dropped
- batch 171-180 done, checker clean, $0.67, 0 item(s) dropped
- batch 181-190 done, checker clean, $0.43, 0 item(s) dropped
- batch 191-200 done, checker clean, $0.57, 0 item(s) dropped
- batch 201-210 done, checker clean, $0.57, 0 item(s) dropped
- batch 211-220 done, checker clean, $0.55, 0 item(s) dropped
- batch 221-230 done, checker clean, $0.62, 0 item(s) dropped
- batch 231-240 done, checker clean, $0.48, 0 item(s) dropped
- batch 241-250 done, checker clean, $0.55, 0 item(s) dropped
- batch 251-260 done, checker clean, $0.59, 0 item(s) dropped
- batch 261-270 done, checker clean, $0.47, 0 item(s) dropped
- batch 271-280 done, checker clean, $0.46, 0 item(s) dropped
- batch 281-290 done, checker clean, $0.40, 0 item(s) dropped
- batch 291-300 done, checker clean, $0.44, 0 item(s) dropped
- batch 301-310 done, checker clean, $0.50, 0 item(s) dropped
- batch 311-320 done, checker clean, $0.67, 0 item(s) dropped
- batch 321-330 done, checker clean, $0.87, 0 item(s) dropped
- batch 331-340 done, checker clean, $0.59, 0 item(s) dropped
- batch 341-350 done, checker clean, $0.60, 0 item(s) dropped
- batch 351-360 done, checker clean, $0.53, 0 item(s) dropped
- batch 361-370 done, checker clean, $0.43, 0 item(s) dropped
- batch 371-380 done, checker clean, $0.47, 0 item(s) dropped
- batch 381-390 done, checker clean, $0.60, 0 item(s) dropped
- batch 391-400 done, checker clean, $0.56, 0 item(s) dropped

## Result (build step done 2026-11-28)

- **All 30 batches done, 0 dropped.** `python -m tools.checker german --from 101 --to 400` -> 0 problems (also 0 for 1..end).
- **Total cost $17.24** (Opus 5.5, effort high; $0.40-0.87/batch, avg $0.57/10 words). Logs: `cache/generate/run-<lo>-<hi>.out`, driver `cache/generate/run-101-400-driver.out`. Driver: `cache/run-101-400.sh` (gitignored).
- 300 entries, 3,123 sentences (9 ahead), 0 empty meanings. 194 new grammar concepts, 187 with 3 examples.
- Reviewer: 0 `REVIEW error` notes; 59 sentence `review` comments (printed in the PDF per the always-print decision) - mostly translation nuance, a few wrong-meaning placements (e.g. 136 "Habt ihr heute etwas vor?" under haben; 211 "Das gehört sich nicht." under belong).
- Commits: generator `e583224`, then one commit per batch (`Content: german entries lo-hi`).

## For the human to judge

1. Spot-read a few entries, e.g. `german/json/entries/00174 *.json`, `00238 *.json`, `00320 *.json`, `00372 *.json`.
2. The 59 sentence review comments: keep printing them as-is, or should the finalize step fix or drop the flagged sentences (one cheap targeted pass)?
3. 7 concepts have <3 examples (vocabulary too thin): noun.gender, adjective.attributive, case.genitive, preposition.auf.language (1), expression.haette_gern, pronoun.welche.some, article.body_parts. Accept?
4. Concept rate ~6.5 per 10 words (194 in 300). Is the grain OK, or too fine for the PDF?

## Review decision (human, 2026-11-28)

- Spot-read 174, 238, 320, 372. 174/320/372 good; 238 beim thin (only locative "by the", missing beim Essen / beim Arzt).
- **No fixes in this ticket.** The reviewer comments, thin entries, <3-example concepts and concept grain are all deferred to one review pass over all 1,000 words, after 401-700 and 701-1000 are done.
- Finalize: no content changes; just wrap up and `coga mark done`.
- Notes for the later review pass: some reviewer comments are wrong (e.g. 372 "zwei ganz andere Dinge" is idiomatic), so the pass must be allowed to reject a flag; the reviewer checks one sentence at a time and misses meanings that are absent altogether, so also check small contraction/preposition entries (beim, zum, im, am...) for missing core uses.

## Usage

{"agent":"claude","cache_creation_input_tokens":281232,"cache_read_input_tokens":16734650,"cli":"claude","input_tokens":398,"model":"claude-opus-5-5","output_tokens":99941,"provider":"anthropic","schema":1,"session_id":"1fa507c9-46e0-4210-827f-53324a0ac0f4","slug":"generate-german-content-for-words-101-400","step":"build","title":"Generate German content for words 101-400","ts":"2026-11-28T17:07:41.249634Z","usage_status":"ok"}
