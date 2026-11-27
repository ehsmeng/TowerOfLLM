---
slug: write-sentence-checker
title: Write sentence checker
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
step: 3 (finalize)
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

## Decisions (with human, 2026-11-27)

- **Case:** mid-sentence tokens must match a form exactly (`Essen` vs `essen`, `Sie` vs `sie` are distinct entries only where meaning differs; words.json already splits that way). In ambiguous position (sentence start, after `. ! ? : ;`, quote, dash; same rule as tools/frequency) the lowercased form also matches. Known edge: sentence-initial `Sie` passes once `sie` *or* `Sie` is known.
- **Names:** forms in `<lang>/names.txt` with category person/place pass anywhere. (brand/foreign/other do not; countries are already vocabulary.)
- **Semantic first use of grammar:** left out of the checker (not mechanically checkable without extra data). Grammar ordering is the content-generation / review tickets' job.
- Known-words rule also applies to grammar `examples[]` (forms <= first_entry). verbs.json exempt.

## Built (step 1, not committed)

- `tools/checker.py`: `python -m tools.checker <lang> [--from N] [--to M]`. Runs `tools.schema.validate_language` first; any schema error → printed with `schema:` prefix, nothing else checked, exit 1. Then the known-words rule for entry sentences (orders in range) and grammar `examples[]` (concepts whose `first_entry` is in range). One line per violation, exit 1 if any.
- `tools/test_checker.py`: 15 unittest cases (`python -m unittest tools.test_checker`), all passing. Covers case folding, gaps, Sie/sie, punctuation/digits, spelled numbers, contractions, particles, clitics, old spelling, names, hyphen compounds, range filter, schema-first.
- Both `docs/example/german` and `german` (no entries yet) currently check clean.
- Reuses `TOKEN_RE` / `AMBIGUOUS_GAP_RE` / `load_language_module` from tools/frequency.py so a checked token = a counted token. Names come from the language module's `NAMES` dict (german/wordlist.py, from names.txt); optional hook, languages without it allow no names.

Worked example (example data + 2 injected sentences):
```
00015 war meanings[0].sentences[6]: 'für' not known until order 16 (limit 15) -- 'Das war für Tom.'
00015 war meanings[0].sentences[6]: 'Tom' not in word list -- 'Das war für Tom.'
grammar 'verb.sein.praesens' (first_entry 2) examples[1]: 'da' not known until order 14 (limit 2) -- 'Ich bin da.'
german: 3 problem(s) in entries 1..end
```
(`Tom` fails there only because docs/example has no wordlist.py; with real german/ hook Tom/Maria/Berlin pass.)

### For the human to judge
1. **Spelling not modernized**: `daß` is reported as unknown rather than auto-mapped. Intended (new content must be modern).
2. **Clitics**: `geht's` → `geht` + `es`; other apostrophe tails (`'n`, `hab'`) are dropped silently, as in the frequency count. Strict alternative: flag them.
3. **Single-letter / non-Latin tokens** are checked (frequency build ignored them), so `z. B.` or `a` would be flagged unless known. Stricter than the counter, by design.
4. **Schema-first is all-or-nothing**: a schema error anywhere in the language blocks checking the requested range. Fail loud, but a broken entry 300 blocks checking 1..100.
5. Names allowed = categories person + place only (not brand/foreign/other).
6. No check that every entry in the range exists — a missing entry is silently not checked (schema only checks entries that are present).

## Review (step 2, human, 2026-11-27)

Code looked OK. Decisions on the six points, already implemented in the orient session (18 tests pass, both data dirs check clean):
1. **Modernize old spelling**: tokens now go through the language hook `modernize` (german/wordlist.py: `daß→dass` etc., plus its FOLD_LOWER for letter-style `Du`/`Dir` and capitalized `Ich`/`Ja` …), same as the frequency count. No hook → no mapping.
2. **Flag dropped apostrophe parts**: if `split_clitics` returns fewer parts than the token has apostrophe pieces (`wie'n`), report "drops an apostrophe part (write it out)". Trailing `hab'` is caught already (`hab` is not a form).
3–5. Kept as built.
6. **Missing entries**: with an explicit `--to`, every order in lo..hi without an entry file is reported as `NNNNN form: entry missing (range lo..hi)`. Without `--to`, no gap check (so the empty `german/` still checks clean).

Left for finalize: commit `tools/checker.py` + `tools/test_checker.py`.

## Usage

{"agent":"claude","cache_creation_input_tokens":119124,"cache_read_input_tokens":2716697,"cli":"claude","input_tokens":94,"model":"claude-opus-5-5","output_tokens":41679,"provider":"anthropic","schema":1,"session_id":"9dd6d391-6871-4206-9322-8353bae3485e","slug":"write-sentence-checker","step":"build","title":"Write sentence checker","ts":"2026-11-27T10:17:18.145716Z","usage_status":"ok"}
