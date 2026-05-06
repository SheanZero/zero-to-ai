# Script Borrowing Guide

Use scripts to remove repeated deterministic work from skill iteration. Do not script taste, judgment, style, or strategy.

## What to borrow from heavier skill-creator workflows

Heavy skill-creator systems often include scripts for:

- quick validation
- eval running
- benchmark aggregation
- description optimization
- packaging
- report generation

For personal writing and analysis skills, start with only:

1. quick skill validation
2. trigger eval file validation

Add full eval runners or benchmark aggregation only after the skill is high-frequency, shared across a team, or repeatedly failing in measurable ways.

## Good writing-skill scripts

- Validate `SKILL.md` frontmatter.
- Check description length and `Use when` trigger phrasing.
- Check required output sections.
- Validate `evals/trigger-evals.json`.
- Scan drafts for `SOURCE_NEEDED` or risky absolute wording.
- Check Markdown heading hierarchy.

## Bad writing-skill scripts

- Decide whether an essay is insightful.
- Decide whether a metaphor is good.
- Decide final editorial taste.
- Auto-rewrite nuanced claims without human/model judgment.

## When a script is justified

Add a script if at least two of these are true:

- The same check appears in many skill updates.
- The check is deterministic.
- The check has clear pass/fail or warning states.
- A script will reduce token use or prevent accidental omissions.
- Manual checking is annoying or error-prone.
