---
slug: review-german-word-list
title: Review German word list
status: done
autonomy: interactive
owner: ehsmeng
human: ehsmeng
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: review/word-list
  steps:
  - name: apply-corrections
    skills: []
    assignee: agent
  - name: draft-order
    skills: []
    assignee: agent
  - name: sign-off
    skills: []
    assignee: human
  - name: finalize
    skills: []
    assignee: agent
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

## Pre-launch check (2026-11-27)

Read-only check of `german/json/words.json`, done in a chat session before launch. Nothing was changed.

- Top 300 forms look right. Function words and pronouns lead, then everyday nouns. Mild Tatoeba bias (Französisch 200, Sprache 230, lernen 224) is real usage, kept.
- No names in the top 300. No old ß spellings. Hyphenated forms (E-Mail 2956, U-Bahn 3229, T-Shirt 3835) and acronyms (USA 1630, KI 4413) are legitimate.
- Loanwords (Computer, Job, okay, cool, hey) kept as real German usage.
- Colloquial words and interjections kept: na, oh, ne, he, eh, ah, tu (imperative "tu das").

### Human decisions

1. Drop `de` (3263, French/name fragment), `Dr` (2902), `ca` (3933), `km` (2566) as junk and abbreviations. Add them to the exclusion list and rebuild. Forms 5,001+ move up to keep 5,000.
2. Learning order: full traceability. Keep reorders in a small, reviewable reorder list under `german/`, applied by `tools/frequency.py`, with the ±50 limit checked by the validator. Do not hand-edit words.json.

### Draft learning-order idea (not yet applied)

Opening: ich · bin(49) · du · ist · er · sie · es · das · nicht · ein · eine · der · die · und · hier(60) · ja · nein …
Gives "Ich bin hier.", "Das ist ein …", "Er ist nicht hier." early. Limit: bist(80) can come no earlier than position 30.
Scope: reorder about the first 150 forms. Leave the rest in frequency order.

## apply-corrections (2026-11-27) — done, not committed

- Added to `german/names.txt`: `de foreign`, `Dr other`, `ca other`, `km other`.
- Pipeline fix (agreed with human): the genitive-s auto-exclusion in `german/wordlist.py` now applies only to capitalized excluded forms. Otherwise excluding `de` would also have dropped `des` (rank 65). All earlier entries are capitalized, so no other change.
- Rebuilt with `python -m tools.frequency german` (cached export). Still 5,000 forms; `des` still at 65.
- Dropped: km (2566), Dr (2902), de (3263), ca (3933). Forms after each one moved up.
- Entered at the bottom: 4997 üblicherweise (72), 4998 amüsieren (71), 4999 aufnehmen (71), 5000 aufzuhalten (71).
- `python -m tools.schema validate german`: 0 errors.
- Changed files: german/names.txt, german/wordlist.py, german/json/words.json. Learning order not touched yet (next step: draft-order).

## draft-order (2026-11-27) — done, not committed

Human decision: in every language the words for "yes" and "no" may move earlier without limit. This is `reorder_exempt` in `language.toml` (German: `ja`, `nein`). The validator lets those forms be any distance earlier; moving them later is still limited to 50.

- Mechanism: `german/order.txt` lists forms in learning order from position 1 (`@N` jumps to position N), applied by `tools/frequency.py` (`read_order`/`apply_order`). Unlisted positions are filled in frequency order. The build fails on an unknown or duplicate form. The ±50 check stays in `tools/schema.py` only. Tested: an illegal pin (sprechen 173 → 37) is reported.
- 56 forms pinned (positions 1–56). After that, frequency order.
- Opening: ich · bin · du · ist · er · sie · es · das · nicht · hier · ja · nein · ein · eine · der · die · und · wir · sind · ihr · Sie · was · wie · so · auch · hat · habe · hast · haben · mein · meine · bist · sehr · aber · noch · gut · den · einen · zu · in · mit · keine · heute · man · kann · dass · sich · auf · mir · mich · dir · dich · wo · da · jetzt · wer
- Early sentences: Ich bin hier. Ja. / Nein. Nein, er ist nicht hier. Ist sie hier? Das ist ein/eine … Wir sind hier. Sind Sie hier? Was ist das? Wie ist das? Das ist auch so. Ich habe es. Hast du es? Das ist mein/meine … Bist du hier? Das ist sehr gut, aber … Ist er noch hier? Wo bist du? Wer ist das? Ich bin jetzt hier. Er ist heute da.
- At or near the limit: jetzt 103→55 (48), wer 104→56 (48), bist 80→32 (48), gut 84→36 (48), hier 60→10 (50, at the limit), wo 99→53 (46). Biggest push-back: zu 8→39 (31). ja 183→11 and nein 344→12 are exempt.
- Not sure about: (1) zu/in/mit come after the copula and possessives (frequent, but not needed for the first sentences). (2) Only 56 pinned, not ~150; pinning more adds little. (3) Ranks 183–344 each move back 1–2 places because ja/nein were pulled forward.
- Rebuilt and validated: german 0 errors, docs/example/german 0 errors.
- Changed: german/order.txt (new), german/language.toml, tools/frequency.py, tools/schema.py, docs/format.md, german/json/words.json.

## finalize (2026-11-27) — final decisions

- Sign-off: human approved the draft learning order as is. No corrections. The three "Not sure about" points are accepted as they stand: zu/in/mit after the copula and possessives; only 56 forms pinned; ranks 183–344 each move back 1–2 places.
- Final state: 5,000 forms. Exclusions de/Dr/ca/km. Genitive-s auto-exclusion applies only to capitalized forms. `german/order.txt` pins 56 forms. `reorder_exempt = [ja, nein]`.
- Rebuilt (`python -m tools.frequency german`): output matches the draft. `tools.schema validate`: german 0 errors, docs/example/german 0 errors.
- Untracked `tools/__pycache__/*.pyc` (`__pycache__/` was already in .gitignore).
- The order is now final. Filenames for content generation can be based on it.

### For the upstream frequency-list ticket / pipeline

- Add abbreviation/unit filtering to the pipeline (Dr, ca, km were caught by hand). For example, a stoplist of common abbreviations, or flag ≤3-letter lowercase forms that are not in a dictionary.
- Foreign-fragment detection (`de`): consider flagging forms whose Tatoeba sentences are mostly in another language, or that only appear next to capitalized name tokens.
- Genitive-s auto-exclusion is now limited to capitalized forms. Keep this rule when porting to other languages.
- `reorder_exempt` (yes/no words) is a per-language field in `language.toml`. New languages should set it.
- `order.txt` + validator ±50 check is the reorder mechanism to mirror for later languages.

## Usage

{"agent":"claude","cache_creation_input_tokens":62233,"cache_read_input_tokens":785686,"cli":"claude","input_tokens":34,"model":"claude-opus-5-5","output_tokens":6774,"provider":"anthropic","schema":1,"session_id":"dd930aa1-8853-43f1-a933-3de66e443c88","slug":"review-german-word-list","step":"apply-corrections","title":"Review German word list","ts":"2026-11-27T07:43:52.578663Z","usage_status":"ok"}

{"agent":"claude","cache_creation_input_tokens":72575,"cache_read_input_tokens":1865398,"cli":"claude","input_tokens":68,"model":"claude-opus-5-5","output_tokens":28051,"provider":"anthropic","schema":1,"session_id":"f50d5993-30d3-44b6-8c13-3e58c3b159bb","slug":"review-german-word-list","step":"draft-order","title":"Review German word list","ts":"2026-11-27T07:59:04.617040Z","usage_status":"ok"}
