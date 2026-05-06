---
name: update-skills
description: Improve existing agent skills by diagnosing failures, tightening instructions, optimizing trigger descriptions, adding references, scripts, trigger tests, and lightweight evals. Use when the user wants to revise, debug, benchmark, iterate, optimize, validate, package, or compare an existing Claude Code, Codex, or general agent skill, especially when a skill undertriggers, overtriggers, produces unstable outputs, or needs to become production-ready.
---

# Update Skills

Improve an existing skill through diagnosis, targeted revision, lightweight validation, and optional evaluation.

Use this skill when a skill already exists and the user wants it to trigger better, produce better outputs, become more reliable, or evolve from a rough v0 into a durable workflow asset.

## Core principles

- Diagnose before rewriting.
- Preserve what already works.
- Improve the smallest effective surface area.
- Do not overfit to one failure case.
- Prefer explaining why a behavior matters over adding rigid all-caps rules.
- Keep the skill lean; remove instructions that are not pulling their weight.
- Add scripts only when repeated deterministic work appears across cases.
- Borrow script patterns from heavier skill-creation systems, but do not copy a heavy eval harness unless the skill is high-value, high-frequency, or shared across a team.
- Use evals for objective or structural skills; use qualitative review for subjective writing or style skills.

## Workflow

### 1. Capture the current state

Inspect or ask for:

- Current `SKILL.md`.
- Optional references, examples, scripts, assets, or eval files.
- What went wrong.
- Examples of failed prompts.
- Examples of good outputs.
- Whether the problem is triggering, output quality, stability, scope, or maintainability.

Classify the issue:

```text
triggering     = skill does not load when needed, or loads when it should not
instruction    = skill loads but follows the wrong process
output         = output format, depth, tone, or completeness is wrong
coverage       = skill misses important cases or edge cases
overreach      = skill tries to do too much
maintenance    = skill is too long, duplicated, stale, or hard to update
resources      = needs references, examples, assets, scripts, or eval files
```

### 2. Diagnose failure modes

Produce a short diagnosis before editing.

Use this template:

```md
# Skill Diagnosis

## Current purpose
[What the skill is trying to do]

## Observed failures
- [Failure 1]
- [Failure 2]

## Likely causes
- Trigger description issue
- Missing input-gathering step
- Vague output format
- Overloaded scope
- Missing examples
- Missing references
- Repeated deterministic work should be scripted
- Missing evals or trigger tests

## Recommended changes
- [Change 1]
- [Change 2]
- [Change 3]
```

### 3. Improve the trigger description

The frontmatter description is the main trigger mechanism. Improve it when the skill undertriggers or overtriggers.

A good description has:

- What the skill does.
- Specific contexts where it should trigger.
- Common user phrases or task types.
- Near-boundary clarity when it should not be used.

Before:

```md
description: Helps review articles.
```

After:

```md
description: Reviews technical articles for unsupported claims, overgeneralized industry analysis, missing counterarguments, and weak programmer advice. Use when editing technical blogs, product analysis, programmer advice essays, or industry commentary where factual credibility and argument strength matter.
```

### 4. Tighten the body

Improve the body in this order:

1. Clarify when to use and not use.
2. Clarify inputs to gather.
3. Clarify the workflow.
4. Clarify the output format.
5. Add examples for ambiguous behavior.
6. Move rare or long content into references.
7. Add scripts for deterministic repeated work.
8. Add eval or trigger files for repeatable checks.
9. Remove redundant or stale instructions.

Avoid making the skill a giant prompt. If it tries to do multiple jobs, split it into separate skills.

### 5. Add or improve examples

Examples should cover:

- A typical successful use case.
- A tricky edge case.
- A near-miss that should not trigger or should be handled differently.

For subjective writing skills, examples often matter more than strict assertions.

### 6. Decide whether evals are needed

Use evals when the skill has objective or structural success criteria.

Good eval candidates:

- Extracting claims.
- Producing fixed report sections.
- Validating file structure.
- Checking for required fields.
- Formatting output.
- Trigger classification.

Poor eval candidates:

- “Make it more elegant.”
- “Sound more human.”
- “Be more insightful.”

For subjective skills, use qualitative review criteria instead.

### 7. Create lightweight eval prompts

If evals are useful, create 3–5 realistic prompts.

Each eval should include:

```json
{
  "id": "descriptive-id",
  "prompt": "Realistic user task",
  "expected_output": "What a good result should include",
  "assertions": [
    "Includes required section X",
    "Marks unsupported claims as SOURCE_NEEDED",
    "Does not rewrite the whole article when asked only to diagnose"
  ]
}
```

For improved rigor, compare:

- old skill vs new skill, or
- with skill vs no skill.

Do not overbuild the eval system unless the skill is high-value, high-frequency, or shared across a team.

### 8. Optimize triggering with near-miss tests

When trigger behavior matters, create 12–20 trigger queries:

- 6–10 should-trigger queries.
- 6–10 should-not-trigger queries.

Use realistic prompts with messy wording, context, typos, abbreviations, and near-boundary cases.

Example:

```json
[
  {
    "query": "can you turn my messy article review checklist into a reusable skill for claude code?",
    "should_trigger": true
  },
  {
    "query": "can you review this article and make it less AI sounding?",
    "should_trigger": false
  }
]
```

Revise the description based on failures. Prefer improving specificity over adding broad keywords.

### 9. Borrow script patterns selectively

Do not blindly copy a full skill-creator script stack into every skill. Instead, decide which script layer is justified.

Use this decision matrix:

| Need | Add now? | Suggested implementation |
|---|---:|---|
| Validate `SKILL.md` exists, frontmatter is valid, description has `Use when`, name is kebab-case | Yes for most durable skills | `scripts/quick_validate_skill.py` |
| Validate trigger eval JSON shape and should-trigger / should-not-trigger balance | Yes when trigger issues matter | `scripts/validate_trigger_evals.py` |
| Run with-skill vs old-skill comparisons | Only for high-value skills | Manual subagent comparison or a project-specific eval runner |
| Aggregate benchmark pass rates, token use, timing | Usually no for personal writing skills | Add only if repeatedly benchmarking multiple skills |
| Auto-improve descriptions through a multi-iteration loop | Usually no | Use trigger tests first; add automation only after repeated trigger failures |
| Package a skill for distribution | Only when sharing | Add a packaging script later |

Script candidates for writing and analysis skills:

- Markdown heading and required-section validation.
- Frontmatter validation.
- Trigger eval JSON validation.
- `SOURCE_NEEDED` scanning.
- Risk-word scanning: “latest”, “obviously”, “everyone”, “will definitely”, “industry standard”.
- Claim extraction scaffolds.
- File tree validation.

Do not script subjective judgment such as “more insightful”, “more human”, or “better taste”.

### 10. Use bundled validation scripts when available

If this skill folder includes scripts, use them when updating a skill directory.

Typical commands:

```bash
python scripts/quick_validate_skill.py /path/to/skill
python scripts/validate_trigger_evals.py /path/to/skill/evals/trigger-evals.json
```

Run validation after editing when files are available. If the environment cannot run scripts, still apply the same checks manually.

### 11. Present the revision

Return:

1. Diagnosis.
2. Summary of changes.
3. Updated `SKILL.md`.
4. Optional updated references/scripts/eval files.
5. Suggested eval prompts or trigger tests.
6. Before/after description comparison.
7. Validation results or manual validation notes.
8. Remaining risks.

## Revision checklist

Before finalizing, verify:

- [ ] The original purpose is preserved or intentionally narrowed.
- [ ] The description triggers on real user phrasing.
- [ ] Near-misses are handled.
- [ ] The workflow is clearer than before.
- [ ] The output format is explicit.
- [ ] The skill is not overfitted to one example.
- [ ] Long content is split out.
- [ ] Repeated deterministic work is scripted or flagged for scripting.
- [ ] Validation scripts are added only where they reduce repeated manual checking.
- [ ] Evals are proposed only where useful.
- [ ] The revised skill remains safe and unsurprising.

## Default response format

When updating a skill for the user, respond with:

```text
Updated skill: [skill-name]

Diagnosis:
[short diagnosis]

Changes made:
- [change 1]
- [change 2]
- [change 3]

Before/after description:
Before: ...
After: ...

Updated files:
- SKILL.md
- [optional references/scripts/evals]

Validation:
[script output summary or manual validation]

Suggested evals or trigger tests:
[tests]

Remaining risks:
[short list]
```
