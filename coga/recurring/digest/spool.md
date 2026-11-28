# Daily digest spool

Producer/consumer queue for `coga digest`. Producers append one JSONL record
at the **bottom** of `## Spool (pending)`; the single consumer (`coga digest`)
advances the `consumed_through:` watermark to the newest record and trims the
consumed prefix, always keeping the newest record in place as an *anchor*.

This file is marked `merge=union` (`.gitattributes`) so two clones appending
concurrently merge without conflict. Together with the top-trim/bottom-append
shape (deletes and appends sit in disjoint hunks separated by the anchor), that
makes the spool mergeable by construction with no lock — see the `coga/sync`
context. The git high-water mark lives separately in the digest ticket's
`### Digest State`, not here.

## Spool (pending)

consumed_through:
{"id":"455198ebec88","ts":"2026-11-26T17:44","project":"TowerOfLLM","kind":"done","detail":"claude finished: finalize → done ✅","ticket":"define-language-neutral-json-format-and-repo-layou","owner":"ehsmeng"}
{"id":"752bc8781fda","ts":"2026-11-26T19:40","project":"TowerOfLLM","kind":"done","detail":"claude finished: finalize → done ✅","ticket":"build-german-frequency-list-from-zauberberg","owner":"ehsmeng"}
{"id":"dc08ec4c867c","ts":"2026-11-27T10:09","project":"TowerOfLLM","kind":"done","detail":"claude finished: finalize → done ✅","ticket":"review-german-word-list","owner":"ehsmeng"}
{"id":"080375ec70e0","ts":"2026-11-27T12:56","project":"TowerOfLLM","kind":"done","detail":"claude finished: finalize → done ✅","ticket":"write-sentence-checker","owner":"ehsmeng"}
{"id":"a0df9cad2d8b","ts":"2026-11-28T08:47","project":"TowerOfLLM","kind":"done","detail":"claude finished: finalize → done ✅","ticket":"generate-german-content-for-words-1-100","owner":"ehsmeng"}
{"id":"5923dd42efc3","ts":"2026-11-28T10:17","project":"TowerOfLLM","kind":"done","detail":"claude finished: finalize → done ✅","ticket":"build-pdf-generator-and-render-pilot","owner":"ehsmeng"}
{"id":"7c89e06b2edb","ts":"2026-11-28T15:48","project":"TowerOfLLM","kind":"done","detail":"claude finished: finalize → done ✅","ticket":"generate-german-verbs-json-for-the-verb-appendix","owner":"ehsmeng"}
