"""Tests for tools/checker.py.  Run: python -m unittest tools.test_checker"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.checker import Vocabulary, check_language, main, tokenize
from tools.frequency import load_language_module
from tools.schema import WordList, WordListItem

REPO = Path(__file__).resolve().parent.parent
EXAMPLE = REPO / "docs" / "example" / "german"


def vocab(*forms: str, names: set[str] = frozenset()) -> Vocabulary:
    words = [WordListItem(order=i, form=f, frequency_rank=i, count=1) for i, f in enumerate(forms, 1)]
    return Vocabulary(WordList(1, "de", "test", words), set(names))


class SplitClitics:  # stand-in for german/wordlist.py
    @staticmethod
    def split_clitics(tok: str) -> list[str]:
        head, *rest = tok.replace("’", "'").split("'")
        return [head] + ["es" for r in rest if r.lower() == "s"]


class Modernize:  # stand-in for german/wordlist.py
    @staticmethod
    def modernize(tok: str) -> str:
        return {"daß": "dass", "Daß": "Dass"}.get(tok, tok)


def bad(v: Vocabulary, text: str, upto: int, lang=None) -> list[str]:
    return [x.token for x in v.check(text, upto, "t", lang)]


class TokenRules(unittest.TestCase):
    V = vocab("ich", "bin", "sie", "Sie", "essen", "Essen", "auf", "im", "geht", "es", "drei")

    def test_sentence_start_folds(self):
        self.assertEqual(bad(self.V, "Ich bin.", 2), [])

    def test_capital_mid_sentence_is_exact(self):
        self.assertEqual(bad(self.V, "ich bin Essen.", 2), ["Essen"])   # noun is order 6
        self.assertEqual(bad(self.V, "ich bin Essen.", 6), [])
        self.assertEqual(bad(self.V, "Ich bin Ich.", 2), ["Ich"])        # no form "Ich"

    def test_capital_after_gap_is_ambiguous(self):
        self.assertEqual(bad(self.V, "Ich bin. Sie bin: Ich", 3), [])   # Sie -> sie(3)

    def test_sie_at_start_matches_either(self):
        self.assertEqual(bad(self.V, "Sie bin.", 3), [])
        self.assertEqual(bad(self.V, "ich bin Sie.", 3), ["Sie"])        # formal Sie is order 4

    def test_punctuation_and_digits(self):
        self.assertEqual(bad(self.V, "„Ich bin 3, 2026!“ – (ich)…", 2), [])

    def test_spelled_out_numbers_must_be_known(self):
        self.assertEqual(bad(self.V, "Ich bin drei.", 2), ["drei"])

    def test_contraction_is_its_own_form(self):
        self.assertEqual(bad(vocab("in", "dem", "ich", "bin"), "Ich bin im.", 4), ["im"])

    def test_separable_particle_is_plain_token(self):
        self.assertEqual(bad(self.V, "Ich bin auf.", 7), [])

    def test_clitics_split(self):
        self.assertEqual(bad(self.V, "Geht's?", 10, SplitClitics), [])
        self.assertEqual(bad(self.V, "Geht's?", 9, SplitClitics), ["es"])

    def test_dropped_apostrophe_part_is_flagged(self):
        self.assertEqual(bad(self.V, "Ich bin wie'n.", 10, SplitClitics), ["wie'n", "wie"])
        self.assertEqual(bad(self.V, "Ich bin hab'.", 10, SplitClitics), ["hab"])

    def test_old_spelling_is_modernized(self):
        self.assertEqual(bad(vocab("dass", "ich"), "Daß ich, daß ich.", 2, Modernize), [])
        self.assertEqual(bad(vocab("dass", "ich"), "Daß ich.", 2), ["Daß"])   # no hook

    def test_real_german_hook(self):
        lang = load_language_module(REPO / "german")
        v = vocab("ich", "weiß", "dass", "es", "geht", "Tom", names={"Tom"})
        self.assertEqual(bad(v, "Ich weiß, daß es Tom geht's.", 6, lang), [])

    def test_names_pass(self):
        v = vocab("ich", "bin", names={"Tom", "Berlin"})
        self.assertEqual(bad(v, "Ich bin Tom. Tom bin Berlin.", 2), [])

    def test_hyphen_compound_is_one_token(self):
        self.assertEqual([t.text for t in tokenize("Die E-Mail.")], ["Die", "E-Mail"])


class LanguageLevel(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / "german"
        shutil.copytree(EXAMPLE, self.root)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def edit(self, rel: str, fn) -> None:
        p = self.root / "json" / rel
        d = json.loads(p.read_text(encoding="utf-8"))
        fn(d)
        p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

    def test_example_is_clean(self):
        self.assertEqual(check_language(self.root), [])

    def test_entry_and_grammar_violations_and_range(self):
        # 'für' is order 16: too late for entry 15. 'Tom' has no names hook here.
        self.edit("entries/00015 war.json", lambda d: d["meanings"][0]["sentences"].append(
            {"text": "Das war für Tom.", "en": "That was for Tom."}))
        self.edit("grammar.json", lambda d: d["concepts"][0]["examples"].append(
            {"text": "Ich bin da.", "en": "I am there."}))          # 'da' is 14 > first_entry 2
        got = check_language(self.root)
        self.assertEqual(len(got), 3, got)
        self.assertIn("00015 war meanings[0].sentences[6]: 'für' not known until order 16 (limit 15)", got[0])
        self.assertIn("'Tom' not in word list", got[1])
        self.assertIn("grammar 'verb.sein.praesens' (first_entry 2) examples[1]: 'da'", got[2])
        self.assertEqual(len(check_language(self.root, 1, 2)), 1)     # only the grammar example
        self.assertEqual(check_language(self.root, 16), [])
        self.assertEqual(main([str(self.root), "--from", "16"]), 0)
        self.assertEqual(main([str(self.root)]), 1)

    def test_missing_entries_with_explicit_range(self):
        # example has entries 1, 2, 15 only
        self.assertEqual(check_language(self.root, 1, 2), [])
        got = check_language(self.root, 1, 4)
        self.assertEqual(len(got), 2, got)
        self.assertTrue(got[0].startswith("00003 ") and got[0].endswith("entry missing (range 1..4)"), got)
        self.assertEqual(check_language(self.root), [])                 # no --to: no gap check
        self.assertEqual(main([str(self.root), "--from", "14", "--to", "15"]), 1)

    def test_schema_errors_stop_the_check(self):
        self.edit("entries/00002 bin.json", lambda d: d.update(bogus=1))
        got = check_language(self.root)
        self.assertTrue(got and all(g.startswith("schema: ") for g in got), got)


if __name__ == "__main__":
    unittest.main()
