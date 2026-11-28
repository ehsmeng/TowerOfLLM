---
slug: generate-german-verbs-json-for-the-verb-appendix
title: Generate German verbs.json for the verb appendix
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
secrets:
- TOWER_ANTHROPIC_KEY: env:TOWER_ANTHROPIC_KEY
script: null
step: 1 (build)
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
