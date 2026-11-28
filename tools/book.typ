// Course book template. Language-neutral: everything comes from the book
// model that tools/pdf.py writes (sys.inputs.data). Explanations and glosses
// are English; target-language text is tagged with its language code so it
// hyphenates correctly.

#let D = json(sys.inputs.at("data"))
#let L = D.language.code
#let B = D.book

// ---------------------------------------------------------------- palette
#let ink = rgb("#1f1c18")
#let muted = rgb("#6e675d")
#let faint = rgb("#a39a8c")
#let accent = rgb("#8c2f22")      // oxblood
#let tint = rgb("#f5efe3")        // warm paper tint for grammar boxes
#let rule-c = rgb("#d8cfbf")
#let review-c = rgb("#9a6a1f")    // reviewer notes: ochre "pencil"
#let ahead-c = rgb("#7a7266")     // notes on words borrowed from later pages

#let serif = ("EB Garamond",)
#let sans = ("Source Sans 3",)

#let pos-names = (
  ADJ: "adjective", ADP: "preposition", ADV: "adverb", AUX: "auxiliary verb",
  CCONJ: "conjunction", DET: "determiner", INTJ: "interjection", NOUN: "noun",
  NUM: "numeral", PART: "particle", PRON: "pronoun", PROPN: "proper noun",
  SCONJ: "subordinating conjunction", VERB: "verb", X: "other",
)

// ---------------------------------------------------------------- document
#set document(title: B.title, keywords: (D.language.name, "vocabulary"))
#set page(
  width: 155mm, height: 235mm,
  margin: (inside: 21mm, outside: 17mm, top: 19mm, bottom: 23mm),
  binding: left,
  footer: context {
    set text(font: sans, size: 7.5pt, fill: muted, number-type: "lining")
    let folio = text(fill: ink, str(counter(page).get().first()))
    let title = text(tracking: 0.1em, upper(B.title))
    if calc.odd(here().page()) { h(1fr); title; h(1.2em); folio } else { folio; h(1.2em); title; h(1fr) }
  },
)
#set text(font: serif, size: 10.5pt, fill: ink, lang: "en", number-type: "old-style",
          hyphenate: true, costs: (hyphenation: 80%))
#set par(justify: true, leading: 0.6em, spacing: 0.9em)
#show heading: it => none   // headings exist only for PDF bookmarks

#let target(body) = text(lang: L, body)
#let label-caps(body, fill: accent, size: 6.8pt) = text(
  font: sans, size: size, weight: "semibold", tracking: 0.13em, fill: fill,
  number-type: "lining", upper(body))
#let ornament = box(line(length: 14mm, stroke: 0.6pt + accent))

// ---------------------------------------------------------------- pieces
#let note-label = "NOTE"
#let review-note(t, fill: review-c) = block(
  above: 0.35em, below: 0.25em, inset: (left: 2.4mm, y: 0.5mm),
  stroke: (left: 0.6pt + fill), breakable: false,
)[
  #set par(justify: false, leading: 0.48em)
  #set text(font: sans, size: 7.4pt, fill: fill, number-type: "lining", hyphenate: true)
  #text(weight: "semibold", tracking: 0.09em, note-label)#h(0.55em)#t
]

// Under an ahead sentence: the forms it borrows from later pages.
#let ahead-note(words) = review-note(fill: ahead-c, {
  [Uses #if words.len() == 1 [a word] else [words] from later in the course: ]
  words.map(w => [#text(font: serif, size: 8.6pt, style: "italic", target(w.form)) (#w.order)]).join(", ")
  [.]
})

#let gmark(nums) = if nums.len() > 0 {
  h(0.2em)
  super(typographic: false, size: 6.4pt, baseline: -0.45em,
        text(font: sans, fill: accent, weight: "semibold", number-type: "lining",
             nums.map(n => "§" + str(n)).join(" ")))
}

// German | English rows, with reviewer remarks spanning both columns.
#let pairs(items, size: 10.5pt, row-gap: 0.5em) = {
  let cells = ()
  for s in items {
    cells.push(text(size: size, target(s.text)) + gmark(s.at("grammar", default: ())))
    cells.push(text(size: size - 0.5pt, style: "italic", fill: muted, s.en))
    let ahead = s.at("ahead", default: ())
    if ahead.len() > 0 {
      cells.push(grid.cell(colspan: 2, inset: (left: 3mm, bottom: 0.15em), ahead-note(ahead)))
    }
    for r in s.review {
      cells.push(grid.cell(colspan: 2, inset: (left: 3mm, bottom: 0.15em), review-note(r)))
    }
  }
  set par(justify: false)
  grid(columns: (1fr, 1fr), column-gutter: 5mm, row-gutter: row-gap, ..cells)
}

#let concept-box(c) = block(
  width: 100%, fill: tint, stroke: (left: 1.4pt + accent),
  inset: (left: 4.5mm, right: 4mm, top: 3.4mm, bottom: 3.8mm),
  above: 1.0em, below: 1.0em, breakable: true,
)[
  #block(below: 0.5em, label-caps("Grammar  §" + str(c.number)))
  #block(below: 0.6em, text(size: 12pt, weight: "semibold", c.title))
  #set text(size: 10pt)
  #c.explanation
  #if c.examples.len() > 0 {
    v(0.25em)
    pairs(c.examples, size: 9.8pt, row-gap: 0.4em)
  }
  #if c.related.len() > 0 {
    v(0.2em)
    set text(size: 8.4pt, fill: muted)
    [_See also_ ]
    c.related.map(r => {
      r.title
      if r.number != none { [ (§#r.number, word #r.entry)] }
    }).join("; ")
  }
  #for r in c.review { review-note(r) }
]

#let meaning-head(i, n, mn, e) = {
  let bits = (pos-names.at(mn.pos, default: mn.pos),)
  if mn.morph != none { bits.push(mn.morph) }
  block(above: 1.25em, below: 0.6em, sticky: true, {
    set par(justify: false)
    if n > 1 { text(fill: accent, weight: "semibold", number-type: "lining", str(i)); h(0.6em) }
    text(weight: "medium", size: 11pt, mn.gloss)
    if mn.base != e.base and mn.base != e.form { text(fill: muted)[ · _of_ #target(mn.base)] }
    linebreak()
    text(font: sans, size: 7.6pt, fill: muted, bits.join(" · "))
  })
  for r in mn.review { review-note(r) }
}

#let entry-page(e) = {
  pagebreak(weak: true)
  heading(level: 2, bookmarked: true)[#e.order #e.form]
  // header
  context {
    let num = text(size: 34pt, fill: accent, number-type: "lining", str(e.order))
    let indent = measure(num).width + 4mm
    set par(justify: false, leading: 0.5em, hanging-indent: indent)
    num; h(4mm); text(size: 30pt, weight: "semibold", target(e.form))
    linebreak()
    text(size: 12.5pt, style: "italic", fill: muted, e.translation)
  }
  v(0.6em)
  line(length: 100%, stroke: 0.5pt + rule-c)
  v(-0.55em)
  {
    set text(font: sans, size: 7pt, fill: faint, number-type: "lining")
    if e.base != e.form [form of #target(e.base) #h(0.8em)]
    h(1fr)
    [frequency rank #e.frequency_rank · #e.count occurrences]
  }
  for r in e.review { review-note(r) }
  // grammar commentary first, then the sentences
  for c in e.grammar { concept-box(c) }
  let n = e.meanings.len()
  for (i, mn) in e.meanings.enumerate(start: 1) {
    meaning-head(i, n, mn, e)
    if mn.sentences.len() > 0 { pairs(mn.sentences) } else {
      text(size: 9.5pt, style: "italic", fill: faint)[No sentences yet: they need words that come later in the course.]
    }
  }
}

// ---------------------------------------------------------------- front matter
#page(footer: none)[
  #set align(center)
  #set par(justify: false)
  #v(26%)
  #label-caps(D.language.native_name, size: 8pt)
  #v(1.2em)
  #block(width: 62%, text(size: 30pt, weight: "medium", number-type: "lining", hyphenate: false, B.title))
  #if B.subtitle != none { v(0.4em); text(size: 13pt, style: "italic", fill: muted, B.subtitle) }
  #v(2.2em)
  #ornament
  #v(1fr)
  #if B.pilot {
    label-caps("Pilot edition", size: 7.5pt)
    linebreak()
    text(size: 10pt, fill: muted, number-type: "lining")[words #B.first–#B.last of #B.planned_last]
  }
  #v(8%)
]

#page(footer: none)[
  #set text(size: 8.6pt, fill: muted)
  #set par(justify: false, leading: 0.55em, spacing: 1.1em)
  #v(1fr)
  *#B.title* \
  #D.language.name · words #B.first–#B.last#if B.pilot [ (pilot edition; the book will cover #B.first–#B.planned_last)]

  This book and its data are licensed under the *Creative Commons Attribution 4.0
  International License* (CC BY 4.0). You may copy, share and adapt them for any
  purpose, provided you give appropriate credit and indicate changes.
  #link("https://creativecommons.org/licenses/by/4.0/")

  *Word frequencies.* #D.language.source.
  #if D.language.source_url != none [#link(D.language.source_url).]
  The learning order follows these counts, moved by a few places where that lets
  early sentences be formed.

  *How the content was made.* Sentences, translations and grammar notes were
  written by a language model#if D.models.len() > 0 [ (#D.models.join(", "))] and
  checked by program: every sentence uses only words taught up to its page,
  plus names, except for a few marked sentences that borrow words from later
  pages. An automatic reviewer then read everything; its remarks are
  printed where they apply, marked #text(font: sans, size: 7pt, weight: "semibold", tracking: 0.09em, fill: review-c, note-label).

  Set in EB Garamond and Source Sans 3 (SIL Open Font License). Typeset with Typst.

  Built #D.built · #D.stats.entries words · #D.stats.sentences sentences ·
  #D.stats.concepts grammar notes
]

#page(footer: none)[
  #heading(level: 1, bookmarked: true)[How to use this book]
  #v(6%)
  #align(center, text(size: 18pt, weight: "medium")[How to use this book])
  #v(1.4em)
  #set par(spacing: 1em)
  Each page teaches one #D.language.name word form, in the order you should
  learn them: the most frequent words first. The large number is the word's
  place in that order; the word index at the back uses these numbers.

  Under the word come its *grammar notes*, then its *example sentences*, grouped
  by meaning when a word has more than one. Every sentence uses only words from
  its own page and earlier pages, so you can read the book from the front and
  understand every line. Names of people and places are the only exception,
  apart from a few marked sentences (see below).

  A grammar point is explained once, on the page where it first appears, and
  numbered with #text(font: sans, fill: accent, weight: "semibold", size: 8pt, "§"). The same
  mark after a sentence shows where that point is at work.

  Some meanings can't be shown yet with the words you know: an article, say,
  before you have met any nouns. Those meanings still get a sentence, which
  borrows a word or two from later pages. A grey note under it lists the
  borrowed words with their numbers:

  #block(above: 0.7em, below: 1.2em, ahead-note(((form: "Beispiel", order: 1234),)))

  Ochre notes come from an automatic reviewer. They point out a sentence or
  translation that may be unusual or imprecise; read the sentence with that in
  mind:

  #block(above: 0.7em, below: 1.2em, review-note[The English is freer than the German here.])

  #v(1fr)
  #align(center, ornament)
  #v(1fr)
]

// ---------------------------------------------------------------- word pages
#pagebreak(to: "odd")
#heading(level: 1, bookmarked: true)[Words #B.first–#B.last]
#counter(page).update(1)
#for e in D.entries { entry-page(e) }

// ---------------------------------------------------------------- appendix
#let section-title(t, sub: none) = {
  pagebreak(to: "odd", weak: true)
  heading(level: 1, bookmarked: true, t)
  v(12%)
  align(center, {
    label-caps("Appendix", size: 7.5pt)
    v(0.5em)
    text(size: 22pt, weight: "medium", t)
    if sub != none { v(0.2em); text(style: "italic", fill: muted, sub) }
  })
  v(2em)
}

// One tense: person (with English) | form | minimal sentence over its translation.
#let tense-table(t) = block(breakable: false, width: 100%, above: 1.5em, below: 0.4em, {
  block(below: 0.7em, sticky: true, label-caps(t.label, size: 6.8pt))
  set par(justify: false, leading: 0.45em)
  let cells = ()
  for r in t.forms {
    cells.push({
      text(size: 9.6pt, target(r.person))
      if r.person_en != none {
        linebreak(); text(font: sans, size: 6.9pt, fill: muted, hyphenate: false, r.person_en)
      }
    })
    cells.push(text(size: 10.5pt, weight: "semibold", hyphenate: false, target(r.form)))
    cells.push(if r.example != none {
      text(size: 9.8pt, target(r.example.text))
      linebreak()
      text(size: 8.6pt, style: "italic", fill: muted, r.example.en)
    })
  }
  grid(columns: (25mm, 31mm, 1fr), column-gutter: 3mm,
       stroke: (x, y) => if y > 0 { (top: 0.3pt + rule-c) },
       inset: (x: 0pt, y: 0.42em), ..cells)
})

#let A = D.appendix
#section-title(
  "The " + str(A.wanted) + " most common verbs",
  sub: "with full conjugation tables",
)
#if A.illustrative {
  review-note[Illustrative: the verb data for this book is not generated yet.
  This shows #A.verbs.len() of #A.wanted verbs, from the format example.]
}
#for vb in A.verbs {
  pagebreak(weak: true)
  heading(level: 2, bookmarked: true, vb.base)
  block(below: 0.4em, {
    text(size: 24pt, weight: "semibold", target(vb.base))
    h(0.6em)
    text(size: 13pt, style: "italic", fill: muted, vb.translation)
  })
  if vb.participles.len() > 0 {
    set text(font: sans, size: 7.8pt, fill: muted)
    vb.participles.pairs().map(((k, f)) => [#k participle #text(font: serif, size: 10pt, fill: ink, target(f))]).join(h(1.5em))
  }
  line(length: 100%, stroke: 0.5pt + rule-c)
  for t in vb.tenses { tense-table(t) }
}

// ---------------------------------------------------------------- indexes
#let leader-row(left, right) = box(width: 100%, {
  left
  box(width: 1fr, inset: (x: 0.25em), repeat(text(fill: rule-c, ".")))
  text(number-type: "lining", size: 8.5pt, fill: muted, right)
})

#pagebreak(to: "odd", weak: true)
#heading(level: 1, bookmarked: true)[Index of words]
#align(center, text(size: 18pt, weight: "medium")[Index of words])
#align(center, text(size: 9pt, style: "italic", fill: muted)[numbers refer to words, not pages])
#v(1.2em)
#{
  set par(justify: false, spacing: 0.32em)
  set text(size: 9.6pt)
  columns(3, gutter: 6mm, {
    let initial = none
    for x in D.index {
      let first = upper(x.form.clusters().first())
      let first = if first in ("Ä",) { "A" } else if first == "Ö" { "O" } else if first == "Ü" { "U" } else { first }
      if first != initial {
        initial = first
        block(above: 0.9em, below: 0.4em, sticky: true, label-caps(first, size: 7.5pt))
      }
      leader-row(target(x.form), str(x.order))
    }
  })
}

#pagebreak(weak: true)
#heading(level: 1, bookmarked: true)[Index of grammar]
#align(center, text(size: 18pt, weight: "medium")[Index of grammar])
#align(center, text(size: 9pt, style: "italic", fill: muted)[§ number, then the word where it is explained])
#v(1.2em)
#{
  set par(justify: false, spacing: 0.42em)
  set text(size: 9.8pt)
  for g in D.grammar_index {
    leader-row(g.title, "§" + str(g.number) + "  ·  " + str(g.entry))
  }
}
