---
name: skill-creator
description: Authors a reusable SKILL.md skill into this repo's .arena/skills/ directory. Use when a task pattern is worth repeating in later turns (a project-specific procedure, a house style for tests, a repeated build step) and no existing skill covers it. Prefer using or adapting a baked-in skill before writing a new one.
---

# Skill Creator

## Overview

A skill is a markdown file with YAML frontmatter that teaches a later agent
how to do something this project needs done again. Skills you author here
**persist in the repo** (`.arena/skills/` is committed) — every later turn
checks this directory before working. One good skill beats ten stale notes in
BACKLOG.md.

## When to Use

- A procedure you did this turn will recur (project-specific test patterns,
  a local dev server quirk, a style rule the baked skills don't cover)
- You keep rediscovering the same setup steps across turns
- The repo's CI or verification keeps tripping on the same convention

**When NOT to use:** one-off work (just do it), anything the baked skills
already cover (test-driven-development, code-review-and-quality,
security-and-hardening, debugging-and-error-recovery, ui-verify), or anything
that changes every turn (look in BACKLOG.md instead).

## Steps

1. **Check the catalog first.** Read the baked skills in your context and
   `ls .arena/skills/` if it exists. Duplicating an existing skill is a
   failure; extending one is fine.
2. **Create the file.** `.arena/skills/<short-name>/SKILL.md` — lowercase
   kebab-case name. Frontmatter:

   ```yaml
   ---
   name: <short-name>
   description: <one or two sentences: what it does, when to use it, when not to>
   ---
   ```

3. **Write the body.** Overview (one paragraph), When to Use (specific,
   project-grounded), Steps (numbered, with the exact commands this repo
   needs — commands discovered by running them, not guessed), Rules
   (what not to do). Keep it under 100 lines; a skill that needs an essay
   needs splitting instead.
4. **Make it reproducible.** Every command must be one you actually ran and
   saw work in this repo. If a step is environment-specific (Windows vs
   container), say which one it applies to.
5. **Commit it.** Add the skill file to the same commit as the work it
   documents. Mention it in BACKLOG.md as an item under "Done" so later turns
   see it exists.

## Rules

- No secrets, no absolute paths outside the repo, no credentials — skills are
  committed and shared.
- Markdown only, SKILL.md exactly (capitalization matters).
- Don't document the arena harness (team-build-turn.yml, the Dockerfile,
  opencode.json) — those are re-synced every turn and your edits vanish.
