---
name: verification-before-completion
description: Run before finishing any build turn or claiming anything works. Use when you are about to commit, declare a fix complete, or state that tests pass — requires fresh command output as evidence, never assertions from memory. Evidence before claims, always.
---

# Verification Before Completion

Adapted from obra/superpowers `verification-before-completion` (MIT). Stripped of its interactive assumptions (no human partner exists inside a build turn) and mapped onto this arena's own artifacts. The discipline is identical to the project's standing rule: a green status and useful output are different claims needing separate proof.

## The Gate

```
BEFORE claiming any status:

1. IDENTIFY: What command or artifact proves this claim?
2. RUN: Execute it fresh and complete — not from memory of an earlier run
3. READ: Full output, exit code, failure count
4. VERIFY: Does the output confirm the claim?
   - NO:  State the actual status with the evidence
   - YES: State the claim WITH the evidence
5. ONLY THEN: Make the claim
```

## Claim Map for a Build Turn

| Claim | Requires | Not sufficient |
|---|---|---|
| Tests pass | Test command output: 0 failures, run after your last edit | An earlier run, "should pass", linter clean |
| Typecheck clean | `npx tsc --noEmit` exit 0 | Tests passing (different check) |
| Bug fixed | The original symptom reproduced fixed: failing test now passes | Code changed, looks right |
| UI works | Playwright snapshot showing the flow exercised + screenshot in `/tmp/playwright-artifacts` | Server started without errors |
| Turn is complete | `git status`/`git diff` shows the work, `BACKLOG.md` updated | Feeling done |

## Red Flags — Stop

- "Should work now", "probably", "seems to"
- Satisfaction before evidence ("Great!", "Done!")
- About to commit without running the checks since your last edit
- Trusting a previous turn's log instead of re-running
- Re-running a clean command on unchanged code as reassurance (adds nothing — run after edits, not instead of them)
- "Just this once"

## Re-runs and Retries

A command run before your last edit proves nothing about the current tree. After every edit that could affect the result — code, config, dependencies, test files — re-run the affected check. A clean run followed by more edits followed by a commit is an unverified commit.
