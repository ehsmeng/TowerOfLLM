---
slug: build-german-frequency-list-from-zauberberg
title: Build German frequency list from Zauberberg
status: done
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

## Build step — what was built (2026-11-26)

Not committed yet.

- `tools/frequency.py`: shared pipeline (download → dedupe → tokenize → case-fold → exclude → rank → `words.json`, then runs the validator). `python -m tools.frequency german [--refresh]`, about 35 s.
- `german/wordlist.py`: German hooks (`EXPORT_URL`, `modernize`, `split_clitics`, `is_excluded`).
- `german/names.txt`: hand-classified exclusions with a category per name.
- `german/json/words.json`: **top 5,000 forms** (human decision: top `word_count`, not every candidate). Passes `python -m tools.schema validate german`. `order = frequency_rank`, `base = null`.
- `.gitignore`: `/cache/` (raw export plus a `.meta.json` with the download date). `docs/format.md` layout updated.

Reproducibility: export downloaded 2026-11-26, sha256 `e16c57e695bfeccccb455c305d262c5cbe2aa74a5c1e1edb725d53cf907309ac`. Both are also in `words.json` `notes`. Gives 787,546 sentences, 6.1M tokens, 135k candidate forms; count at the cut-off is 72 (`wahrlich`).

### Decisions (with reasons)
- **Dedupe:** drop a sentence if its letters, lowercased, match an earlier sentence (by id). Removes 5,672 (0.7%). Tatoeba already rejects exact duplicates, so only punctuation/case variants remain, and those would double-count.
- **Tokens:** letter runs with internal `-` (`E-Mail`, `U-Bahn`) or apostrophe. Latin script only, at least 2 letters. Digits and punctuation never form tokens.
- **Clitics:** `geht's`/`gibt’s` become host + `es`. Other apostrophe tails are dropped.
- **Case:** a capital is *ambiguous* at sentence start, or after `. ! ? : ;`, a quote mark or a dash. Each ambiguous capitalised token is split between `Xyz`/`xyz` by their unambiguous (mid-sentence) ratio, and goes to lowercase if never seen mid-sentence. Counts are fractional, then rounded. Results: `Sie` 59,360 / `sie` 54,691, `Essen`/`essen`, `Morgen`/`morgen`, `Mal`/`mal` all separate. Capitals with no meaning (`Du/Dir/Euch…` in letter style, `Ich/Nein/Ja/Danke/Hallo/Ach`) are always folded.
- **Old spelling is NOT rare:** `daß` appeared 8.6k times vs `dass` 40k. Added an explicit ß→ss list (~150 forms) built from every ß-form whose ss-spelling also occurs, checked by hand. A rule can't decide this (`Fuß` stays, `Fluß`→`Fluss`; `Buße`≠`Busse`, `Maße`≠`Masse`). No old ß forms remain in the top 5,000.
- **Names:** a curated list. No German dictionary or NLP library is installed, and German nouns are capitalised, so case can't tell names from nouns. I screened every capitalised form in the top 5,800. Excluded: persons (Tom 107k, Maria 26k, Mary, Johannes, Sami, Ziri, Yanni, Skura…), cities (Boston, Tokio/Tokyo/Tōkyō, Paris, New+York…), brands and sites (Tatoeba, Facebook, Google, Toki+Pona). Genitive -s (`Toms`) is excluded automatically.
- **Countries kept** (Deutschland, Japan, Europa, USA…) as category `country`. *Default chosen while your answer was pending.* Flip it in `EXCLUDED_CATEGORIES`.
- **Ties:** alphabetical (casefold, then exact form). Not first occurrence, because export order changes daily.

### Points for the human to judge
1. Countries kept, cities dropped: OK?
2. `Sie`/`sie`: sentence-initial tokens are split by the *mid-sentence* ratio. Initial "Sie" is subject position, so formal/3rd-person may be skewed (Sie ranks 14, sie 15).
3. Borderline name calls: excluded `Mark` (name, not marrow) and `Jesus`; kept `Gott`, `Ernst`, `Weiß`, `Bach`, `Rose`, `Fischer`, `Koch`, `Bauer`, and Venus/Mars/Jupiter.
4. Cut-off at exactly 5,000 means review-german-word-list can't pull in a word ranked 5,001–5,050 (max_reorder 50) without re-running with a higher `word_count`. Fine, or emit a +50 margin?
5. Swiss/typo `ss` spellings (`weiss` 26, `gross` 17) are not mapped to ß. They sit far below the cut-off.
6. Names below rank ~5,800 are unscreened. They need screening if `word_count` goes to 10k.

## Review step — human decisions (2026-11-26)

1. Countries kept, cities dropped: **OK**.
2. `Sie`/`sie` split by mid-sentence ratio: **OK**.
3. Kept dual-use words (Gott, Koch, Bauer, Rose, Ernst, Bach, Weiß, Fischer) stay: they are common nouns as well as names. **Planets dropped**: Mars, Jupiter, Venus added to `german/names.txt` as `place`. Rebuilt: still 5,000 forms, validator 0 errors, last form `zweifeln` (72).
4. No +50 margin: **not needed**. There are enough words below 5,000 to reorder with.
5. Swiss/typo `ss` not mapped: **OK**.
6. **Condition for raising `word_count` to 10k:** first screen the capitalized forms below rank ~5,800 for names (extend `german/names.txt`).

Review done. Next: finalize (commit the build, then `coga mark done`).

## Usage

{"agent":"claude","cache_creation_input_tokens":222039,"cache_read_input_tokens":3196810,"cli":"claude","input_tokens":98,"model":"claude-opus-5-5","output_tokens":91172,"provider":"anthropic","schema":1,"session_id":"cceb7977-d3ba-4acd-b836-99b60215d8ec","slug":"build-german-frequency-list-from-zauberberg","step":"build","title":"Build German frequency list from Zauberberg","ts":"2026-11-26T17:46:29.930738Z","usage_status":"ok"}
