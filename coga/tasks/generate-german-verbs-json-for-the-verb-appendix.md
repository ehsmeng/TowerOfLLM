---
slug: generate-german-verbs-json-for-the-verb-appendix
title: Generate German verbs.json for the verb appendix
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

Generate `german/json/verbs.json`: the 20 most common German verbs with full conjugation tables and one minimal example sentence per form, so the PDF appendix renders real data instead of the illustrative `docs/example/german/json/verbs.json`. Output: the data file, validated, plus a re-rendered pilot PDF.

## Context

Project: German vocabulary course for English speakers (see build-pdf-generator-and-render-pilot). Format spec: `docs/format.md` § Verbs; schema `tools/schema.py` (`Verbs`, `Verb`, `VerbTense`); renderer `tools/pdf.py` + `tools/book.typ` (appendix).

- Selection: rank verbs by `total_count` = summed `count` of all their forms in `german/json/words.json`, grouped by base. Count only forms whose entry has a VERB/AUX meaning with that base (possessive `sein` not counted). Entries exist only for 1–100 now, so decide how to find the base of forms without an entry (e.g. a lemma lookup, or the model) and record it in the file's `notes`.
- Tenses per verb: praesens, praeteritum, perfekt, plusquamperfekt, futur_i, futur_ii, konjunktiv_i, konjunktiv_ii, imperativ (du/ihr/Sie), plus participles; same shape as the illustrative `sein`.
- Top-level `persons` maps each person label to English (ich → I, du → you (informal, one person), er/sie/es → he / she / it, wir → we, ihr → you (informal, several), sie/Sie → they / you (formal), Sie → you (formal)). From human review 2026-11-28: the appendix must show the German pronouns with their English.
- Human review 2026-11-28: one **minimal German example sentence after each verb form**, with its English translation (the PDF prints it one column per row: person + English | form | sentence over a smaller italic translation). Stored per tense as `examples: {person: {text, en}}`. Exempt from the known-words rule, but should be short and use common words. Run a reviewer pass; its `review` comments are printed.
- Forms must be correct (perfekt auxiliary haben/sein, separable/irregular forms; modal verbs have no proper imperative; handle missing persons by omitting them).
- Likely generated with the Anthropic API like `tools/generate.py` (key `TOWER_ANTHROPIC_KEY`); a conjugation library could cross-check the forms.
- Depends on: build-pdf-generator-and-render-pilot.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
