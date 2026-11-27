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
