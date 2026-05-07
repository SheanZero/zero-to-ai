# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

`zero-to-ai` is **not** a runtime application — it is the source workspace where Claude Code / Codex **skills** are designed and authored. The deliverables are skill folders that get installed into other projects (Columns, Vaults, etc.) to power workflows there.

There is no top-level package manager, no build, and no test harness. Each skill is a self-contained folder consumed by Claude Code's `Skill` tool.

Do **not** run `/szw-init` (or any other `szw-*` skill) inside this repo to manage it as a writing column. The repo authors those skills; it is not itself a column.

## Top-level layout

| Path | Role |
|---|---|
| `skills/basic/` | Meta-skills for authoring skills: `new-skills`, `update-skills`. `update-skills/scripts/` contains the validators used across the repo. |
| `skills/write/` | The `szw-*` family — a coordinated 16+ skill ecosystem for technical-column writing (init / discuss / research / outline / write / review / publish / wiki). Each folder is `SKILL.md` + optional `scripts/`, `templates/`, `references/`. |
| `study/` | Design documents. **`fan.md` is the canonical spec** (26-command inventory, article status machine, directory layout); `fan-llm-wiki-extension.md` covers the wiki layer; `article-pipeline-guide.md` is the pipeline deep-dive. Read these before changing pipeline semantics. |
| `work/` | Live working artifacts. **`HANDOFF.md` is the current-state document** — open it first to recover context after a clear. `PLAN-*.md` files are in-flight skill plans; `REVIEW-*.md` are audit reports. |
| `write-progress/` | Earlier proposal docs (ADR rationale, EDITORIAL_CONTEXT draft, flow). Largely superseded by `study/fan.md` — keep for historical context, don't treat as authoritative. |

## How szw-* skills are structured

The `szw-*` pipeline skills share a strict shape; preserve it when editing or adding new ones:

- **`SKILL.md`** with frontmatter `name` + `description` (must contain a `Use when ...` trigger) and an explicit "When to use / When not to use" section. Validators enforce this.
- **Two-script Phase pattern** (most pipeline skills):
  - `scripts/prepare-<verb>.py` — Phase 0: read state, parse upstream artifacts, emit JSON context to stdout.
  - `scripts/finalize-<verb>.py` — Phase 3: read JSON from stdin, render artifacts, advance `STATE.md` / `ARTICLE.md`, gate on verdict. Subcommands like `commit` / `abort` are common.
- **Templates in `templates/`**, references in `references/`, longer flows split out per the progressive-disclosure rule in `skills/basic/new-skills/SKILL.md`.
- **All Python scripts target `python3` with stdlib only** (no `requirements.txt` anywhere). Don't introduce third-party deps without strong reason.
- **Exit codes are part of the contract** (e.g. `create-skeleton.sh` uses 1/2/3 for arg/overwrite/permission errors). Read the existing script's exit-code table before adding new failure modes.

The pipeline orchestrates around two state files inside a target Column:

- `.zero/STATE.md` — Active Articles table + Recently Completed; the routing source of truth.
- `<column>/articles/<slug>/ARTICLE.md` — per-article frontmatter with the 11-value status enum (`created` → `brief_done` → `research_done` → `outline_done` → `draft_done` → `review_failed`/`review_passed` → `published` → `completed`/`archived`/`paused`).

If you change either schema, update **all** consumers — `parse-state.py`, every `prepare-*.py`/`finalize-*.py`, and `references/*-schema.md`. The handoff document tracks which skills are downstream consumers.

## Common commands

Validate a skill folder you've just edited:

```bash
python3 skills/basic/update-skills/scripts/quick_validate_skill.py <path-to-skill-folder>
```

Validate a trigger-eval JSON file:

```bash
python3 skills/basic/update-skills/scripts/validate_trigger_evals.py <path>/evals/trigger-evals.json
```

Run the column-skeleton bootstrap (only meaningful inside a *target* Column directory, never this repo):

```bash
bash skills/write/szw-init/scripts/create-skeleton.sh [target_dir]
```

There are no project-wide test, lint, or build commands. Run skill scripts directly with `python3` against synthetic Column directories under `/tmp/` when sanity-checking behavior.

## Working conventions

- **Read `work/HANDOFF.md` first** when picking up work — it tracks which `szw-*` skills are done, which are next, and which design decisions have been locked.
- **`study/fan.md` is authoritative for command names, status enum, and directory layout.** When `fan.md` and an older doc disagree, fan.md wins.
- Skill descriptions follow the `[capability]. Use when [contexts]` pattern enforced by `quick_validate_skill.py` — keep the `Use when` trigger phrase or the validator will flag it.
- Skill names are kebab-case; the `szw-` prefix is the namespace for the writing-pipeline ecosystem and should not be reused for unrelated skills.
- Default response language for content in `study/`, `work/`, and `SKILL.md` files is Chinese with English technical terms preserved (paths, command names, frontmatter keys). Match the surrounding file when editing.
