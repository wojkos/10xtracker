# Frame Brief: Support Worktrees

> Framing step before /10x-plan. This document captures what is *actually*
> at issue, separated from what was initially assumed.

## Reported Observation

User created a git worktree (intending the "one worktree per change" model
described in CLAUDE.md) and found that `context/changes/<id>/` change-tracking
files were not visible inside that worktree. They asked how to "add support
for changes in worktrees."

## Initial Framing (preserved)

- **User's stated cause or approach**: Not clearly stated — the raw request
  had no specific theory for *why* the worktree couldn't see the change
  folder, just "how can I add support."
- **User's proposed direction**: Add some form of worktree support to the
  toolkit (unspecified — could mean a skill/code change or a documented
  process).
- **Pre-dispatch narrowing**:
  - Trigger: "context/changes/ isn't visible in the worktree" (not a crash or error — an absence)
  - Scope: wants to update change state from a worktree, "maybe there is new change" (open to either a code change or process fix)
  - Relationship: "one worktree = one change" — confirms the model CLAUDE.md already describes

## Dimension Map

1. **Commit timing relative to worktree creation** — git worktrees check
   out from committed history; a change-tracking file created via
   `/10x-new`/`/10x-plan` but not yet committed on the source branch will not
   exist in a newly added worktree.  ← matches reported observation
2. **Skill path/cwd assumptions** — `/10x-*` skills could hardcode paths
   tied to the original checkout's location rather than resolving relative
   to cwd, breaking when invoked from a worktree's directory.
3. **Stale/wrong branch checked out in the worktree** — worktree created
   from a ref that predates the change folder's commit.
4. **No worktree was actually created** — the ask is about designing the
   intended workflow, not fixing something concretely broken in git itself.

## Hypothesis Investigation

| Hypothesis | Evidence | Verdict |
| --- | --- | --- |
| Commit timing relative to worktree creation | `context/changes/support-worktrees/` and `context/changes/archive-project/` are both untracked (`git status` shows `??`) immediately after `/10x-new`. `git log -- context/changes/` shows change-folder commits landing alongside the *first implementation* commit (e.g. `94548a2 feat(next-action-dashboard): add next action panel rendering (p2)`), not at change-creation time. | STRONG |
| Skill path/cwd assumptions | Grepped `.claude/skills/**` for "worktree", "cwd", "repo root", "working directory" — no `/10x-*` skill contains worktree-aware or hardcoded-path logic. Skills resolve paths relative to invocation directory generically. | NONE |
| Stale/wrong branch | `git worktree list` shows only the main checkout (`master`) — no other worktree exists to have checked out a stale ref. Not reproducible in current state. | NONE |
| No worktree actually created | `.git/worktrees/` does not exist on disk and `git worktree list` returns only the main checkout. No worktree is currently registered in this repo. | STRONG |

## Narrowing Signals

- User confirmed the friction is an *absence* ("isn't visible"), not an
  error — consistent with hypothesis 1 (uncommitted files don't propagate to
  a new worktree), inconsistent with hypothesis 2 (which would surface as a
  path-not-found or wrong-directory error instead).
- User confirmed the intended model is "one worktree = one change," matching
  CLAUDE.md's existing lesson design — the fix belongs in *when* that
  worktree gets created relative to committing the change folder, not in a
  new multi-worktree coordination feature.
- No `.git/worktrees` entry exists — whatever worktree the user made was
  either never registered via `git worktree add` or was later removed; there
  is no broken git plumbing to repair.

## Cross-System Convention

Git worktrees share the `.git` object/history database but each has its own
working tree; a worktree only contains what is committed to the ref it
checks out — this is standard git behavior, not project-specific. Projects
that combine worktrees with generated/tracked planning artifacts typically
resolve this by committing the artifact (even a small "start change X"
commit) *before* branching into the worktree. This repo already does that
implicitly for `plan.md` (committed alongside the first implementation
commit) — the gap is that `change.md` from `/10x-new` has no equivalent
commit point, and no lesson step tells the user to commit before running
`git worktree add`.

## Reframed (or Confirmed) Problem Statement

> **The actual problem to plan around is**: the change-creation workflow
> (`/10x-new` and the worktree step that follows it) has no defined point at
> which change-tracking files get committed relative to worktree creation,
> so "one worktree per change" silently breaks the moment a worktree is
> created before that first commit.

This is not a git bug and not a missing skill feature — no code in
`.claude/skills` needs to become worktree-aware. What's missing is a
convention (and a one-line reminder in the router/lesson content) for *when*
to commit the change folder so a subsequently-created worktree actually
contains it. Updating `change.md` status from inside a worktree needs no
special mechanism either — it's the same repo history, so a normal commit +
merge/PR carries it back.

## Confidence

**HIGH** — the underlying mechanism (worktrees only see committed history)
is a certain, verifiable git fact, not a hypothesis. Direct repo evidence
(untracked change files immediately after `/10x-new`, no `.git/worktrees`
present, no skill touches worktree/path logic) all points the same
direction with nothing contradicting it.

## What Changes for /10x-plan

Scope the plan narrowly: (1) define/document the "commit the change folder
before `git worktree add`" step — likely a small addition to CLAUDE.md's
task router or parallel-work-rules section — and (2) confirm no special sync
mechanism is needed for status updates made inside a worktree beyond normal
commit + merge. Do **not** plan new worktree-detection code or a new skill;
the evidence found nothing to build there.

## References

- Source: [CLAUDE.md](../../../CLAUDE.md) (task router, parallel work rules)
- Source: [context/changes/support-worktrees/change.md](change.md) (untracked at creation — direct evidence)
- Source: `context/changes/archive-project/` (untracked at creation — corroborating evidence)
- Git history: `git log --oneline -- context/changes/` (commit-timing pattern)
