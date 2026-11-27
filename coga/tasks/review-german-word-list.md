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
workflow: review/word-list
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
