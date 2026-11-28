---
slug: generate-german-verbs-json-for-the-verb-appendix
title: Generate German verbs.json for the verb appendix
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

Generate `german/json/verbs.json`: the 20 most common German verbs with full conjugation tables and one minimal example sentence per form, so the PDF appendix renders real data instead of the illustrative `docs/example/german/json/verbs.json`. Output: the data file, validated, plus a re-rendered pilot PDF.

## Context

Project: German vocabulary course for English speakers (see build-pdf-generator-and-render-pilot). Format spec: `docs/format.md` § Verbs; schema `tools/schema.py` (`Verbs`, `Verb`, `VerbTense`); renderer `tools/pdf.py` + `tools/book.typ` (appendix).

- Selection: rank verbs by `total_count` = summed `count` of all their forms in `german/json/words.json`, grouped by base. Count only forms whose entry has a VERB/AUX meaning with that base (possessive `sein` not counted). Entries exist only for 1–100 now, so decide how to find the base of forms without an entry (e.g. a lemma lookup, or the model) and record it in the file's `notes`.
- Tenses per verb: praesens, praeteritum, perfekt, plusquamperfekt, futur_i, futur_ii, konjunktiv_i, konjunktiv_ii, imperativ (du/ihr/Sie), plus participles; same shape as the illustrative `sein`.
- Top-level `persons` maps each person label to English (ich → I, du → you (informal, one person), er/sie/es → he / she / it, wir → we, ihr → you (informal, several), sie/Sie → they / you (formal), Sie → you (formal)). From human review 2026-11-28: the appendix must show the German pronouns with their English.
- Human review 2026-11-28: one **minimal German example sentence after each verb form**, with its English translation (the PDF prints it one column per row: person + English | form | sentence over a smaller italic translation). Stored per tense as `examples: {person: {text, en}}`. Exempt from the known-words rule, but should be short and use common words. Run a reviewer pass; its `review` comments are printed.
- Forms must be correct (perfekt auxiliary haben/sein, separable/irregular forms; modal verbs have no proper imperative; handle missing persons by omitting them).
- Likely generated with the Anthropic API like `tools/generate.py` (key `TOWER_ANTHROPIC_KEY`); a conjugation library could cross-check the forms.
- Validate: the file must load through `tools/schema.py` (`Verbs`) and the pilot PDF must re-render cleanly; put a few rendered appendix pages in front of the reviewer.
- Decision 2026-11-28 (shared counts): `base` is null throughout `words.json`, and `count` belongs to the whole form. When a form has both verb and non-verb meanings (e.g. `meine` = possessive "my" vs. `meinen`; possessive `sein`), **split** its count between them (model-estimated shares) and give the verb only its share. Record the shares in the data. The PDF must print a comment where counts were split, saying which forms and roughly what share went to the verb.
- Decision 2026-11-28 (tooling): build a **reusable** generator (e.g. `tools/verbs.py`, CLI like `tools/generate.py`) with tests, not a one-off run.
- Decision 2026-11-28 (edge cases): modal verbs and separable verbs get no special rule. Treat them like any other verb, and let sampling vary the example sentences (e.g. double infinitive vs. participle, a split-off prefix). The forms themselves must still be correct.
- Decision 2026-11-28 (dependencies): install `simplemma` to find the base of forms that have no entry, and check it against the entries' `meanings[].base` where they exist. Check conjugations against the kaikki.org German Wiktionary JSONL extract: download it once into a gitignored cache, never commit it. Mismatches go on the blackboard for the reviewer. Record both sources in the file's `notes`.
- Decision 2026-11-28 (outputs): commit `german/json/verbs.json`, `tools/verbs.py` + tests, **and** the re-rendered pilot PDF.
- Out of scope: verbs beyond the top 20, and any schema or appendix-layout change other than the split-count comment (raise any further need on the blackboard rather than doing it silently).
- Depends on: build-pdf-generator-and-render-pilot.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Evaluator review

**Review: generate-german-verbs-json-for-the-verb-appendix**

**Clarity.** An agent could start from this ticket cold. It names the output path, the schema classes, the tense ids, the person map, the shape of the examples and how to validate. I checked the inlined facts against the code and they hold. `VerbTense.examples` and `Example.review` exist, `pdf.py` prints `review` for verb rows, and the illustrative `sein` has all 9 tenses, participles and the same `persons` map. Three things are left open:
- **New code or not.** No tool generates verbs today, and `generate.py`'s reviewer only handles entries and concepts. The ticket doesn't say whether a reusable script (say `tools/verbs.py`, with tests) is part of the deliverable or whether a one-off run is fine. It should say.
- **Render command.** "Re-rendered pilot PDF" should give the command, presumably `python -m tools.pdf german --to 100`.
- **Committed outputs.** Say whether the PDF gets committed.

**Workflow.** `build/agent-then-review` fits: the agent builds the data, a human judges forms, examples and appendix pages, then the agent finalizes. `interactive` is the right autonomy for a selection rule that needs judgment.

**Contexts.** Leaving them out is fine, since the facts are inlined. Two things are missing:
- **No lemmatizer.** No conjugation or lemma library is installed (spacy, simplemma and mlconjug are all absent). "A conjugation library could cross-check" therefore means a new dependency, and the ticket should say whether that's allowed.
- **API spend.** If the model looks up bases for about 4,900 forms, the ticket should set a cost or model expectation.

**Scope.** It's on the edge. It bundles base lookup and ranking, generating 20 verbs × about 9 tenses × 6 persons (roughly 1,000 forms and example sentences), a reviewer pass, and possibly a new tool. That's doable as one ticket, but splitting off "rank the top 20" as a step that gets reviewed first would catch selection errors early.

**Assumptions to question before launch:**
- **`base` is empty in `words.json`.** It's null for all 5,000 words, so "grouped by base" can't use the word list at all, even for 1–100. Bases come only from the entries (`meanings[].base`) or from the new lookup.
- **Counting is per form, not per meaning.** `count` belongs to the form, so a form with any VERB/AUX meaning adds its whole count. The `sein` form therefore includes its possessive uses, which contradicts "possessive `sein` not counted" (that rule only drops forms like `seine` that have no verb meaning). Worse, the `meine` entry has a `meinen` VERB meaning, so the whole count of `meine`, mostly the possessive, goes to `meinen` and could push it into the top 20 wrongly. Decide whether to apportion counts or exclude forms that are mainly another part of speech.
- **AUX counting.** Modal and auxiliary uses (`wird`, `hat`) count toward `werden` and `haben`. That's probably intended, but say so.
- **Edge cases with no stated rule.** Modals' perfekt (double infinitive vs. participle) and separable verbs whose prefix splits off in examples both need a decision.

## Build (agent, 2026-11-28)

Decisions confirmed by human:
- A: relax validator base check (schema.py ~527): base must occur as a *form* in words.json or as an entry `meanings[].base` (words.json `base` is null everywhere, so the old check rejects every verb).
- B1: typed field `Verb.count_splits: [{form, count, verb_share}]`; pdf.py prints the split-count comment from it.
- C: kaikki English-Wiktionary German extract (kaikki.org-dictionary-German.jsonl, 1.1 GB) into gitignored cache/kaikki/.
- Plan: rank via entries + simplemma + kaikki paradigms, model estimates shares for ambiguous forms; one gen call + one review call per verb (Opus 5.5); cross-check forms vs kaikki.

### What was built (uncommitted)
- `tools/verbs.py` (CLI `python -m tools.verbs german [--rank-only] [--force --only a,b] [--reshare] [--reindex]`) + `tools/test_verbs.py` (13 offline tests; full suite 61+ OK).
- `german/json/verbs.json`: 20 verbs, 9 tenses each (modals: 8, no imperativ), participles, 1 example/form, `count_splits`, `persons`. `python -m tools.schema validate german` → 0 errors.
- Re-rendered pilot PDF (`python -m tools.pdf german --to 100`): 203 pages, 0 warnings; appendix pp. 111–~196. Sample pages: 112 (sein + split note), 128 (können Futur I), 129 (können Futur II with reviewer errors), 140 (gehen, no split).
- schema.py: `CountSplit` + `Verb.count_splits`; float support in loader/jsonschema; relaxed base check (A). pdf.py `split_note` + book.typ prints it under the verb heading. docs/format.md updated. requirements.txt: simplemma.
- Caches (gitignored): `cache/kaikki/` (1.1 GB extract + 33 MB verb index), `cache/verbs/` (shares.json, gen/, review/, api.jsonl, report.md). Total API cost ≈ $4.75 (Opus 5.5).

### Ranking (top 20)
sein 249176, haben 158903, werden 66917, können 51524, sagen 29487, wollen 25607, gehen 23881, machen 23755, müssen 22528, wissen 22149, kommen 19972, sehen 19709, geben 18910, tun 18375, sollen 16465, mögen 15763, lassen 11651, sprechen 11002, glauben 10805, denken 9906. Next: finden 8706, essen 8250, hören 8027, brauchen 7519, helfen 7170.
- Method: entries' VERB/AUX bases (1–100) else simplemma lemma *only if the form is in that verb's kaikki paradigm* (stops possessive seinen→sein) plus every kaikki verb paradigm containing the form. Ambiguous = >1 verb, or entry has non-verb meaning, or kaikki also lists the form as a non-verb word. Candidates = verbs whose upper bound ≥ 20th lower bound (27 candidates, 39 ambiguous forms → one share call). meinen and bitten drop out after shares.
- Splits recorded: sein (sein 45%, wart 90%), werden (ward 92%), können (gekonnt 93%), wollen (wollen 99%, gewollt 98%), wissen (weiß 93%), geben (gegeben 98%), lassen (lassen/lass 99%, gelassen 95%), sprechen (sprich 97%), denken (gedacht 99%). Shares that round to 100% are counted in full (tut).
- simplemma vs entries: 1 disagreement (meine: entry meinen, simplemma mein).
- kaikki form-of records (e.g. headword "wurde") are skipped when indexing; they produced fake verbs.

### Cross-check vs kaikki
0 mismatches on all 20 verbs (51–53 cells each). First run had 6 "mismatches" that were my checker's bugs (it forced imperatives onto modals and turned `tun Sie` into `tuen Sie`); fixed + tested, those 6 verbs regenerated. Nothing left for the reviewer from kaikki.

### Points for the human to judge
1. **Reviewer flags: 48**, printed in the PDF. Content is never changed by the reviewer. Notable *errors*: können Futur II examples (4× "gekonnt haben" mistranslated as "learned/mastered", p.129), gehen futur_i ihr ("heute früh" vs "tonight"). Want a repair pass that regenerates flagged examples (`--force --only können,gehen`), or leave flags visible?
2. **Konjunktiv I flags (~15)**: reviewer repeatedly notes Konj I forms identical to the indicative (wir/sie haben, gehen…) are replaced by Konj II in real speech. Forms are correct; this is pedagogy. Options: accept, or a per-tense note (would be a schema/layout change → out of scope here).
3. **Form column hyphenates** long compound forms ("werde gekonnt ha-ben", p.129). One-line fix in book.typ (`hyphenate: false` on the form cell) — layout change, not done; OK to include?
4. Appendix length ≈ 85 pages for 20 verbs (each tense block is unbreakable). Fine for a pilot?
5. Share estimates: sein form 45% verb (possessive 55%) — plausible for Tatoeba?

## Usage

{"agent":"claude","cache_creation_input_tokens":475675,"cache_read_input_tokens":10246243,"cli":"claude","input_tokens":220,"model":"claude-opus-5-5","output_tokens":154740,"provider":"anthropic","schema":1,"session_id":"a05ee74b-b212-4135-8a7a-b406f0a60659","slug":"generate-german-verbs-json-for-the-verb-appendix","step":"build","title":"Generate German verbs.json for the verb appendix","ts":"2026-11-28T12:54:15.957580Z","usage_status":"ok"}


## Review (human, 2026-11-28)

1. Yes please do a repair pass.
2. (a) Leave it: the Konjunktiv I forms stay as they are, with no per-tense note.
3. yes, please set hyphenate: false.
4. Fine
5. Nobody cares about the statistics. Accept the share estimates as they are, and **remove the split-count comment at the top of each verb page**. This overrides the ticket's 2026-11-28 shared-counts decision that the PDF must print it. Keep `count_splits` in the data. Only the printed note goes: `split_note` in pdf.py and the line in book.typ.

**Instructions for finalize (from the human, clarified in an orient session):**
- **No reviewer comments printed in the verb appendix.** They make it look bad. Instead of printing each `review` comment, *act on it*: fix the example or translation it points to, then remove the comment. This covers all 48 flags, not just können and gehen. If a flag doesn't point to a real error (for example the Konjunktiv I "people use Konj II" notes, see answer 2), drop it without changing the text. After the repair, the verb rows must print no `review` text at all. Either stop pdf.py from printing it for verbs, or make sure no `review` is left in verbs.json, whichever is cleaner. Mention anything you can't fix in the bump message or on the blackboard rather than printing it.
- Then apply hyphenate: false, re-run the schema validation and tests, re-render the pilot PDF (`python -m tools.pdf german --to 100`), check a few appendix pages, and commit verbs.json, tools/verbs.py and its tests, the schema/pdf/typ/docs changes, and the PDF.

