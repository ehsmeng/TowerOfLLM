---
name: build/agent-then-review
description: Agent builds a reviewable deliverable, the human reviews it, the agent folds in feedback and commits.
steps:
  - name: build
    assignee: agent
  - name: review
    assignee: human
  - name: finalize
    assignee: agent
---

## build

Produce the deliverable the ticket's Description asks for. Make it concrete
enough to review: alongside any spec or code, include a small worked example
of the real output (e.g. one sample data file, a few rendered pages) so the
human reacts to something tangible rather than a description. Don't commit
yet. On the blackboard, write what you built, where it lives, the decisions you
made (with reasons), and the specific points you want the human to judge.
Then `coga bump`.

## review

The human reads the deliverable and the blackboard summary, then either
approves or writes concrete feedback on the blackboard. When done, `coga bump`.
If the work is wrong at its premise rather than needing edits, rewind or
`coga panic` instead of bumping.

## finalize

Read the human's feedback on the blackboard and apply all of it. If feedback
is ambiguous, ask (interactive) or `coga panic` (auto) — don't guess. Re-run
any checks the deliverable has, record what changed on the blackboard, commit
the work, and finish with `coga mark done <slug>`.
