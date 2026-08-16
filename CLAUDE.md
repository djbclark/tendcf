# Notes for AI sessions working in this repo

`AGENTS.md` is a symlink to this file.

## Handoffs are data — commit and push in place

`docs/handoffs/` is session-handoff memory (Tier 2 deep-recovery
documents), not code — an append-only log, one file per handoff, never
rewritten. Per the operator's explicit instruction (2026-08-15), this repo
has a push-in-place exception for that directory, matching the pattern
used elsewhere in the ops-djbclark suite (e.g. `site-private/memory/`):

- Commit handoff files directly to `master`, in place — no branch, no PR,
  no worktree required.
- Push immediately after committing. Don't leave it local awaiting a
  separate "ok to push" prompt.
- This exception is narrow: `docs/handoffs/` only. Ordinary code/doc
  changes in this repo still go through normal review as the operator
  directs in the moment — this file doesn't blanket-authorize pushing
  arbitrary work.
