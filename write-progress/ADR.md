ADR 建议你不要做成“文章选题记录”，而是做成技术专栏的长期内容决策记录。

一句话：

EDITORIAL_CONTEXT.md 记录“现在怎么写”；
ADR 记录“为什么我们决定以后都这么写”。

ADR 不需要很多，但每一条都应该能影响未来很多篇文章。

⸻

一、ADR 在你的技术博客里解决什么问题？

你的博客定位是：

技术行业分析 + 给程序员的建议

这种内容最容易在长期写作中发生几个漂移：

1. 追热点，变成 AI 新闻搬运
2. 写工具评测，变成功能清单
3. 写程序员建议，变成职业焦虑
4. 写行业分析，变成空泛预测
5. 写 AI 编程，变成模型强弱比较
6. 写教程，变成没有观点的操作说明

ADR 就是用来防止这些漂移的。

它记录的是那些以后会反复影响你判断的内容策略决定。

⸻

二、什么值得写成 ADR？

我建议满足这三个条件才写 ADR：

1. 这个决定以后会反复影响文章方向
2. 这个决定有真实取舍，不是显而易见的规则
3. 未来的你或 AI agent 可能会忘记为什么这么做

比如这些就值得写：

不做纯模型 benchmark 搬运
不写“AI 替代程序员”的焦虑流量文
所有工具评测必须落到程序员行动建议
优先分析工作流变化，而不是单点功能
产品分析文必须区分厂商叙事和真实用户价值
公众号版可以更有表达欲，但不能牺牲事实边界

这些不值得写 ADR：

这篇文章标题叫 A 还是 B
这次用哪个例子
这段导语怎么改
今天是否写 Claude Code
某个临时热点要不要跟

⸻

三、推荐目录结构

建议你在博客 repo 里这样放：

tech-column/
  EDITORIAL_CONTEXT.md
  docs/
    editorial-adr/
      0001-no-benchmark-dumping.md
      0002-every-tool-review-needs-programmer-advice.md
      0003-no-ai-career-anxiety-farming.md
      0004-workflow-over-model-worship.md
      0005-separate-fact-interpretation-opinion-prediction.md

命名建议：

0001-no-benchmark-dumping.md
0002-no-career-anxiety-farming.md
0003-tool-review-must-end-with-action.md

不要用中文文件名也可以，英文 slug 更方便 agent 搜索和引用。正文可以中文。

⸻

四、ADR 模板

我建议你用一个很短的模板，不要搞得像公司架构文档。

# 0001 - 不做纯模型跑分搬运
## Status
Accepted
## Date
2026-05-06
## Context
我们会经常写 AI coding tools、模型能力、Claude Code、Codex、Cursor、GSD、Skills 等主题。  
这些主题很容易滑向 benchmark 搬运、模型排名、功能清单。
这类内容短期流量可能高，但更新快、上下文复杂，也容易让文章失去长期价值。
## Decision
本专栏不做纯 benchmark 搬运。
可以引用 benchmark，但必须满足至少一个条件：
1. 用来解释开发工作流变化
2. 用来支撑工具选择建议
3. 用来说明程序员能力结构变化
4. 用来反驳某个流行误解
## Consequences
好处：
- 文章更有长期价值
- 不被模型发布节奏牵着走
- 更符合“行业分析 + 程序员建议”的定位
代价：
- 少追一部分即时热点
- 文章产出速度可能慢一些
- 需要更多判断和资料筛选
## Linked Context
- EDITORIAL_CONTEXT.md: Evidence Standards
- EDITORIAL_CONTEXT.md: Topic Boundaries

⸻

五、我建议你第一批建 8 个 ADR

ADR 0001：不做纯模型跑分搬运

# 0001 - 不做纯模型跑分搬运
## Status
Accepted
## Context
AI 模型 benchmark 更新快，且经常需要复杂上下文才能正确解释。  
如果本专栏只追逐模型排名，会变成低价值信息流。
## Decision
不发布纯 benchmark 搬运文。  
benchmark 只能作为证据，不能作为文章主体。
## Consequences
文章会少一些即时流量，但更有长期判断价值。

⸻

ADR 0002：所有工具评测必须落到程序员行动建议

# 0002 - 工具评测必须落到程序员行动建议
## Status
Accepted
## Context
AI coding tools 的功能变化很快。单纯罗列功能，很快过时。  
读者真正关心的是：这个工具会改变我的工作方式吗？我应该怎么用？
## Decision
所有工具评测必须回答：
1. 它改变了哪个开发环节？
2. 它适合哪类程序员？
3. 它不适合什么场景？
4. 程序员应该调整什么习惯？
5. 有哪些误用风险？
## Consequences
文章不会是单纯产品说明，而会更像工作流分析。

⸻

ADR 0003：不制造“程序员被 AI 淘汰”的廉价焦虑

# 0003 - 不制造程序员职业焦虑
## Status
Accepted
## Context
AI 编程话题容易被写成“程序员要被淘汰”的焦虑叙事。  
这种写法有传播性，但容易牺牲准确性，也不符合本专栏的价值。
## Decision
不把“程序员被淘汰”作为默认叙事。  
优先分析：
1. 哪些任务会被自动化
2. 哪些能力会升值
3. 哪些工作方式会变化
4. 程序员可以采取什么行动
## Consequences
文章会更克制，但也更可信。

⸻

ADR 0004：优先分析工作流变化，而不是单点功能

# 0004 - 优先分析工作流变化
## Status
Accepted
## Context
AI coding tools 经常发布新功能。  
单点功能容易过时，但功能背后的工作流变化更有长期价值。
## Decision
分析工具时，优先回答：
1. 这个功能改变了开发流程中的哪一步？
2. 它把人的职责迁移到了哪里？
3. 它增加了什么新的验证需求？
4. 它让什么能力变得更重要？
## Consequences
文章会少一些功能罗列，多一些结构判断。

⸻

ADR 0005：区分事实、推论、观点和预测

# 0005 - 区分事实、推论、观点和预测
## Status
Accepted
## Context
行业分析文很容易把观察、判断和预测混在一起。  
这会降低技术读者的信任感。
## Decision
所有重要判断必须区分：
- Fact：已有事实
- Interpretation：基于事实的解释
- Opinion：作者观点
- Prediction：未来判断
- Advice：给读者的行动建议
如果证据不足，必须降低表达强度。
## Consequences
文章表达会更谨慎，但可信度更高。

⸻

ADR 0006：产品分析文必须区分厂商叙事和用户价值

# 0006 - 区分厂商叙事和用户价值
## Status
Accepted
## Context
AI 工具厂商经常使用宏大叙事，例如“重新定义开发”“10x productivity”“软件工程自动化”。  
这些叙事不一定等同于真实用户价值。
## Decision
产品分析文必须区分：
1. 厂商说它解决什么问题
2. 用户真实遇到什么问题
3. 工具实际改变了什么流程
4. 哪些价值已经成立
5. 哪些价值仍然只是愿景
## Consequences
文章会更少复述发布稿，更重真实使用场景。

⸻

ADR 0007：公众号版可以更有表达欲，但不能牺牲事实边界

# 0007 - 表达可以锋利，事实必须稳
## Status
Accepted
## Context
公众号文章需要标题、导语、观点和传播感。  
但技术读者对夸大和错误非常敏感。
## Decision
公众号版可以使用更强的表达、更明确的判断和更有钩子的标题。  
但不能：
1. 夸大未经验证的事实
2. 把预测写成现实
3. 把个体体验写成行业趋势
4. 用焦虑替代论证
## Consequences
文章会兼顾传播性和技术可信度。

⸻

ADR 0008：程序员建议必须具体到行为

# 0008 - 程序员建议必须具体到行为
## Status
Accepted
## Context
“学习 AI”“提升效率”“拥抱变化”这类建议没有实际帮助。  
本专栏的读者需要可以执行的下一步。
## Decision
所有程序员建议必须尽量具体到行为。
坏建议：
> 程序员要提升 AI 协作能力。
好建议：
> 写需求时，把目标、约束、边界情况、测试命令和完成标准写清楚，再交给 AI agent 执行。
## Consequences
文章会更实用，也更容易形成读者信任。

⸻

六、ADR 和 EDITORIAL_CONTEXT.md 怎么同步？

建议规则：

ADR 记录决策原因。
EDITORIAL_CONTEXT.md 只保留当前有效规则。

比如 ADR 里写了：

0003 - 不制造程序员职业焦虑

那么 EDITORIAL_CONTEXT.md 里应该同步一条短规则：

## Topic Boundaries
Do not use AI replacement anxiety as the default narrative.  
Prefer analyzing task changes, skill shifts, and actionable adaptation.

不要把整篇 ADR 复制进去。
EDITORIAL_CONTEXT.md 是“宪法正文”，ADR 是“立法记录”。

⸻

七、每次什么时候更新 ADR？

建议你在这几个节点更新：

1. 发现某个选题方向以后会反复出现
2. 某篇文章暴露了长期写作风险
3. 你决定以后不再写某类内容
4. 你决定采用某种固定文章框架
5. 你和 AI agent 对文章方向反复争执
6. 某条规则需要解释“为什么”

例如：

你写了几篇 Claude Code / Codex 对比，发现总是容易写成“谁更强”。
这时就该写 ADR：

0009 - AI coding tool comparison should compare workflows, not abstract model strength

⸻

八、可以新增一个 editorial-adr skill

这个 skill 不需要复杂，作用是帮你判断“要不要写 ADR”。

建议 description：

---
name: editorial-adr
description: Create or update editorial decision records for a technical column. Use when a writing, positioning, terminology, or content strategy decision will affect future articles and needs a durable rationale.
---

核心规则：

# Editorial ADR
Use this skill when a decision is:
1. Hard to reverse
2. Likely to affect future articles
3. Based on a real tradeoff
4. Potentially surprising to future editors or agents
Do not create ADRs for one-off article choices.
## Output
- Suggested ADR title
- Whether this decision deserves an ADR
- ADR draft
- Changes needed in EDITORIAL_CONTEXT.md

⸻

九、建议和你的 skills 工作流结合

你的写作工作流可以这样加 ADR：

/topic-grill
↓
/industry-brief
↓
如果出现长期内容策略问题：
/editorial-adr
↓
/evidence-research
↓
/claim-diagnose
↓
/human-editor

比如你让 Claude 写一篇：

“Claude Code 和 Codex 谁更适合程序员？”

topic-grill 可能发现这个题目容易滑向模型强弱比较。
这时可以触发 ADR：

以后所有 AI coding tool 对比，优先比较 workflow fit，不比较抽象强弱。

这条就值得写成 ADR。

⸻

十、我的最终建议

第一阶段你只需要建这三个东西：

EDITORIAL_CONTEXT.md
docs/editorial-adr/0001-no-benchmark-dumping.md
docs/editorial-adr/0002-every-tool-review-needs-programmer-advice.md

不要一开始写太多 ADR。
ADR 不是规则清单，而是发生过真实取舍之后留下的决策记录。

最重要的三条先立住：

1. 不做 AI 新闻 / benchmark 搬运
2. 工具分析必须落到程序员行动建议
3. 不制造“AI 替代程序员”的廉价焦虑

这三条会直接决定你的技术博客气质。