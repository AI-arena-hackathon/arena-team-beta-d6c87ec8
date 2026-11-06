---
name: ui-verify
description: Verifies a built web UI in a headless browser with Playwright. Use when this turn built, changed, or extended anything with a user interface, or when a test needs to prove a page actually renders and works. The browser only reaches localhost — it exists to verify your own build, nothing else.
---

# UI Verification with Playwright

## Overview

A test suite proves logic; the browser proves the page. This turn has a
Playwright MCP server available (`browser_navigate`, `browser_snapshot`,
`browser_click`, `browser_type`, `browser_take_screenshot`). Use it to verify
that what you built actually renders and that the primary flow works — then
fix what you find before finishing. The model is text-only: you interact with
the page through its **accessibility tree** (snapshots), not screenshots.

## When to Use

- The product has any UI surface (HTML page, SPA, served API docs, admin page)
- You changed markup, styles, routing, or any code a page depends on
- A bug report mentions "blank page", "button does nothing", or "nothing loads"

## Steps

1. **Serve the build.** Start the app exactly as the repo declares it
   (package.json scripts — e.g. `npm run dev`, `npm run start`, or
   `python3 -m http.server 8080` for static output). Run it in the background:
   `nohup <command> > /tmp/server.log 2>&1 &`, then wait ~2s and check the log
   for a listen/ready line. If a port is taken, pick another and use it
   consistently. Only localhost matters — no external services are reachable.
2. **Navigate and snapshot.** `browser_navigate` to `http://127.0.0.1:<port>`
   (localhost is bypassed by the sandbox proxy). Then `browser_snapshot` and
   confirm the expected UI is present — heading, key text, controls. An empty
   or error page is a build failure: fix it.
3. **Exercise the primary flow.** Click buttons, type into inputs, follow the
   main interaction the idea promises. After each step, `browser_snapshot`
   again (refs go stale after any navigation or render). Assert the state you
   expected: navigation happened, output appeared, errors did not.
4. **Fix what you find.** Every discrepancy is a bug in your code, not in the
   browser. Fix, restart the server if the change needs it, re-verify.
5. **Screenshot the result.** `browser_take_screenshot` with **no filename
   argument** — the file lands in `/tmp/playwright-artifacts`, outside the
   repo. It is for the human and the archive, not for you to read (text-only
   model). Do not commit screenshots into the repo. (Verified: an explicit
   `filename` argument instead writes next to the working directory — inside
   the repo — so leave it out unless you intend to commit the proof.)
6. **Stop the server.** Kill the background process before finishing so the
   turn leaves no stray processes.

## Flaky-Failure Triage (adapted from `affaan-m/ECC` `skills/e2e-testing`, MIT)

Browser failures are usually one of four things. Identify which before
"fixing" anything, because three of the four are not product bugs:

| Symptom | Likely cause | Do this |
|---|---|---|
| Fails ~always in the browser, passes headless | Timing: assertion ran before render/settle | Wait for the specific element/state, not a fixed sleep; re-snapshot and assert |
| Fails once, passes on re-run | Genuine flake | Re-run the exact step 2–3 times. If it passes, note it in the commit message as flaky and add a wait, not a retry loop |
| Fails only at one viewport | Responsive/CSS | Reproduce at that width; fix the layout, do not special-case the test |
| Fails on a state you just changed | Real bug | Fix the code; the discrepancy is yours, not the browser's |

Do not paper over a deterministic failure with retries or `waitForTimeout` —
that converts a bug into a flake and hides it from every future turn.

## Rules

- Never navigate anywhere except `127.0.0.1` / `localhost` — everything else
  is blocked anyway; do not waste turns trying.
- Prefer the accessibility tree: snapshots, clicks, typed text. Screenshots
  are evidence, not input.
- If the Playwright tools are unavailable or the browser fails to launch,
  fall back to a `curl` smoke check of the served page plus the repo's tests,
  and say so in the commit message — a missing browser is not an excuse to
  skip verification entirely.
