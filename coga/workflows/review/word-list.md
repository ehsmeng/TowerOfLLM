---
name: review/word-list
description: Human sign-off on a ranked word list — agent applies known corrections, proposes the learning order, human approves, agent finalizes and commits. Reusable per language.
steps:
  - name: apply-corrections
    assignee: agent
  - name: draft-order
    assignee: agent
  - name: sign-off
    assignee: human
  - name: finalize
    assignee: agent
---

## apply-corrections

Apply every correction already decided on the blackboard (exclusions, spelling
or case-folding fixes) through the build pipeline in `tools/`: add to the
exclusion list or config, never hand-edit the generated word list. Rebuild so
the list keeps its target length (later forms move up), run the validator, and
note on the blackboard what was dropped and which forms entered at the
bottom. Don't commit yet. Then `coga bump`.

## draft-order

Make the learning order traceable: keep reorders in a small, reviewable
reorder file under the language directory (e.g. `german/`), applied by the
build, with the `max_reorder` limit enforced by the validator. Propose the
order for the opening range named on the blackboard and leave the rest in
frequency order. On the blackboard, show the proposed opening, list the
sentences it makes possible early, and point out any moves near the limit
and any spots you weren't sure about. Rebuild, validate, then `coga bump`.

## sign-off

The human checks the corrected list and the proposed order, then either
approves or writes specific corrections (form, target position) on the
blackboard, and runs `coga bump`. If the list is wrong at its premise (bad
source, wrong filters), `coga panic` or rewind instead. The order must be
final after this step, since it sets the content filenames.

## finalize

Apply all sign-off corrections. If any are ambiguous, ask instead of
guessing. Rebuild and re-run the validator. Record the final decisions on
the blackboard, plus anything the upstream frequency-list ticket or its
pipeline should take on. Commit, then `coga mark done <slug>`.
