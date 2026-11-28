"""Offline tests for tools/generate.py (no API calls).  Run: python -m unittest tools.test_generate"""

from __future__ import annotations

import unittest

from tools.checker import Vocabulary
from tools.generate import (GenBatch, GenConcept, GenEntry, GenExample, GenMeaning,
                            GenSentence, Review, ReviewIssue, apply_review, check_batch,
                            drop_failing, to_concept, to_entry, uses_form)
from tools.schema import GrammarConcept, WordList, WordListItem

FORMS = ["ich", "bin", "du", "ist", "er"]
WORDS = WordList(1, "de", "t", [WordListItem(order=i, form=f, frequency_rank=i, count=1)
                                for i, f in enumerate(FORMS, 1)])
VOCAB = Vocabulary(WORDS, {"Tom"})


def s(text, notes=()):
    return GenSentence(text=text, en="x", grammar_notes=list(notes), notes=None)


def entry(order, form, *sentences):
    return GenEntry(order=order, form=form, base=form, translation="x", notes=None,
                    meanings=[GenMeaning(gloss="x", base=form, pos="PRON", morph=None,
                                         sentences=list(sentences))])


def concept(cid, first, *examples):
    return GenConcept(id=cid, title="t", explanation="e", first_entry=first, related=[],
                      examples=[GenExample(text=t, en="x") for t in examples])


def batch(*entries, concepts=()):
    return GenBatch(entries=list(entries), new_concepts=list(concepts))


class Check(unittest.TestCase):
    def check(self, b, existing=()):
        return check_batch(b, [4, 5], WORDS, VOCAB, list(existing), None, "de")

    def test_clean_batch(self):
        b = batch(entry(4, "ist", s("Tom ist hier.")),  # 'hier' unknown -> flagged
                  entry(5, "er", s("Er ist.")))
        p = self.check(b)
        self.assertEqual(p.bad_sentences, {(4, 0, 0)})
        ok = batch(entry(4, "ist", s("Tom ist.", ["v.sein"])), entry(5, "er", s("Er ist.")),
                   concepts=[concept("v.sein", 4, "Tom ist.")])
        self.assertFalse(self.check(ok))

    def test_known_words_limit_per_entry(self):
        p = self.check(batch(entry(4, "ist", s("Er ist.")), entry(5, "er", s("Er ist."))))
        self.assertEqual(p.bad_sentences, {(4, 0, 0)})  # 'er' is order 5

    def test_must_use_form(self):
        p = self.check(batch(entry(4, "ist", s("Ich bin.")), entry(5, "er", s("Er ist."))))
        self.assertEqual(p.bad_sentences, {(4, 0, 0)})

    def test_wrong_entries_is_fatal(self):
        p = self.check(batch(entry(4, "ist")))
        self.assertTrue(p.fatal)

    def test_grammar_rules(self):
        old = GrammarConcept(id="old", title="t", explanation="e", first_entry=2)
        b = batch(entry(4, "ist", s("Tom ist.", ["old"]), s("Du bist.", [])),
                  entry(5, "er", s("Er ist.", ["new"]), s("Ich bin er.", ["new"])),
                  concepts=[concept("new", 4, "Er ist.")])
        p = self.check(b, [old])
        self.assertIn((4, 0, 0), p.bad_sentences)       # re-introduces 'old'
        self.assertIn("new", p.bad_concepts)            # introduced twice
        self.assertIn(("new", 0), p.bad_examples)       # 'er' unknown at first_entry 4

    def test_drop_cleans_up(self):
        b = batch(entry(4, "ist", s("Tom ist hier.", ["c"]), s("Tom ist.")),
                  entry(5, "er", s("Er ist.")),
                  concepts=[concept("c", 4, "Tom ist.")])
        p = self.check(b)
        cleaned, dropped = drop_failing(b, p, [])
        self.assertFalse(self.check(cleaned))
        self.assertEqual(cleaned.new_concepts, [])      # lost its introducing sentence
        self.assertEqual(len(dropped), 2)


class PerEntryRetry(unittest.TestCase):
    def check(self, b):
        return check_batch(b, [4, 5], WORDS, VOCAB, [], None, "de")

    def test_bad_orders_and_split(self):
        from tools.generate import split_batch
        b = batch(entry(4, "ist", s("Tom ist.", ["c4"])),
                  entry(5, "er", s("Er ist hier.", ["c5"])),        # 'hier' unknown
                  concepts=[concept("c4", 4, "Tom ist."), concept("c5", 5, "Er ist.")])
        p = self.check(b)
        self.assertEqual(p.bad_orders, {5})
        kept_e, kept_c, bad_e, bad_c = split_batch(b, p)
        self.assertEqual([e.order for e in kept_e], [4])
        self.assertEqual([c.id for c in kept_c], ["c4"])
        self.assertEqual([c.id for c in bad_c], ["c5"])

    def test_bad_concept_example_fails_its_entry(self):
        b = batch(entry(4, "ist", s("Tom ist.", ["c"])), entry(5, "er", s("Er ist.")),
                  concepts=[concept("c", 4, "Er ist.")])               # 'er' unknown at 4
        self.assertEqual(self.check(b).bad_orders, {4})

    def test_merge(self):
        from tools.generate import merge_retry
        b = batch(entry(4, "ist", s("Tom ist.", ["c4"])), entry(5, "er", s("Er ist hier.")),
                  concepts=[concept("c4", 4, "Tom ist.")])
        sub = batch(entry(5, "er", s("Er ist.")), entry(4, "ist", s("ignored")))
        m = merge_retry(b, [b.new_concepts[0]], sub, {5})
        self.assertEqual(m.entries[0].meanings[0].sentences[0].text, "Tom ist.")
        self.assertEqual(m.entries[1].meanings[0].sentences[0].text, "Er ist.")
        self.assertFalse(self.check(m))
        # retry that leaves an entry out keeps the old (still failing) version
        m2 = merge_retry(b, [b.new_concepts[0]], batch(), {5})
        self.assertEqual(self.check(m2).bad_orders, {5})

    def test_prompt_precomputes_allowed_forms(self):
        from tools.generate import batch_prompt
        pr = batch_prompt(WORDS, [3, 5], [], [], [])
        self.assertIn("KNOWN FORMS (allowed in every entry below):\nich bin\n", pr)
        self.assertIn("3\tdu\tdu\n5\ter\tdu ist er", pr)

    def test_compact_schema(self):
        from anthropic.lib._parse._transform import transform_schema
        sch = transform_schema(GenSentence)
        self.assertEqual(sch["required"], ["text", "en"])


class Resume(unittest.TestCase):
    def test_entry_ok(self):
        from tools.generate import entry_ok
        self.assertTrue(entry_ok(to_entry(entry(4, "ist", s("Tom ist.")), "de"), VOCAB, None))
        self.assertFalse(entry_ok(to_entry(entry(4, "ist", s("Er ist.")), "de"), VOCAB, None))


class Misc(unittest.TestCase):
    def test_uses_form_case(self):
        self.assertTrue(uses_form("Ist er da?", "ist", None))
        self.assertFalse(uses_form("ich bin Ist.", "ist", None))
        self.assertTrue(uses_form("Sie ist da.", "Sie", None))

    def test_review_notes(self):
        e = to_entry(entry(4, "ist", s("Tom ist.")), "de")
        c = to_concept(concept("c", 4, "Tom ist."))
        rev = Review(issues=[
            ReviewIssue(order=4, meaning=0, sentence=0, concept_id=None, example=None,
                        severity="warning", issue="odd"),
            ReviewIssue(order=None, meaning=None, sentence=None, concept_id="c", example=0,
                        severity="error", issue="bad"),
            ReviewIssue(order=9, meaning=0, sentence=0, concept_id=None, example=None,
                        severity="error", issue="nowhere")])
        unplaced = apply_review([e], [c], rev)
        self.assertEqual(e.meanings[0].sentences[0].review, "odd")
        self.assertIsNone(e.meanings[0].sentences[0].notes)
        self.assertEqual(c.examples[0].review, "bad")
        self.assertEqual(len(unplaced), 1)


class People(unittest.TestCase):
    def test_batch_people_random_but_reproducible(self):
        from tools.generate import batch_people
        pool = [f"N{i}" for i in range(30)]
        a = batch_people("de", 1, pool)
        self.assertEqual(a, batch_people("de", 1, list(reversed(pool))))
        self.assertEqual(len(set(a)), 6)
        self.assertTrue(set(a) <= set(pool))
        self.assertNotEqual(a, batch_people("de", 11, pool))
        self.assertEqual(sorted(batch_people("de", 1, ["A", "B"])), ["A", "B"])


class Force(unittest.TestCase):
    def setUp(self):
        import shutil, tempfile
        from pathlib import Path
        from tools.schema import Grammar, LanguagePaths, dump_json
        self.tmp = Path(tempfile.mkdtemp())
        self.paths = LanguagePaths(self.tmp)
        for n, f in [(1, "ich"), (2, "bin"), (3, "du")]:
            dump_json(to_entry(entry(n, f), "de"), self.paths.entry(n, f))
        dump_json(Grammar(1, "de", [to_concept(concept("a", 1)), to_concept(concept("b", 2))]),
                  self.paths.grammar)
        self.addCleanup(shutil.rmtree, self.tmp)

    def test_clears_range(self):
        from tools.generate import clear_range, existing_entries
        from tools.schema import Grammar, load_json
        clear_range(self.paths, "de", 2, 3)
        self.assertEqual(sorted(existing_entries(self.paths)), [1])
        self.assertEqual([c.id for c in load_json(Grammar, self.paths.grammar).concepts], ["a"])

    def test_refuses_with_later_entries(self):
        from tools.generate import clear_range, existing_entries
        with self.assertRaises(SystemExit):
            clear_range(self.paths, "de", 1, 2)
        self.assertEqual(len(existing_entries(self.paths)), 3)   # nothing deleted



class Ahead(unittest.TestCase):
    """Ahead pass checks and application, plus the schema rules for `ahead`."""
    V = Vocabulary(WordList(1, "de", "t", [WordListItem(order=i, form=f, frequency_rank=i, count=1)
                                          for i, f in enumerate(["die", "ist", "hier", "Frau"], 1)]),
                   set())

    def entry(self):
        from tools.schema import Entry, Meaning
        return Entry(1, "de", 1, "die", "der", "the", [Meaning("the", "der", "DET")])

    def answer(self, *texts, order=1):
        from tools.generate import GenAhead, GenAheadItem, GenAheadSentence
        return GenAhead(items=[GenAheadItem(order=order, meaning=0, sentences=[
            GenAheadSentence(text=t, en="x") for t in texts])])

    def test_check_and_apply(self):
        from tools.generate import apply_ahead, check_ahead
        e = self.entry()
        targets = [(e, 0)]
        out = self.answer("Die Frau ist hier.", "Die Katze ist hier.")
        msgs, bad = check_ahead(out, targets, self.V, None, 4)
        self.assertEqual(bad, {(1, 0, 1)})                      # 'Katze' not in the list
        filled, dropped = apply_ahead(out, targets, bad, self.V, None, "generated by m")
        self.assertEqual(filled, [(1, 0)])
        [s_] = e.meanings[0].sentences
        self.assertTrue(s_.ahead)
        self.assertEqual(len(dropped), 1)

    def test_regular_fill_wins(self):
        from tools.generate import apply_ahead
        e = self.entry()
        e.order = 4  # everything known: the fill sentence is a regular one
        apply_ahead(self.answer("Die Frau ist hier.", order=4), [(e, 0)], set(), self.V, None, "n")
        self.assertFalse(e.meanings[0].sentences[0].ahead)

    def test_missing_item_reported(self):
        from tools.generate import GenAhead, check_ahead
        msgs, _ = check_ahead(GenAhead(items=[]), [(self.entry(), 0)], self.V, None, 4)
        self.assertTrue(any("missing" in m for m in msgs))

    def test_schema_rules(self):
        from tools.schema import Sentence, from_dict, SchemaError, to_dict, validate_entry
        e = self.entry()
        e.meanings[0].sentences = [Sentence("a", "b", ahead=True), Sentence("c", "d")]
        self.assertTrue(any("mixes" in x for x in validate_entry(e, "e")))
        e.meanings[0].sentences = [Sentence("a", "b", ["x.y"], ahead=True)]
        self.assertTrue(any("cannot introduce" in x for x in validate_entry(e, "e")))
        self.assertNotIn("ahead", to_dict(Sentence("a", "b")))
        self.assertTrue(to_dict(Sentence("a", "b", ahead=True))["ahead"])
        with self.assertRaises(SchemaError):
            from_dict(Sentence, {"text": "a", "en": "b", "ahead": 1})


if __name__ == "__main__":
    unittest.main()
