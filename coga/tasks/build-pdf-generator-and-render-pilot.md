---
slug: build-pdf-generator-and-render-pilot
title: Build PDF generator and render pilot
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
step: 3 (finalize)
---

## Description

Build the PDF generator in `tools/` and render the 100-word pilot, so the page design can be reviewed on real content. Output: generator code plus a pilot PDF.

## Context

Project: German vocabulary course for English speakers, with word frequencies from Tatoeba's German sentences (tatoeba.org, CC BY 2.0 FR; counts only, sentences are newly written). Content is CC BY 4.0, code MIT. Target: 1,000 word forms in learning order (frequency order, adjusted by at most 50 positions so early sentences can be formed); a second 1,000 (words 1,001–2,000) may follow later, possibly as its own PDF. `words.json` keeps 5,000 ranked forms so the course can grow without rebuilding the list. Pilot: first 100 words. Layout: shared Python in `tools/`, data in `german/json/` (one JSON file per word), audio in `german/audio/`, PDF `german/first 1000 german words.pdf`. Later languages (e.g. `french/json/`) mirror the same layout.

- Layout (from the human): one word per page (more pages if needed). The header shows the learning-order number and the word, with the English translation near it, followed by the grammar commentary and all example sentences with their translations. Aim for a "magnificent" typographic result.
- Grammar commentary shows the concept's explanation plus its `examples[]` on first use.
- Appendix: the 20 most common verbs from `verbs.json`, with full conjugation tables for every tense.
- Front/back matter: CC BY 4.0 notice and credit to Tatoeba as the frequency source.
- Sentence and grammar-example `review` comments (reviewer concerns, see generate-german-content-for-words-1-100) are printed right after the sentence, in both the pilot and the final PDF. `notes` are never printed.
- Grammar-placement warnings from the pilot review (e.g. 74 werden: future note on the wrong sentence; 54 da: subordinate clause with no note) were deferred to this stage by the human (2026-11-28). Decide here how to handle them in the rendered PDF.
- Concept grain (human, 2026-11-28): `grammar.json` is a fine-grained superset (70 concepts in entries 1–100, e.g. separate `negation.noch_nicht`, `negation.nicht_mehr`, `verb.modal.plural_forms`). Each concept is already introduced exactly once. The PDF step may merge, group or skip concepts in post-processing so that each explanation appears once; the JSON is not regenerated for this.
- Generator must be language-neutral: language name, title and paths come from config.
- Open: PDF toolchain (e.g. Typst, LaTeX, WeasyPrint/HTML→PDF, ReportLab). Choose for typography quality and how well it scales to ~1,000+ pages per book.
- The generator takes a word range (e.g. 1–1,000, later 1,001–2,000) so a second 1,000 can be rendered as its own PDF. `german/language.toml` `word_count` (5000) sizes the word list, not the book; add a per-book range/title setting here.
- Depends on: generate-german-content-for-words-1-100.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Decisions (human, 2026-11-28)

- Toolchain: **Typst** (`typst` pip package in `.venv`, no system deps). Python writes the Typst markup and compiles it.
- Verb appendix: **render `docs/example/german/json/verbs.json`** (1 verb, marked illustrative) until a real `german/json/verbs.json` exists. Generating the real one is a separate ticket.
- Reviewer flags stored in `notes` (`REVIEW warning: …` at entry/meaning/concept level, 8 in the Opus data): **extract and print them as reviewer remarks**, in the same style as `review`. No JSON change.
- Type: **EB Garamond + Source Sans 3**, vendored (OFL) so the build is reproducible.

## Findings

- `german/json/verbs.json` doesn't exist yet.
- The ticket's "74 werden / 54 da" warnings come from the Sonnet run; the Opus data has different flags (18 `review`, 8 `REVIEW` in notes).

## Build result (2026-11-28) — ready for review

**Pilot PDF:** `german/first 1000 german words (pilot 1-100).pdf` (115 pages, 1.2 MB, compiles in <1 s).
Rebuild: `.venv/bin/python -m tools.pdf german --to 100`. Full book later: `python -m tools.pdf german` (fails loud until all 1,000 entries exist).

Files (nothing committed):
- `tools/pdf.py`: loads and checks the data, flattens it to `cache/pdf/<code>-<book>.json`, compiles with Typst. CLI `--book <id> --to N --out`.
- `tools/book.typ`: language-neutral Typst template (all names and titles come from the model).
- `tools/test_pdf.py`: 8 tests (review extraction, quotes, index sort, range/pilot, `notes` never in model, missing entries fail loud, compile). All 38 repo tests green.
- `tools/schema.py`: new `Book` dataclass; `LanguageConfig.title` replaced by `books: list[Book]` (`[[books]]` in TOML: id, title, subtitle, file, first, last). Validation checks ids are unique and 1 <= first <= last <= word_count.
- `german/language.toml`, `docs/example/german/language.toml`: `[[books]] id="1-1000"`. `docs/format.md` updated. `requirements.txt` + `typst>=0.15`.
- `fonts/`: EB Garamond (8 TTF) + Source Sans 3 (6 TTF) + OFL texts, ~7 MB.

Design: 155×235 mm, mirrored margins. Each word starts a new page:
header = big oxblood learning number + word (30 pt) + italic translation; rule; frequency rank and count; "form of X" when base ≠ form.
Then the grammar boxes (tinted, left accent rule, "GRAMMAR §n", title, explanation, examples, "See also" with §/word refs).
Then meanings (number, gloss, POS · morph), with sentences in two columns: target language | English in muted italic. A §n superscript marks the sentence that introduces a concept.
Reviewer remarks: ochre sans with a "REVIEWER" label and left rule, spanning both columns right after the sentence/example (also under the header, meaning or concept for `notes`-level flags).
Front matter: title page, colophon (CC BY 4.0, Tatoeba credit from config, model named, fonts, stats), "How to use this book".
Back matter: verb appendix, word index (3 columns, number = learning order, not page), grammar index. The PDF has bookmarks for every word.

Decisions (agent):
- Grammar §-numbering is per book, in introduction order; the index and cross-references use **word numbers**, not page numbers, so they stay valid when layout changes.
- Concept grain: **no merging yet.** All 70 printed as-is, each once on its first_entry page. Code hook is `build_model`'s `in_range`; merging rules can go there.
- Grammar placement: the generator now **checks structurally** (concept tagged on a sentence ≠ its first_entry, concept carried by no sentence, tagged before introduction) and warns. The Opus data has **0 structural problems**. Semantic problems (wrong explanation, unclear placement) appear only as printed reviewer remarks. The Sonnet-era 74 werden / 54 da issues are gone: both werden concepts are introduced at 68 wird, and 54 da has §36 "da sein" on "Ist Stefan da?".
- Straight quotes become typographic (‘ ’ “ ”) in Python on display strings only.
- Meanings with 0 sentences print "No sentences yet: they need words that come later in the course."

### Points for the human to judge
1. **Overall look**: trim size, typeface, colours (oxblood accent, ochre reviewer remarks). See e.g. p.23 (wie, two concept-level remarks), p.52 (mich, sentence remarks), p.56 (da), p.107 (verb table), p.108 (index).
2. **Reviewer remarks are loud** on some pages (wie §16: two remarks call the explanation confusing). Per the always-print rule that is intended; confirm the learner-facing wording, the "REVIEWER" label and the "How to use" explanation.
3. **Empty space**: most words take less than half a page (one word per page, as specified). Fine, or allow 2 short words per page later?
4. **German words inside English explanations** aren't set apart (e.g. "ich is the subject, mich is…"). Italicising them would need markup in grammar.json (e.g. `*mich*`) or a heuristic; the JSON currently has none. Worth a generator change for 101–1,000?
5. **Concept merging**: keep all 70 fine concepts, or name groups to merge (e.g. the three §33/§34/§64 "three words for…" boxes)?
6. **Colophon wording** names the model and says sentences were checked by program. OK to publish?
7. **Fonts in git** (~7 MB TTF), vs. downloading them at build time.
8. Verb appendix is illustrative (1 verb, sein, with a banner); real `verbs.json` needs its own ticket.

## Usage

{"agent":"claude","cache_creation_input_tokens":231618,"cache_read_input_tokens":9356265,"cli":"claude","input_tokens":198,"model":"claude-opus-5-5","output_tokens":122502,"provider":"anthropic","schema":1,"session_id":"d6ab91dd-2bea-4071-9f45-017f1736305a","slug":"build-pdf-generator-and-render-pilot","step":"build","title":"Build PDF generator and render pilot","ts":"2026-11-28T08:25:02.877635Z","usage_status":"ok"}



## Review (human):

### Points for the human to judge:
1. good
2. It is confusing that it says "REVIEWER". Keep it but call it "NOTE" instead.
3. No, one per page.
4. No.
5. Keep all fine concepts.
6. Yes
7. In git, if it is open source.
8. Ok. please create a verb ticket then. Note that i have verb feedback below.


### Varous remarks
- For example, word "die" (#16) one of the meaning cases has "No sentences yet: they need words that come later in the course.". Please add a sentence regardless of if we have the word or not and add a comment under that the word is from the future. 
- Verbs: on the verb presentation page (page 107) i would like the german words (ich, du, er/sie/es, wir, ihr, sie/Sie) written and translated to english.
- Verbs: I would love to see a minimal german sentence after each verb form. I am thinking one column layout (instead of like now with two), and a sentence to the right, with italic smaller font english translation under it.