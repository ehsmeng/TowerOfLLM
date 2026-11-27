---
slug: write-sentence-checker
title: Write sentence checker
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
step: 1 (build)
secrets: null
script: null
---

## Description

Write the validator in `tools/` that every content batch must pass, so the core rule ("sentences use only words shown so far") is enforced by code rather than trusted to the generator. Output: a checker that reports violations for a range of entries.

## Context

Project: German vocabulary course for English speakers, with word frequencies from Tatoeba's German sentences (tatoeba.org, CC BY 2.0 FR; counts only, sentences are newly written). Content is CC BY 4.0, code MIT. Target: 5,000 word forms in learning order (frequency order, adjusted by at most 50 positions so early sentences can be formed) (count is a parameter; 10k possible later). Pilot: first 100 words. Layout: shared Python in `tools/`, data in `german/json/` (one JSON file per word), audio in `german/audio/`, PDF `german/first 5k german words.pdf`. Later languages (e.g. `french/json/`) mirror the same layout.

- Checks: every token in a sentence for entry N is one of forms 1..N (case-insensitive where it makes sense; decide on punctuation and numbers); ≤10 sentences per meaning; every sentence has an English translation; entries conform to the schema; the first use of each grammar concept carries a grammar note, and grammar.json is consistent.
- **Division of labor (decided 2026-11-26 in the format ticket's review):** the format ticket's `python -m tools.schema validate <lang>` already checks structure and cross-file consistency: schema/types, NFC, filenames, `order` vs `words.json`, sentence-count limits (≤10 per meaning, ≤20 per entry), grammar ids exist / introduced exactly once at `first_entry`, `|order − frequency_rank| ≤ max_reorder`. This checker owns the *semantic* rules only: known-words (forms 1..N), semantic first use of grammar concepts, and the same known-words rule for each grammar concept's `examples[]` (only forms with order ≤ that concept's `first_entry`). Call the schema validator first rather than duplicating its checks. Verb conjugation tables (`verbs.json`, PDF appendix) are exempt from the known-words rule.
- Note: entries are now keyed by learning `order`, not frequency rank, and the frequency source is Tatoeba, not Der Zauberberg.
- Must report violations with entry, sentence and offending token, and exit non-zero (fail loud).
- Contractions (decided 2026-11-27): `im`, `zum`, `am`, `ins` etc. are their own forms. They count as known only once introduced as their own entry, not via their parts (consistent with counting word forms).
- Separable-verb particles (decided 2026-11-27): pure token match. `auf` in `ich stehe … auf` is known if `auf` was introduced earlier (e.g. as a preposition). The grammar note covers the separable meaning on first use.
- Numbers and punctuation (decided 2026-11-27): strip punctuation before checking; digit tokens (`3`, `2026`) always pass. Spelled-out numbers (`drei`) must be known words.
- Depends on: define-language-neutral-json-format-and-repo-layou.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
