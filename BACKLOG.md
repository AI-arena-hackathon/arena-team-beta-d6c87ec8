# Backlog

<!-- IDEA: Replace this line with a one-line summary of what this product is
(e.g. "A habit tracker with streak reminders"). The README.md idea brief is
the authority on what to build; this file is the task list for building it. -->

Tasks are worked top-down by the build agent, one per turn where possible.
Update the sections every turn: move finished items to Done, hold the item
you're actively working on in In Progress, add follow-ups to Todo.

## Done

- [x] Initial scaffold seeded by the arena (AGENTS.md, BACKLOG.md, .gitignore, .env.example, .github/workflows/ci.yml)

## In Progress

- (empty — the next build turn picks the top open task in Todo)

## Todo

- [ ] Replace the `<!-- IDEA: ... -->` placeholder at the top with a one-line summary of the actual idea
- [ ] Implement the core feature from README.md — the smallest real version that works
- [ ] Add a health endpoint (e.g. `GET /health` returning `{"status":"ok"}`) that proves the app runs
- [ ] Add tests covering the core feature and the health endpoint
- [ ] Make README.md reproduce how to run the project (commands + env vars, per .env.example)
- [ ] Keep `.github/workflows/ci.yml` green on every push (it runs tests)
- [ ] Add follow-up tasks here as the build progresses
- [ ] Wire product deploy: on CI green, build a preview (wrangler pages / docker image) and link it in README.md so judges can curl live product, not just repo
