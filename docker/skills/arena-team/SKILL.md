---
name: arena-team
description: Runs this turn as a one-container team — research, implement, review, and verify fan out over subagents (the task tool's explore/general agents) with you as build director. Use when the task_prompt starts with the [team] marker, or when a single backlog item is deep enough to justify delegated research and a review pass before verification.
---

# Team Turn (one container, sequential fan-out)

## Overview

A team turn is the same size of work as a normal turn — one backlog item —
executed with delegated roles instead of one agent doing everything. You are
the **build director**: you decide the fan-out, hand each piece to a
subagent, assemble the results, and take responsibility for the final state.
Everything runs in ONE container with ONE working tree — no worktrees at this
tier (spec P3). Subagents must be told what each other is doing so they do
not clobber files; run them sequentially, not in parallel.

## Roles and order

1. **RESEARCH (explore subagent).** Delegate a repo + backlog survey first:
   what exists, which files the backlog item touches, integration points.
   Give it the backlog item by name. Ask for a short map back, not a plan.
2. **IMPLEMENT (general subagent(s)).** One subagent per independent piece,
   run one at a time. Give each: the file list from research, what the other
   pieces are, and the repo's standing rules (AGENTS.md). Review each
   subagent's output as it lands; reject and re-run before moving on rather
   than accumulating broken work.
3. **REVIEW (general subagent, read-only).** A fresh pass over the uncommitted
   work (git diff) hunting build-breakers: missing imports, mismatched
   function signatures, files the tests expect but that don't exist. No
   writing in this role — findings only.
4. **VERIFY (you).** Fix review findings, then run the repo's checks
   (npm test / npx tsc --noEmit / pytest) yourself — follow the
   `verification-loop` skill and write `VERIFICATION_REPORT.md` as its
   single artifact. If the product has a UI, browser-verify with the
   ui-verify skill — that is director's work, not a subagent's.
5. **ASSEMBLE.** Ensure the working tree is coherent and the backlog is
   updated. Do not commit — the harness stages and commits your work at the
   end of the turn (workflow "Commit progress" step).

## Rules

- Same turn size as a single-agent turn: the team is for depth and quality on
  ONE item, not for breadth. Do not add backlog items to "feed the team".
- Sequential fan-out only. Subagents share the working tree; parallel writes
  would race on the same files.
- Subagents do not spawn subagents (no delegation loops) — you are the only
  director.
- If a subagent is unavailable or fails twice on the same piece, do that
  piece yourself and say so in the turn summary — the turn must still land.
- Report the roster at the end: who did what, what the review found, and what
  the checks say now. That summary is the judging input for this turn.
