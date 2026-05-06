---
name: new-skills
description: Create new agent skills from scratch with clear triggers, lean SKILL.md structure, progressive disclosure, examples, and optional scripts or references. Use when the user wants to create, write, design, scaffold, or package a new Claude Code, Codex, or general agent skill, especially when they have a repeatable workflow they want to turn into a reusable skill.
---

# New Skills

Create a new skill from scratch. The goal is to produce a small, composable, reusable skill that captures a repeatable workflow without becoming a heavy framework.

Use this skill to turn a vague workflow, prompt pattern, editorial process, code review routine, research process, or tool workflow into a clean skill folder.

## Core principles

- One skill should do one job well.
- Prefer a short, sharp `SKILL.md` over a large all-in-one manual.
- Put trigger logic in the frontmatter `description`, not buried in the body.
- Use progressive disclosure: keep common instructions in `SKILL.md`; move rare, long, or domain-specific details into references.
- Add scripts only when the operation is deterministic, repetitive, or error-prone.
- Do not overfit to one example. Generalize from the user’s workflow.
- Avoid time-sensitive claims inside the skill unless they are intentionally versioned.

## Workflow

### 1. Capture intent

First infer what you can from the current conversation. Only ask questions that materially affect the skill design.

Resolve:

- What task should this skill enable?
- Who or what agent will use it: Claude Code, Codex, ChatGPT, or generic agent?
- When should it trigger?
- What are the expected inputs?
- What are the expected outputs?
- What should the skill never do?
- Are there examples of good and bad outputs?
- Does it need references, examples, templates, or scripts?
- Is the skill mostly objective, mostly subjective, or mixed?

If the user’s workflow is already clear, proceed without unnecessary questions.

### 2. Decide the skill shape

Choose the lightest structure that works.

Use this default tree:

```text
skill-name/
  SKILL.md
```

Add optional files only when needed:

```text
skill-name/
  SKILL.md
  EXAMPLES.md
  REFERENCES.md
  references/
    domain-a.md
    domain-b.md
  scripts/
    helper.py
```

Split content out of `SKILL.md` when:

- `SKILL.md` would exceed roughly 100–150 lines.
- The skill has rare advanced paths.
- The skill serves multiple domains.
- Examples or reference material would distract from the main workflow.

Add scripts when:

- The same code would be generated repeatedly.
- Validation, formatting, extraction, or conversion can be deterministic.
- Explicit error handling matters.
- A script can reduce token use and improve reliability.

### 3. Name the skill

Use short kebab-case names.

Good:

```text
topic-grill
claim-diagnose
technical-review
platform-packager
```

Avoid vague names:

```text
helper
writer
assistant
workflow
```

### 4. Write the frontmatter

Every `SKILL.md` must start with:

```md
---
name: skill-name
description: [What it does]. Use when [specific triggering contexts, phrases, inputs, or task types].
---
```

Description rules:

- Write in third person.
- First sentence: capability.
- Second sentence: explicit `Use when...` trigger.
- Include likely user phrases and contexts.
- Be slightly assertive so the skill triggers when useful.
- Avoid generic descriptions such as “helps with writing” or “improves documents.”

### 5. Draft the skill body

Use this structure unless there is a strong reason not to:

```md
# Skill Title

Brief purpose statement.

## When to use

- Trigger scenario 1
- Trigger scenario 2
- Trigger scenario 3

## Inputs to gather

- Input 1
- Input 2
- Input 3

## Workflow

### 1. Step name
Instructions.

### 2. Step name
Instructions.

### 3. Step name
Instructions.

## Output format

Use this exact or default template:
...

## Quality checklist

- [ ] Check 1
- [ ] Check 2
- [ ] Check 3
```

For writing, research, review, and strategy skills, prefer clear output templates.
For coding or file transformation skills, include validation steps.

### 6. Add examples

Add 2–3 realistic examples when they help the agent understand boundaries.

Use examples that show:

- A common use case.
- An edge case.
- A near-miss where this skill should not be used.

Keep examples short. Move long examples to `EXAMPLES.md`.

### 7. Suggest lightweight test prompts

For every new skill, propose 2–3 realistic test prompts.

For objective skills, include expected outputs or assertions.
For subjective writing/editorial skills, use qualitative review criteria instead of forced assertions.

Example:

```json
{
  "skill_name": "claim-diagnose",
  "evals": [
    {
      "id": "overstated-industry-claim",
      "prompt": "Review this technical blog draft and identify unsupported claims.",
      "expected_output": "Flags claims by type, evidence needed, risks, and safer rewrites."
    }
  ]
}
```

### 8. Present the result

Return:

1. Recommended folder tree.
2. Complete `SKILL.md`.
3. Optional `EXAMPLES.md`, `REFERENCES.md`, or scripts if needed.
4. 2–3 test prompts.
5. A short review checklist for the user.

Do not over-explain. Give the user copyable files.

## Quality checklist

Before finalizing, verify:

- [ ] The skill name is specific and kebab-case.
- [ ] The description clearly says what the skill does and when to use it.
- [ ] The skill has one primary job.
- [ ] The body is lean and action-oriented.
- [ ] Long or rare content is split into references.
- [ ] Scripts are added only for deterministic repeated work.
- [ ] The output format is explicit.
- [ ] Examples cover common and edge cases.
- [ ] The skill avoids unsupported time-sensitive facts.
- [ ] The skill does not contain surprising, unsafe, or misleading behavior.

## Default response format

When creating a skill for the user, respond with:

```text
Created skill: [skill-name]

Folder tree:
[tree]

SKILL.md:
[full file]

Optional files:
[only if needed]

Test prompts:
[2–3 prompts]

Review notes:
[short checklist]
```
