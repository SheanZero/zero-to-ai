EDITORIAL_CONTEXT.md 建议你把它当成技术专栏的“世界观 + 术语表 + 写作宪法”，不是普通风格指南。

它的作用不是直接发布，而是给 Claude / Codex / skills 看，让它们每次写文章时保持同一套判断体系。

你的定位是：

技术行业分析 + 给程序员的建议

所以 EDITORIAL_CONTEXT.md 不应该只写“语言要清晰、不要 AI 腔”，而应该沉淀这几类东西：

1. 这个专栏写什么
2. 不写什么
3. 常用术语怎么定义
4. 观点边界是什么
5. 文章结构偏好
6. 程序员建议的标准
7. 事实与推论怎么区分
8. 哪些表达是禁用的

⸻

一、它应该解决什么问题？

你之后会反复写这些主题：

AI Agent
Claude Code
Codex
GSD
Skills
MCP
AGENTS.md
Context Engineering
Agentic Coding
程序员能力变化
技术管理者工作流变化
AI 编程工具生态

这些词如果每篇文章都重新定义，很容易漂。

比如：

“AI 编程”到底是让 AI 写代码，还是 agentic coding 工作流？
“会用 AI”到底是会写 prompt，还是会拆任务、组织上下文、验证结果？
“程序员被替代”到底是岗位消失，还是工作内容被重组？
“Skills”到底是 prompt 模板、插件，还是可复用工作流单元？

EDITORIAL_CONTEXT.md 就是用来把这些长期判断固定下来。

⸻

二、建议文件结构

我建议你第一版这样写：

# EDITORIAL_CONTEXT.md
## 1. Column Positioning
## 2. Audience
## 3. Editorial Principles
## 4. Canonical Terms
## 5. Topic Boundaries
## 6. Article Types
## 7. Argument Standards
## 8. Programmer Advice Standards
## 9. Evidence Standards
## 10. Style Guide
## 11. Banned Patterns
## 12. Reusable Frames
## 13. Open Questions

这比普通 STYLE_GUIDE.md 更适合你，因为你不是单纯统一文风，而是在建立一个长期技术观察框架。

⸻

三、我建议你可以直接这样起草

下面是一版可以直接放进项目里的初稿。

# EDITORIAL_CONTEXT.md
This document defines the editorial context for a technical column focused on industry analysis and practical advice for programmers.
It is not a public-facing article. It is used by AI agents, writing skills, and human editors to maintain consistent terminology, judgment standards, and writing style across articles.
---
## 1. Column Positioning
This column explains technical industry changes and translates them into practical advice for programmers.
The column is not a news digest, benchmark tracker, tutorial site, or generic AI commentary feed.
Core positioning:
> Help programmers understand how technology changes reshape tools, workflows, skills, and career choices.
The column should answer four questions:
1. What changed?
2. Why does it matter?
3. What is the structural reason behind it?
4. What should programmers do differently?
---
## 2. Audience
Primary audience:
- Practicing programmers
- Independent developers
- Technical leads
- Engineering managers
- AI tool users who care about real workflows, not hype
The reader is assumed to understand basic software development concepts, but should not be assumed to know every new AI tool, model, agent framework, or vendor-specific term.
The reader values:
- Clear judgment
- Practical advice
- Technical credibility
- Honest uncertainty
- Examples from real developer workflows
The reader dislikes:
- Empty AI hype
- Career anxiety farming
- Overconfident predictions
- Tool worship
- Benchmark dumping
- Vague advice like “learn AI” or “improve productivity”
---
## 3. Editorial Principles
### Principle 1: Do not just report news. Explain structure.
Bad:
> Claude Code released a new feature. Here is what it does.
Better:
> Claude Code's new feature shows that AI coding tools are moving from chat-based assistance toward workflow-level delegation.
### Principle 2: Every industry judgment should lead to programmer implications.
If an article says a tool, model, protocol, or workflow matters, it must explain what changes for programmers.
### Principle 3: Separate facts, interpretations, opinions, and predictions.
Use clear wording:
- Fact: what is documented, released, measured, or observable.
- Interpretation: what the fact likely means.
- Opinion: the author's judgment.
- Prediction: what may happen later, with uncertainty.
- Advice: what programmers should do now.
### Principle 4: Avoid fake certainty.
Do not write early signals as inevitable outcomes.
Bad:
> AI agents will replace junior programmers.
Better:
> AI agents may reduce some routine junior tasks, but they also increase the value of task decomposition, review, debugging, and product understanding.
### Principle 5: Prefer workflow analysis over model worship.
The column cares less about which model is “stronger” in the abstract, and more about how tools change real development workflows.
---
## 4. Canonical Terms
### AI Agent
A software-embedded AI system that can pursue a goal over multiple steps, use tools, manage context, and produce or modify artifacts.
Avoid using “AI Agent” to mean any chatbot or automation script.
### Agentic Coding
A development workflow where AI agents participate in task clarification, code modification, test execution, review, debugging, and iteration.
Agentic Coding is broader than “AI writes code.”
### AI Coding Tool
A tool that helps developers write, understand, modify, test, review, or ship software using AI.
Examples may include Claude Code, Codex, Cursor, Windsurf, Devin, etc.
### Context Engineering
The practice of designing, curating, compressing, and updating the information an AI agent needs to perform a task well.
Context Engineering includes but is not limited to prompt writing.
### Prompt Engineering
Writing instructions to influence model behavior.
Prompt Engineering is narrower than Context Engineering.
### Skill
A reusable unit of agent capability. It may include instructions, checklists, workflows, references, scripts, examples, and conventions.
A skill is not just a prompt template.
### GSD
A heavier workflow system for structured task planning, execution, and verification.
Use GSD mainly for engineering project execution, not lightweight writing workflows.
### AGENTS.md
A project-level or global instruction file that tells coding agents how to behave in a repository or workspace.
It is useful for persistent conventions, project structure, build commands, testing rules, and workflow agreements.
### MCP
A protocol or integration layer that allows AI systems to access external tools, data sources, and services.
Do not describe MCP as magic. Explain the concrete tool or data access it enables.
### Vibe Coding
A loose term for coding with AI through high-level intent and iterative feedback.
Use with caution. It is often imprecise.
Preferred alternatives:
- AI-assisted development
- Agentic coding
- AI-mediated prototyping
- Intent-driven coding
---
## 5. Terms to Avoid or Use Carefully
### “AI will replace programmers”
Use only when discussing the phrase critically.
Prefer:
- AI will reshape developer workflows.
- Some routine programming tasks may be automated.
- The value distribution inside software engineering may change.
### “Programmers must learn AI”
Too vague.
Prefer specifying concrete abilities:
- Task decomposition
- Context organization
- Technical review
- Tool orchestration
- Debugging AI-generated code
- Writing better specs
- Evaluating tradeoffs
### “The best AI tool”
Avoid unless the comparison criteria are explicit.
Prefer:
- Better for large refactors
- Better for terminal-driven debugging
- Better for writing
- Better for review
- Better for product prototyping
### “Latest”
Avoid unless verified with current sources.
Prefer exact dates or version numbers.
### “Obviously / Clearly / Everyone knows”
Avoid. These weaken technical credibility.
---
## 6. Topic Boundaries
### In Scope
- AI coding tools
- Agentic workflows
- Developer productivity
- Programmer skill changes
- Engineering management under AI
- Tool ecosystems
- Model-tool interaction
- Technical product strategy
- Open-source developer tools
- Software development methodology
- Writing workflows for technical creators
### Out of Scope
- Pure model benchmark reposting
- General AI news without developer implications
- Crypto-style hype narratives
- Career anxiety farming
- Low-quality tool listicles
- Unverified rumors
- Motivational writing without concrete action
- “One weird trick” productivity advice
---
## 7. Article Types
### Industry Analysis
Purpose:
Explain a technical industry change and its structural meaning.
Standard structure:
1. Surface event
2. Deeper shift
3. Why it matters
4. Who benefits
5. Who is pressured
6. Programmer implications
7. Actionable advice
### Programmer Advice
Purpose:
Translate industry changes into specific actions for programmers.
Standard structure:
1. Misunderstanding
2. Reality
3. Concrete scenarios
4. Skills that rise in value
5. Skills that decline in value
6. What to do now
7. What not to waste time on
### Product Analysis
Purpose:
Analyze a tool, platform, or product direction.
Standard structure:
1. What the product does
2. What problem it is really solving
3. Who it is for
4. What workflow it changes
5. Where it is strong
6. Where it is weak
7. What programmers should learn from it
### Technical Blog
Purpose:
Explain a technical concept, method, or workflow with clarity and practical usefulness.
Standard structure:
1. Problem
2. Concept
3. Example
4. Workflow
5. Mistakes
6. Practical checklist
---
## 8. Argument Standards
Every major article should have:
- One clear thesis
- 3–5 supporting claims
- Evidence for important claims
- At least one counterargument
- A programmer-facing takeaway
- Clear distinction between observation and prediction
Each section should answer:
1. What is the claim?
2. Why should the reader believe it?
3. What does it change for programmers?
Avoid sections that only summarize background without advancing the argument.
---
## 9. Programmer Advice Standards
Advice must be concrete.
Bad:
> Programmers should improve their AI literacy.
Better:
> Programmers should learn to write task specs that include goal, constraints, expected behavior, edge cases, test commands, and definition of done.
Good programmer advice should include:
- A specific behavior
- A reason
- A realistic example
- A warning about misuse
- A next step
Every advice article should include:
- What to do now
- What to stop doing
- What to watch
- What not to overreact to
---
## 10. Evidence Standards
Preferred sources:
1. Official documentation
2. Source code or release notes
3. Primary announcements
4. Research papers
5. Reputable technical analysis
6. Real usage examples
7. Community feedback, clearly labeled as anecdotal
Risky sources:
- Vendor marketing pages
- Social media claims
- Single-user anecdotes
- Unsourced benchmark screenshots
- Outdated documentation
- Rumors
Rules:
- Do not invent dates, numbers, quotes, benchmarks, or user claims.
- Mark unsupported claims as SOURCE_NEEDED.
- If evidence is weak, downgrade the wording.
- If relying on personal judgment, label it as interpretation or opinion.
- If making a prediction, include uncertainty.
---
## 11. Style Guide
Tone:
- Clear
- Opinionated
- Technically credible
- Practical
- Not sensational
- Not overly academic
- Not corporate
Preferred style:
- Use concrete examples.
- Use short paragraphs.
- Explain technical terms in plain language.
- Start with conflict, misunderstanding, or observable change.
- End with a clear judgment or action.
Avoid:
- Long abstract openings
- Empty trend language
- Excessive bullet lists
- AI-generated symmetry
- Over-polished corporate tone
- Repetitive “not X, but Y” patterns
Opening style:
Bad:
> With the rapid development of artificial intelligence, software development is undergoing unprecedented changes.
Better:
> The biggest change in AI coding tools is not that they can write more code. It is that they are starting to take over parts of the development workflow that used to require human coordination.
---
## 12. Banned Patterns
Avoid these patterns unless used intentionally and sparingly:
- “随着 AI 的快速发展……”
- “在当今时代……”
- “值得注意的是……”
- “显而易见……”
- “未来已来……”
- “程序员都要被淘汰了……”
- “只要学会 prompt 就够了……”
- “XX 是程序员的终极答案……”
- “这将彻底颠覆整个行业……”
---
## 13. Reusable Frames
### Frame: Tool Feature → Workflow Shift
Use when analyzing new AI tool features.
Structure:
1. What feature appeared?
2. What workflow does it automate or reshape?
3. What human responsibility remains?
4. What skill becomes more important?
### Frame: Hype → Reality → Action
Use for programmer advice.
Structure:
1. What is the hype?
2. What is actually happening?
3. What should programmers do?
### Frame: Capability → Constraint → Strategy
Use for product analysis.
Structure:
1. What can the tool do?
2. Where does it fail?
3. How should users work with it?
### Frame: Signal → Trend → Uncertainty
Use for industry analysis.
Structure:
1. What is the signal?
2. What trend may it indicate?
3. What uncertainty remains?
---
## 14. Open Questions
Maintain unresolved questions here.
Examples:
- Will skills become a cross-tool standard or remain vendor-specific?
- Will AGENTS.md-like project instructions become common in all AI coding tools?
- Will junior developer work disappear, or will it shift toward review and orchestration?
- Will AI coding tools converge into IDEs, CLIs, cloud agents, or hybrid systems?

⸻

四、你还可以加一个中文版写作偏好区

因为你主要写中文技术公众号 / 技术博客，我建议再加一个中文段落。

---
## 15. Chinese Writing Preferences
中文文章要避免两种问题：
1. 太像英文技术文直译
2. 太像公众号情绪文
理想风格：
- 有观点，但不煽动
- 有判断，但不装神
- 有例子，但不水
- 有技术细节，但不堆术语
- 对程序员友好，不制造廉价焦虑
常用表达偏好：
- “这件事真正改变的不是 X，而是 Y。”
- “对程序员来说，问题不是要不要用 AI，而是如何把任务拆到 AI 能执行、人能验收。”
- “工具变强以后，人的价值不会自动消失，但会从执行代码迁移到定义问题、组织上下文和判断结果。”
- “不要把这个变化理解成模型能力竞赛，它更像是一场开发工作流的重组。”
避免表达：
- “全面颠覆”
- “彻底取代”
- “普通程序员没机会了”
- “不会 AI 就会被淘汰”
- “XX 才是唯一答案”

⸻

五、我建议你把它和 skills 的关系设计清楚

EDITORIAL_CONTEXT.md 不应该替代 skills。

它们的关系是：

文件 / Skill	作用
EDITORIAL_CONTEXT.md	长期世界观、术语、边界
topic-grill	拷问单篇选题
industry-brief	生成单篇文章 brief
evidence-research	查证据
claim-diagnose	诊断判断是否站得住
section-slicer	拆文章结构
human-editor	二稿润色
platform-packager	平台包装

也就是说：

EDITORIAL_CONTEXT.md = 专栏宪法
skills = 具体工种
article draft = 单次产出

⸻

六、维护规则很重要

建议你在文件顶部加一段维护规则：

## Maintenance Rules
Update this file when:
- A recurring term becomes ambiguous.
- A new article introduces a reusable concept.
- A writing mistake appears repeatedly.
- A content strategy decision should affect future articles.
- A term should be deprecated or replaced.
Do not update this file for:
- One-off article details
- Temporary news
- Single-use examples
- Draft-specific wording

这样可以避免它变成垃圾桶。

⸻

七、和 ADR 怎么分工？

EDITORIAL_CONTEXT.md 适合放当前有效的规则。
editorial-adr/ 适合放为什么做了这个决定。

比如：

EDITORIAL_CONTEXT.md 里写：

We do not publish pure benchmark reposts.

ADR 里写：

# 0001 - 不做纯模型跑分搬运
## Context
模型 benchmark 更新太快，容易产生低价值内容。
## Decision
我们只在 benchmark 能支撑工作流分析或程序员建议时引用它。
## Consequence
文章会少一些热点流量，但更有长期价值。

简单说：

EDITORIAL_CONTEXT.md：现在我们怎么做
ADR：当初为什么这么决定

⸻

八、最小版本不用太长

如果你觉得上面太长，第一版可以只保留 7 个部分：

# EDITORIAL_CONTEXT.md
## 1. Column Positioning
## 2. Audience
## 3. Canonical Terms
## 4. Topic Boundaries
## 5. Argument Standards
## 6. Programmer Advice Standards
## 7. Style Guide

后面写文章时，再逐步补。

⸻

九、我最建议你先写进去的 5 条核心规则

这五条是你的专栏底盘：

1. 本专栏不做 AI 新闻搬运，而是解释技术变化背后的工作流变化。
2. 每篇文章都必须回答：这件事对程序员意味着什么？
3. 所有重要判断必须区分事实、推论、观点和预测。
4. 不制造“程序员被 AI 淘汰”的廉价焦虑；重点分析能力结构变化。
5. 给程序员的建议必须具体到行为，而不是停留在“学习 AI”“提高效率”这种空话。

有了这五条，你的文章就不会轻易跑偏。