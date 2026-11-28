"""Offline tests for tools/verbs.py (no API calls).  Run: python -m unittest tools.test_verbs"""

from __future__ import annotations

import unittest

from tools.schema import Entry, Meaning, Verbs, WordList, WordListItem, from_dict, to_dict
from tools.verbs import (FINITE_PERSONS, OTHER, PERSONS, GenExample, GenForm, GenTense, GenVerb,
                         GenRepair, RepairAction, Repair, ReviewIssue, VerbReview, candidates, check_verb, count_note, crosscheck,
                         expected_cells,
                         kaikki_cell, paradigm, rank, readings, repair_verb, to_verb, uses_form)


def wl(*pairs):
    return WordList(1, "de", "t", [WordListItem(order=i, form=f, frequency_rank=i, count=c)
                                   for i, (f, c) in enumerate(pairs, 1)])


SEIN = {"forms": ["bin", "ist", "sein", "war", "gewesen"], "table": {}, "participles": {}}
MEINEN = {"forms": ["meine", "meinen", "meint"], "table": {}, "participles": {}}
HABEN = {"forms": ["habe", "hat", "haben"], "table": {}, "participles": {}}
LEMMA = {"bin": "sein", "ist": "sein", "sein": "sein", "war": "sein", "gewesen": "sein",
         "seinen": "sein", "meine": "mein", "meint": "meinen", "hat": "haben", "habe": "haben"}


def lem(w):
    return LEMMA.get(w, w)


class Kaikki(unittest.TestCase):
    def test_cells(self):
        self.assertEqual(kaikki_cell({"first-person", "indicative", "present", "singular"}), ("praesens", "ich"))
        self.assertEqual(kaikki_cell({"indicative", "multiword-construction", "perfect", "plural",
                                      "third-person"}), ("perfekt", "sie/Sie"))
        self.assertEqual(kaikki_cell({"second-person", "singular", "subjunctive", "subjunctive-ii"}),
                         ("konjunktiv_ii", "du"))
        self.assertEqual(kaikki_cell({"imperative", "plural", "second-person"}), ("imperativ", "ihr"))
        # future subjunctive and infinitives are not table cells we use
        self.assertIsNone(kaikki_cell({"first-person", "future", "future-i", "multiword-construction",
                                       "singular", "subjunctive", "subjunctive-i"}))
        self.assertIsNone(kaikki_cell({"future", "future-i", "infinitive", "multiword-construction"}))

    def test_paradigm(self):
        p = paradigm([
            {"form": "irregular", "tags": ["table-tags"]},
            {"form": "haben", "tags": ["auxiliary"]},
            {"form": "getan", "tags": ["participle", "past"]},
            {"form": "tue", "tags": ["first-person", "indicative", "present", "singular"]},
            {"form": "habe getan", "tags": ["first-person", "indicative", "multiword-construction",
                                            "perfect", "singular"]},
        ])
        self.assertEqual(p["forms"], ["getan", "tue"])
        self.assertEqual(p["table"]["perfekt"]["ich"], ["habe getan"])
        self.assertEqual(p["participles"], {"past": ["getan"]})


class Ranking(unittest.TestCase):
    def setUp(self):
        self.words = wl(("bin", 100), ("meine", 50), ("hat", 40), ("sein", 30), ("seinen", 20),
                        ("gewesen", 10), ("meint", 5))
        meine = Entry(1, "de", 2, "meine", "mein", "my", [
            Meaning("my", "mein", "DET"), Meaning("(I) mean", "meinen", "VERB")])
        self.verbs = {"sein": SEIN, "meinen": MEINEN, "haben": HABEN}
        self.rs, self.dis = readings(self.words, {2: meine}, self.verbs, lem, {"sein", "meine"})

    def test_readings(self):
        r = self.rs
        self.assertFalse(r["bin"].ambiguous)
        self.assertTrue(r["meine"].ambiguous)          # entry has DET + VERB meanings
        self.assertEqual(r["meine"].verbs, {"meinen"})
        self.assertTrue(r["sein"].ambiguous)           # kaikki lists possessive "sein"
        self.assertNotIn("seinen", r)                  # lemma "sein" but not in its paradigm
        self.assertEqual(self.dis, ["meine: entry bases ['meinen'], simplemma 'mein'"])

    def test_candidates_bound(self):
        # lower: sein 110, haben 40, meinen 5; upper adds ambiguous forms
        self.assertEqual(candidates(self.rs, 1), ["sein"])
        self.assertEqual(set(candidates(self.rs, 2)), {"sein", "meinen", "haben"})

    def test_rank_with_shares(self):
        shares = {"meine": {"meinen": 0.04, OTHER: 0.96}, "sein": {"sein": 0.2, OTHER: 0.8}}
        top = rank(self.rs, shares, 3)
        self.assertEqual([t.base for t in top], ["sein", "haben", "meinen"])
        sein = top[0]
        self.assertEqual(sein.total, 100 + 10 + 6)
        self.assertEqual([(s.form, s.count, s.verb_share) for s in sein.splits], [("sein", 30, 0.2)])
        self.assertEqual(sein.splits[0].notes, "rest: non-verb 80%")
        self.assertEqual(top[2].total, 5 + 2)
        self.assertIn("split: sein 6 of 30", count_note(sein))

    def test_missing_share_not_counted(self):
        top = rank(self.rs, {}, 3)
        self.assertEqual(top[0].total, 110)


def tense(tid, forms, texts=None, persons=None):
    persons = persons or FINITE_PERSONS
    texts = texts or [f"x {f} x." for f in forms]
    return GenTense(tense=tid, forms=[GenForm(person=p, form=f) for p, f in zip(persons, forms)],
                    examples=[GenExample(person=p, text=t, en="e") for p, t in zip(persons, texts)])


def sein_verb(**over):
    six = lambda *f: list(f)
    ts = [
        tense("praesens", six("bin", "bist", "ist", "sind", "seid", "sind")),
        tense("praeteritum", six("war", "warst", "war", "waren", "wart", "waren")),
        tense("perfekt", six(*[a + " gewesen" for a in ("bin", "bist", "ist", "sind", "seid", "sind")])),
        tense("plusquamperfekt", six(*[a + " gewesen" for a in ("war", "warst", "war", "waren", "wart", "waren")])),
        tense("futur_i", six(*[a + " sein" for a in ("werde", "wirst", "wird", "werden", "werdet", "werden")])),
        tense("futur_ii", six(*[a + " gewesen sein" for a in ("werde", "wirst", "wird", "werden", "werdet", "werden")])),
        tense("konjunktiv_i", six("sei", "seist", "sei", "seien", "seiet", "seien")),
        tense("konjunktiv_ii", six("wäre", "wärst", "wäre", "wären", "wärt", "wären")),
        tense("imperativ", ["sei", "seid", "seien Sie"], persons=["du", "ihr", "Sie"]),
    ]
    d = dict(base="sein", translation="to be", present_participle="seiend",
             past_participle="gewesen", tenses=ts)
    d.update(over)
    return GenVerb(**d)


class Checks(unittest.TestCase):
    def test_uses_form(self):
        self.assertTrue(uses_form("Ich bin müde.", "bin", "sein", "gewesen"))
        self.assertTrue(uses_form("Wo bist du gewesen?", "bist gewesen", "sein", "gewesen"))
        self.assertTrue(uses_form("Ich fange morgen an.", "fange an", "anfangen", "angefangen"))
        self.assertTrue(uses_form("Ich habe nicht kommen können.", "habe gekonnt", "können", "gekonnt"))
        self.assertFalse(uses_form("Ich habe nicht gekonnt.", "habe gewollt", "wollen", "gewollt"))
        self.assertFalse(uses_form("Ich war müde.", "bin", "sein", "gewesen"))

    def test_good_verb(self):
        self.assertEqual(check_verb(sein_verb(), "sein"), [])

    def test_imperative_optional_others_not(self):
        v = sein_verb()
        v.tenses = v.tenses[:-1]
        self.assertEqual(check_verb(v, "sein"), [])
        v.tenses = v.tenses[1:]
        self.assertTrue(any("tenses must be" in e for e in check_verb(v, "sein")))

    def test_bad_example_and_persons(self):
        v = sein_verb()
        v.tenses[0].examples[0].text = "Ich war müde."
        v.tenses[1].forms = v.tenses[1].forms[:5]
        errs = check_verb(v, "sein")
        self.assertTrue(any("praesens.ich" in e and "does not use" in e for e in errs))
        self.assertTrue(any("praeteritum: missing persons" in e for e in errs))

    def test_crosscheck(self):
        p = {"table": {"praesens": {"ich": ["bin"], "du": ["bist"]},
                       "konjunktiv_i": {"sie/Sie": ["seien"]},
                       "konjunktiv_ii": {"du": ["wärst", "wärest"]}},
             "participles": {"past": ["gewesen"]}}
        p["table"]["imperativ"] = {"du": ["sei"], "ihr": ["seid"]}
        v = sein_verb()
        bad, checked, missing = crosscheck(v, p)
        self.assertEqual(bad, [])
        self.assertEqual(checked, 8)                   # bin, bist, seien, wärst, sei, seid, seien Sie (derived), past
        # no kaikki imperative (modal verbs): omitting it is fine, nothing derived
        modal = sein_verb()
        modal.tenses = modal.tenses[:-1]
        no_imp = {"table": {k: c for k, c in p["table"].items() if k != "imperativ"}, "participles": {}}
        self.assertEqual(crosscheck(modal, no_imp)[0], [])
        self.assertEqual(crosscheck(modal, p)[0], ["tenses omitted but in kaikki: ['imperativ']"])
        # with a kaikki imperative, Sie may come from the present ("tun Sie") or Konjunktiv I
        tun = {"table": {"praesens": {"sie/Sie": ["tun"]}, "konjunktiv_i": {"sie/Sie": ["tuen"]},
                         "imperativ": {"du": ["tu"]}}, "participles": {}}
        self.assertEqual(expected_cells(tun)["imperativ"]["Sie"], ["tun Sie", "tuen Sie"])
        sep = {"table": {"praesens": {"sie/Sie": ["fangen an"]}, "imperativ": {"du": ["fang an"]}}}
        self.assertEqual(expected_cells(sep)["imperativ"]["Sie"], ["fangen Sie an"])
        v.tenses[0].forms[1].form = "bis"
        self.assertEqual(crosscheck(v, p)[0], ["praesens.du: 'bis' vs kaikki ['bist']"])
        self.assertEqual(crosscheck(v, None)[0], ["'sein' not in the kaikki index: nothing cross-checked"])


class Convert(unittest.TestCase):
    def test_to_verb_roundtrip(self):
        from tools.verbs import Ranked
        from tools.schema import CountSplit
        rk = Ranked("sein", 116, [("bin", 100)], [CountSplit("sein", 30, 0.2, "rest: non-verb 80%")])
        v = to_verb(sein_verb(), rk, "n")
        self.assertTrue(all(e.review is None for t in v.tenses for e in t.examples.values()))
        self.assertEqual(v.tenses[-1].label, "Imperativ (command)")
        self.assertEqual(v.count_splits[0].form, "sein")
        data = Verbs(1, "de", [v], PERSONS)
        self.assertEqual(from_dict(Verbs, to_dict(data)), data)

    def test_pdf_prints_no_verb_review(self):
        from tools.pdf import verb_row
        from tools.verbs import Ranked
        v = to_verb(sein_verb(), Ranked("sein", 1, [], []), "n")
        t = v.tenses[0]
        t.examples["ich"].review = "warning: stray"
        self.assertNotIn("review", verb_row("ich", t.forms["ich"], t, PERSONS)["example"])


ISSUE = ReviewIssue(tense="praesens", person="du", severity="error", comment="Wrong English.")


class FakeGen:
    """Answers repair/review calls from queues; records the labels."""
    def __init__(self, repairs, reviews):
        self.repairs, self.reviews, self.labels = list(repairs), list(reviews), []

    def call(self, system, user, schema, label):
        self.labels.append(label)
        return (self.repairs if schema is GenRepair else self.reviews).pop(0)


def fixed(v, text="Du bist da.", en="You are here."):
    v = v.model_copy(deep=True)
    ex = next(e for e in v.tenses[0].examples if e.person == "du")
    ex.text, ex.en = text, en
    return v


class RepairPass(unittest.TestCase):
    def act(self, a="fixed"):
        return [RepairAction(tense="praesens", person="du", action=a, reason="r")]

    def test_fix_then_clean(self):
        g = sein_verb()
        gen = FakeGen([GenRepair(verb=fixed(g), actions=self.act())], [VerbReview(issues=[])])
        r = repair_verb(gen, g, VerbReview(issues=[ISSUE]), None, rounds=2, retries=1)
        self.assertEqual(r.open, [])
        self.assertEqual(r.verb.tenses[0].examples[1].en, "You are here.")
        self.assertEqual(gen.labels, ["repair sein r1", "review sein r1"])
        self.assertEqual(Repair.from_json(r.to_json()).verb, r.verb)

    def test_no_issues_no_calls(self):
        gen = FakeGen([], [])
        r = repair_verb(gen, sein_verb(), VerbReview(issues=[]), None, rounds=2, retries=1)
        self.assertEqual((r.rounds, r.open, gen.labels), ([], [], []))

    def test_bad_repair_retried_then_rejected(self):
        g = sein_verb()
        bad = fixed(g, text="Du warst da.")          # no longer uses the form "bist"
        gen = FakeGen([GenRepair(verb=bad, actions=self.act())] * 2, [])
        r = repair_verb(gen, g, VerbReview(issues=[ISSUE]), None, rounds=2, retries=1)
        self.assertEqual(r.verb, g)                  # original kept
        self.assertEqual(r.open, [ISSUE])
        self.assertTrue(r.rounds[0]["rejected"])

    def test_rounds_exhausted_leaves_open(self):
        g = sein_verb()
        gen = FakeGen([GenRepair(verb=fixed(g), actions=self.act())] * 2,
                      [VerbReview(issues=[ISSUE])] * 2)
        r = repair_verb(gen, g, VerbReview(issues=[ISSUE]), None, rounds=2, retries=0)
        self.assertEqual(len(r.rounds), 2)
        self.assertEqual(r.open, [ISSUE])


if __name__ == "__main__":
    unittest.main()
