---
slug: build-german-frequency-list-from-zauberberg
title: Build German frequency list from Zauberberg
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
secrets: null
script: null
step: 1 (build)
---

## Description

Download Tatoeba's German sentences and build the ranked German word-form list that orders the whole course. Output: `german/json/words.json` with every candidate form ranked by count, in the shape `docs/format.md` defines, plus the code that reproduces it (shared logic in `tools/`, German-specific filters in `german/`).

## Context

Project: German vocabulary course for English speakers, with word frequencies from Tatoeba's German sentences (tatoeba.org, CC BY 2.0 FR; counts only, sentences are newly written). Content is CC BY 4.0, code MIT. Target: 5,000 word forms in learning order (frequency order, adjusted by at most 50 positions so early sentences can be formed) (count is a parameter; 10k possible later). Pilot: first 100 words. Layout: shared Python in `tools/`, data in `german/json/` (one JSON file per word), audio in `german/audio/`, PDF `german/first 5k german words.pdf`. Later languages (e.g. `french/json/`) mirror the same layout.

- Source (decided 2026-11-26): Tatoeba's German sentences, per-language export `https://downloads.tatoeba.org/exports/per_language/deu/deu_sentences.tsv.bz2`. Use only the word counts, never the sentences. Credit Tatoeba in `words.json` `source` (from `german/language.toml`), and later in the README and PDF.
- Reproducibility: the export changes daily. Record the download date and a checksum in `words.json` `notes` (or on the blackboard), and keep the raw download out of git (cache it under a gitignored path).
- Count word forms, not lemmas (decided). Fold case sensibly: sentence-initial capitals vs nouns (Tatoeba sentences are short, so sentence-initial words are a large share). Decide and document.
- Exclude proper names. Tatoeba is dominated by a few stock names (Tom, Maria, Mary, John…), which will land in the top 100 if they are not filtered. Also exclude numbers, punctuation and other junk tokens.
- Consider deduplicating identical sentences before counting. Decide and document.
- Modern spelling: Tatoeba is mostly post-1996, so old-spelling conversion (daß→dass) is only a safety net. Add it only if old forms show up in the list.
- Ranking: `frequency_rank` by descending count, ties broken deterministically (e.g. first occurrence in the export, or alphabetical; document which). In this ticket `order` = `frequency_rank`. Reordering for learning happens in review-german-word-list. `base` may stay `null`.
- Output every candidate form, not just the first 5,000, so the cut-off can move (`word_count` in `german/language.toml`). The file must pass the existing validator in `tools/schema.py`.
- Review scope for this ticket's review step: method (tokenizing, case folding, filters, ties, reproducibility). Judging the list itself and setting the learning order belongs to review-german-word-list.
- Depends on: define-language-neutral-json-format-and-repo-layou (done).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
