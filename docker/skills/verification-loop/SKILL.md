---
name: verification-loop
description: Runs the full pre-commit verification ladder (build, typecheck, lint, test, security, diff) and writes a fixed-format report. Use before committing a build turn, when the harness flags a type or test failure, or when you need a single artifact proving the tree is green. Produces VERIFICATION_REPORT.md; never claims green without the command output.
---

# Verification Loop

Adapted from `affaan-m/ECC` `skills/verification-loop` (MIT). Their loop is
generic; this is the arena's version — the six phases, the fixed report format,
and the hard rule that a phase you skipped is reported as SKIPPED with a
reason, never as PASS.

## Why this exists

A build turn is judged on what it can prove, not on what it believes. This
loop produces one artifact — `VERIFICATION_REPORT.md` at the repo root — that
carries the evidence into the next turn, into judging, and into the archive.
It also makes failures legible: a turn that reports "typecheck FAILED, here
is the error" beats a turn that claims success and gets caught by the
harness after the fact.

## The Six Phases

Run each phase that applies to this repo, in order. Discover the real commands
first (see the stack-discovery section in the `test-driven-development`
skill) — a Gradle repo has no `npm test`, a pytest repo has no `tsc`.

| # | Phase | Typical command (adapt to the repo) |
|---|---|---|
| 1 | **Build** | the build/dev command the README or CI declares |
| 2 | **Typecheck** | `npx tsc --noEmit`, `mvn -q compile`, `pyright`, `cargo check` |
| 3 | **Lint / format** | the repo's lint script; run it if one exists |
| 4 | **Test** | the full suite, not the focused test |
| 5 | **Security** | dependency audit + secret scan on what you touched |
| 6 | **Diff** | `git status --porcelain` + `git diff --stat` — what actually changed this turn |

Rules that make the loop honest:

- **Fresh output, always.** Run the commands now, after your last edit. A
  result from before your last edit proves nothing (see
  `verification-before-completion`).
- **Exit code is the verdict.** Read the code, not the vibe of the output.
- **Fail is not error.** A crash in the tool is an ERROR, not a FAIL; an
  ERROR is never acceptable to commit on.
- **No phase, no claim.** If a phase cannot run (no linter configured, no
  tests yet), record `SKIPPED (reason)` — never `PASS`.
- **Stop at the first FAIL** in the ladder? No — keep going and report every
  phase. A later phase's output often explains the earlier failure.

## The Report

Write `VERIFICATION_REPORT.md` at the repo root, overwriting any previous
turn's report. Exact format (this is the contract; the harness's Enforce step
and the next turn both read it):

```markdown
# Verification report — turn <turn_id if known, else "manual">

| Phase | Command | Result | Exit |
|---|---|---|---|
| Build | <command> | PASS \| FAIL \| SKIPPED (reason) | <code> |
| Typecheck | <command> | ... | <code> |
| Lint | <command> | ... | <code> |
| Test | <command> | ... | <code> |
| Security | <command> | ... | <code> |
| Diff | <command> | N files changed | — |

## Test evidence
- command: <full test command>
- result: <N passed, M failed, K skipped>
- failing test names (if any): <names + one-line reason>

## Security notes
- dependency audit: <clean | findings + severity>
- secrets: <none introduced | where checked>

## Verdict
READY | NOT READY
<one line: the single most important thing the next turn must know>
```

The `Verdict` must match reality: `READY` only when every applicable phase
PASSed. If anything FAILED or ERRORed, the verdict is `NOT READY` and the
next line says exactly what to fix. Do not soften this — the arena's
`VERIFICATION_FAILURE.log` and this report are the same honesty contract from
opposite ends.

## Red Flags

- Writing the report from a previous turn's commands, or from memory.
- Marking a phase `PASS` because "there is nothing to check".
- A `READY` verdict with any non-PASS row.
- Deleting `VERIFICATION_FAILURE.log` / `VERIFICATION_NOTE.log` — the harness
  writes those when it fails a turn; the next turn must fix what they say.
- Committing with a stale report (report written before your last edit).
