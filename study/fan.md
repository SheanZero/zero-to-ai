# 写作工作流 Skills 蓝图

> 配套文档：
> - [`gsd-research.md`](./gsd-research.md) —— GSD 65 个 skill 的体系参考
> - [`gsd-workflow-guide.md`](./gsd-workflow-guide.md) —— GSD 使用建议
> - [`writing-workflow-proposal.md`](./writing-workflow-proposal.md) —— 写作工作流总体建议
> - [`../write-progress/{flow,EDITORIAL_CONTEXT,ADR}.md`](../write-progress/) —— 写作流程草稿
>
> 本文目标：给出**全新写作工作流 skills 集合**的具体蓝图，从创建专栏开始，列出每个命令的触发、输入、步骤、产出、衔接、Gates，按 v1.0 → v2.0 → v3.0 分阶段交付。
>
> 编写日期：2026-05-06

---

## TL;DR

1. **命名空间** `/szw-*`（column 缩写，与 `/gsd-*` 平行）。
2. **共 27 个命令**，分 8 类：专栏生命周期 / 文章主流水线 / 轻量出口 / 长期资产 / 进度路由 / 复盘 / 系列 / 配置。
3. **分阶段交付**：v1.0 (12) → v2.0 (8) → v3.0 (7)。先跑通 MVP，再扩展。
4. **持久化双层结构**（按"是否需要用户直接交互"分层）：
   - 显性容器目录（用户起名，默认 `Column/`）—— 写作宪法、决策、术语、证据、灵感、文章过程产物、成品全部上显性层，用户可直接读 / 改 / 获取启发
   - 隐藏 `Column/.zero/` —— 只装纯系统状态（STATE.md 活记忆 / szw-config.json 配置 / .continue-here 暂停 handoff），机器读写为主
5. **6 个子 agent** + 完成 marker 协议（仿 GSD `agent-contracts.md`）。
6. **关键纪律**：写前必拷问（grill），写后必诊断（diagnose），发前必反审（review），发后必复盘（retro）。

---

## 1. 命名规范与设计原则

### 1.1 命名规则

| 项 | 规则 | 示例 |
|---|---|---|
| 命令前缀 | `/szw-*` | `/szw-init`、`/szw-discuss` |
| Skill 目录 | `~/.claude/skills/szw-<name>/SKILL.md` | `szw-discuss/SKILL.md` |
| 子 agent | `<name>-agent`，独立 session | `evidence-researcher` |
| 文件命名 | 阶段产物用 `NN-name.md` 排序 | `01-brief.md`、`02-research.md` |
| ADR 命名 | `NNNN-slug.md`，英文 slug | `0001-no-benchmark-dumping.md` |
| 专栏容器目录 | 用户起名，默认 `Column/`；推荐英文短词 | `Column/`、`AICoding/`、`TechWeekly/` |
| 隐藏系统状态目录 | 容器目录下的 `.zero/`（固定，仅装 STATE.md / szw-config.json / .continue-here） | `Column/.zero/` |

### 1.2 设计原则（沿用 GSD + mattpocock 思想）

1. **薄 wrapper**：每个 SKILL.md 只放触发条件 + 简短指令，详细工作流写在 `~/.szw-system/workflows/<name>.md`（仿 GSD 的 `workflows/`）。
2. **完成 marker 协议**：子 agent 用 H2 标题作为完成信号（仿 GSD `references/agent-contracts.md`）。
3. **可路由不强制**：每个命令既能单独跑，也能被 `/szw-progress --next` 自动串联。
4. **梯度可降级**：每个流水线 skill 都支持 `--quick` 跳过部分子步骤。
5. **artifact 优先**：所有产出都落到 `articles/<slug>/`，主对话只看摘要不看过程。

---

## 2. 命令分类总览（速查）

| 类别 | 数量 | v1.0 | v2.0 | v3.0 |
|---|---|---|---|---|
| 专栏生命周期 | 3 | szw-init | — | szw-stats / szw-summary |
| 创建入口（项目化） | 2 | szw-new-article | szw-new-series | — |
| 文章主流水线 | 7 | szw-discuss / szw-write / szw-publish / szw-complete | szw-research / szw-outline / szw-review | — |
| 轻量出口 | 2 | — | szw-capture / szw-quick | — |
| 长期资产 | 4 | szw-context / szw-adr | — | szw-glossary / szw-evidence-bank |
| 进度路由 | 3 | szw-progress / szw-resume | — | szw-pause |
| 复盘 | 2 | — | — | szw-retro / szw-audit |
| 系列管理 | 1 | — | — | szw-series |
| 配置 | 2 | szw-help / szw-config | — | — |
| **合计** | **26** | **12** | **7** | **7** |

---

## 3. v1.0 MVP（12 个命令）

目标：跑通"建专栏 → 创建文章项目 → 写一篇文章 → 发布 → 完结"的最小闭环（支持多 article 并行）。

### 3.0 Article 状态机

每个 article 在 ARTICLE.md 里有 `status` 字段，值在以下枚举中流转。STATE.md 的 `Active Articles` 表只显示非终态，`Recently Completed` 显示终态。

| Status | 由哪个命令进入 | 含义 | 是否 active |
|---|---|---|---|
| `created` | `/szw-new-article` | 项目刚建，未拷问 | ✅ |
| `brief_done` | `/szw-discuss` | brief 已确认 | ✅ |
| `research_done` | `/szw-research`（v2.0） | evidence + diagnosis 通过 | ✅ |
| `outline_done` | `/szw-outline`（v2.0） | thesis + section 拆片完成 | ✅ |
| `draft_done` | `/szw-write` | 04-draft.md 写完，等 review | ✅ |
| `review_failed` | `/szw-review` | HIGH issue 待修，最优先级 | ✅ |
| `review_passed` | `/szw-review` | 全 LOW，可发布 | ✅ |
| `published` | `/szw-publish` | 多平台版本就绪 | ✅ |
| `paused` | `/szw-pause`（v3.0） | 留 handoff，等待 resume | ✅ |
| `completed` | `/szw-complete --published` | 终态：流水线正式结束 | ❌ |
| `archived` | `/szw-complete --archived` | 终态：放弃 | ❌ |

**多 article 并行**：一个专栏下可同时有多篇 article 在不同 status，由 `/szw-progress` 列表 + 单 article 操作命令独立推进。所有命令都接受 `<slug>` 参数定位具体 article；不指定时按 STATE.md `last_touched` 取默认。

---

### 3.1 `/szw-init` —— 初始化专栏

| 项 | 内容 |
|---|---|
| **Description** | Initialize a new technical column from scratch. Adapts to two modes: empty directory (full construction) or existing directory (review-then-construct). Build COLUMN.md, EDITORIAL_CONTEXT.md, ADRs, and directory skeleton. |
| **触发** | 用户表达"我要开个技术专栏"/"建立写作系统"/"把这些散稿整合成专栏" |
| **输入** | 当前工作目录（可空可非空）+ 用户对专栏定位 / 用途的描述 |
| **步骤（公共部分）** | **Step 0 — 检测当前目录状态**：<br>　- 空目录（或仅 `.git` / `.DS_Store`）→ 走 **Mode A: 完整构造**<br>　- 含已有文件（草稿、笔记、已发布文章等）→ 走 **Mode B: review + 构造**<br><br>**Step 1 — 询问容器目录名**：默认 `Column`，可改为 `AICoding` / `TechWeekly` / `Zero` 等；如果当前已经在用户期望的目录里则跳过 |
| **Mode A（空目录）** | 1. 深度问答：专栏定位 / 目标读者 / 文章类型偏好（参考 EDITORIAL_CONTEXT §1-2）<br>2. 调用 `column-positioner` 子 agent 起草 `COLUMN.md`<br>3. 起草 `EDITORIAL_CONTEXT.md` 最小 7 节版（positioning / audience / principles / canonical-terms / topic-boundaries / argument-standards / style）<br>4. 询问是否建 3 条核心 ADR（默认建：no-benchmark-dumping / tool-review-needs-action / no-anxiety-farming）<br>5. 创建目录骨架（见下） + 写入 `.zero/STATE.md` 初始版 + `.zero/szw-config.json` |
| **Mode B（已有文件）** | 1. **扫描现有文件**：识别 markdown / 已发布文章 / 草稿 / 散落笔记，按主题聚类<br>2. 调用 `column-reviewer` 子 agent 分析：主题分布 / 写作风格 / 已使用术语 / 受众线索 / 已表达过的判断<br>3. **生成建议初稿**：<br>　- COLUMN.md 候选定位（基于已写内容反推真实偏好）<br>　- EDITORIAL_CONTEXT.md 候选术语 / 边界 / 风格<br>　- ADR 候选（如果发现作者已有反复出现的内容策略偏好）<br>4. **用户确认环节**：逐节展示建议，询问"接受 / 修改 / 跳过"，必要时多轮调整<br>5. **整合**：把已有文件移到 `articles/archived/` 或保持原位，根据用户选择<br>6. 创建目录骨架（见下） + 写入 `.zero/STATE.md` + `.zero/szw-config.json` |
| **目录骨架** | 显性：`published/` `articles/{,quick,archived}/` `editorial-adr/` `glossary/` `inbox/{pending,done}/` `series/` `summaries/`<br>隐藏：`.zero/{evidence,audits}/` |
| **产出** | `<容器目录>/{COLUMN.md, EDITORIAL_CONTEXT.md, ROADMAP.md}`、`editorial-adr/0001-0003.md`、`.zero/STATE.md`、`.zero/szw-config.json`；及全部空子目录；Mode B 下额外的 `articles/archived/` 入库 |
| **衔接** | 完成后建议 `cd <容器目录>` 然后 `/szw-help` 查命令；或 `/szw-new-article` 起第一篇 |
| **Gates** | Pre-flight：拒绝在已有 `.zero/` 的目录重跑（防覆盖，提示用 `/szw-evolve` v3.0 做重大转向）；Mode B 下若发现致命冲突（例如已有 `.zero/` 但不完整）escalate 询问 |

---

### 3.2 `/szw-new-article` —— 创建文章项目

| 项 | 内容 |
|---|---|
| **Description** | Create a new article as a structured project under the column. Each article is treated as its own project with metadata, type, target platforms, and a dedicated working directory. A column can host many articles. |
| **触发** | 准备开新文章；从 inbox 升级灵感；从 series 拉取下一篇 |
| **输入** | 标题 / 主题 + 可选 `--from-inbox <slug>` `--series <name>` `--type <article-type>` |
| **步骤** | 1. **询问 slug**（自动建议 `YYYY-MM-<topic-slug>`，强制英文短串便于 agent 索引）<br>2. **询问 article type**（industry-analysis / programmer-advice / product-analysis / tech-blog；与 EDITORIAL_CONTEXT §6 对齐）<br>3. **询问 target platforms**（默认从 `szw-config.json.default_platforms` 取，可覆盖）<br>4. **可选关联**：<br>　- `--from-inbox <slug>`：把 `inbox/pending/<slug>.md` 内容预填到 ARTICLE.md，移到 `inbox/done/`<br>　- `--series <name>`：检查 `series/<name>/INDEX.md` 存在，登记此 article 为系列下一篇<br>5. **创建项目目录**：`articles/<slug>/` + 写入 `ARTICLE.md`：<br>　- metadata：slug / type / target_platforms / created_at / status: created<br>　- thesis：（待 brief 后填）<br>　- linked_series：（如有）<br>　- linked_inbox：（如有）<br>6. **更新 STATE.md**：在 `## Active Articles` 表追加一行（slug / status: created / last_touched: now / next: /szw-discuss）<br>7. 提示用户下一步 `/szw-discuss <slug>` |
| **产出** | `articles/<slug>/ARTICLE.md`、可能的 `inbox/done/<slug>.md`、`series/<name>/INDEX.md` 更新 |
| **衔接** | `/szw-discuss` 拷问选题 + 起草 brief |
| **Gates** | Pre-flight：必须在专栏容器目录内（`.zero/szw-config.json` 存在）；slug 与已有 article 撞名 → escalate 询问改名或恢复；`--series` 指向不存在的 series → 提示先 `/szw-new-series` |

---

### 3.3 `/szw-discuss` —— 选题讨论拷问 + 文章 brief（合并）

| 项 | 内容 |
|---|---|
| **Description** | Stress-test the topic AND structure it into an article brief in one command. Two-phase: (1) interview-style grill (via szw-topic-grill), (2) structure into 01-brief.md with grill Q&A as appendix. |
| **触发** | `articles/<slug>/ARTICLE.md` 已存在；准备启动文章流水线第一步 |
| **输入** | article slug（命令参数或默认取 STATE.md `Active Articles` 表 last_touched 最大的） |
| **Phase 1 — 拷问** | 1. **前置检查**：`articles/<slug>/ARTICLE.md` 必须存在<br>2. 调用 `topic-grill-interviewer` 子 agent，按 9 问拷问（参考已有 [`skills/write/szw-topic-grill/SKILL.md`](../skills/write/szw-topic-grill/SKILL.md)）<br>3. 与 EDITORIAL_CONTEXT + ADR 自动比对，发现冲突立刻 escalate（"这选题违反 ADR 0001"）<br>4. 拷问通不过 → 把文章移到 `articles/archived/<slug>/` 并写明原因（abort）<br>5. 拷问通过 → 暂存 9 问 Q&A 进入 Phase 2 |
| **Phase 2 — 结构化** | 6. 读取 Phase 1 拷问结果 + 当前文章类型偏好（industry-analysis / programmer-advice / product-analysis / tech-blog）<br>7. 按 EDITORIAL_CONTEXT §6 Article Types 选模板<br>8. 产出 `01-brief.md`：<br>　- **正文**：thesis / reader-payoff / supporting-claims (3-5) / counterargument / evidence-needed / out-of-scope / target-platform<br>　- **附录 A：Topic Grill Q&A**：完整 9 问问答记录（用户回答 + AI 推荐答案 + 最终决定）<br>　- **附录 B：宪法对齐检查**：与 ADR / EDITORIAL_CONTEXT 比对结果<br>9. 把 thesis 回填到 `ARTICLE.md`，更新 status: brief_done |
| **产出** | `articles/<slug>/01-brief.md`（含拷问附录）、更新 ARTICLE.md / STATE.md |
| **衔接** | `/szw-write`（v1.0 跳过证据/诊断/拆片，直接起稿）；v2.0 后走 `/szw-research` |
| **Gates** | Pre-flight：ARTICLE.md 必须存在；Abort：拷问与 ADR 直接冲突；Escalation：拷问中选题模糊到无法回答 5 个问题以上 |
| **为什么合并** | 原 `/szw-grill` 和 `/szw-brief` 是连续两步，中间产物 `00-grill.md` 几乎从不被独立引用；合并并改名为 `/szw-discuss` 后用户少切一次命令，brief 自带"如何得出这个判断"的可追溯附录，更便于后续 audit / retro |

---

### 3.4 `/szw-write` —— 起稿 + 润色（合并，支持全文 / 章节模式）

| 项 | 内容 |
|---|---|
| **Description** | Unified write command for both first-draft authoring and polishing. Two modes: (1) **full mode** writes/polishes the entire article, (2) **section mode** targets a specific outline section. Each invocation is recorded in `.zero/writing-history/<slug>/` for retro & audit. |
| **触发** | v1.0：`01-brief.md` 已存在；v2.0 后：`03-outline.md` 已存在；review 后回头修复也走此命令 |
| **输入** | `01-brief.md` + `03-outline.md`（v2.0+）+ EDITORIAL_CONTEXT + 适用 ADR + glossary + **`.zero/style-profile.md`**（作者风格档案，由 szw-review 累积）+ 当前 `04-draft.md`（如果存在） |
| **调用语法** | `/szw-write [section_id?] [--mode draft\|polish\|both]`<br>　- `/szw-write` —— 全文 + both（默认；初次起稿用）<br>　- `/szw-write --mode polish` —— 全文润色（review 后修复用）<br>　- `/szw-write S2` —— 仅 outline 第 2 节，both（章节级迭代）<br>　- `/szw-write S3 --mode polish` —— 仅章节 S3 润色 |
| **Phase 1 — Draft（draft / both 模式）** | 1. 加载 outline + EDITORIAL_CONTEXT §11 Style Guide + Banned Patterns + 相关 ADR + **style-profile.md（作者风格档案）**<br>2. 按选定的 Article Type 模板和 outline section 写文字，**主动按 style-profile 调整**：避免 anti-patterns（用户反复删除的词）；优先使用作者偏好句式；保留作者中英混用习惯<br>3. 每节自检 acceptance criteria（来自 03-outline.md §2）<br>4. 章节模式只写 / 改指定 section，不动其他<br>5. 全文模式写完整 04-draft.md |
| **Phase 2 — Polish（polish / both 模式）** | 6. 调用 superpowers `humanizer` skill 过一遍<br>7. 调用 `humanizer-editor` 子 agent 检查 EDITORIAL_CONTEXT §11 / §12 banned patterns + **style-profile anti-patterns**<br>8. 检查 §15 Chinese Writing Preferences（如果中文）<br>9. 锐化判断（避免"或许 / 可能 / 在某种程度上"过度堆叠）<br>10. 检查每节 reader payoff |
| **写作历史记录** | 11. 每次 `/szw-write` 调用产出快照写入 `.zero/writing-history/<slug>/`：<br>　- 文件名：`NN-{mode}-{target}-{timestamp}.md`<br>　　 例：`01-both-full-2026-05-06T10-15.md` / `02-polish-S2-2026-05-06T11-30.md`<br>　- 同时更新 `INDEX.md`：每次操作的 mode / target / 修改 section 列表 / 与上一版 diff 摘要<br>12. 当前 `04-draft.md` 始终是最新合成结果（作为下游 review / package 的输入） |
| **产出** | `articles/<slug>/04-draft.md`（最新版，覆盖式更新）<br>`.zero/writing-history/<slug>/INDEX.md` + 各次快照 |
| **衔接** | 初次写 → `/szw-review`；review 报 HIGH issue → 回 `/szw-write [section] --mode polish` 修复；最终 → `/szw-publish` |
| **Gates** | Pre-flight：outline 存在（v2.0+）/ brief 存在（v1.0）；`section_id` 必须在 outline 里有定义；Revision：banned patterns 自动重写；Escalation：humanizer 报告 5+ 个 AI 腔标志且 polish 一轮后仍未消，提示用户手动介入 |
| **参与度** | 综合 ★★★★★ HIGH（取 polish 阶段最高分）。draft 阶段决策权重 2 / 审阅 4 / 修改 5；polish 阶段决策权重 5 / 审阅 5 / 修改 5。章节模式可降为 ★★★★（仅范围缩小，深度不变）。 |
| **为什么合并** | 原 `/szw-draft` 和 `/szw-edit` 分两步，但实际写作中是迭代过程：写一段改一段、回头修前面、review 后某节重写。合并为单命令多模式后：(a) 自然支持"指定章节迭代"；(b) draft / polish 可独立调用也可一次跑完；(c) `.zero/writing-history/` 留下完整迭代轨迹，便于复盘"这篇是怎么写出来的"。 |

---

### 3.5 `/szw-publish` —— 多平台打包

| 项 | 内容 |
|---|---|
| **Description** | Package the polished draft into platform-specific versions (blog, WeChat, X, Xiaohongshu). |
| **触发** | `04-draft.md` 已存在且 review 通过 |
| **输入** | draft v2 + target platforms |
| **步骤** | 1. 询问目标平台（默认 blog + wechat）<br>2. 各平台独立产出：<br>　- blog：保留全文 + 内链 + 代码块<br>　- wechat：拆段加小标题 + 首屏钩子 + 加重点 + 文末引导<br>　- x：thread 形式，第一条 hook，每条 280 字内<br>　- xhs：首屏 5 行 + emoji + 标签<br>3. 调用 `dense-summary` 子能力（v3.0 独立成 skill）生成各平台首屏<br>4. 写到 `published/<slug>/` 多文件 |
| **产出** | `published/<slug>/{blog,wechat,x,xhs}.md`、ARTICLE.md status: published |
| **衔接** | 平台版本就绪后用 `/szw-complete <slug>` 终结流水线；之后可选 `/szw-retro`（v3.0）复盘 |
| **Gates** | Pre-flight：v2 存在 + claim-diagnose 通过（v2.0 起）；提示用户手动发布或对接发布 API |

---

### 3.6 `/szw-complete` —— 终结文章流水线

| 项 | 内容 |
|---|---|
| **Description** | Mark an article as completed (after publish) or archived (abandoned). Move it from STATE.md `Active Articles` to `Recently Completed`. Optionally trigger retro. Use to close the lifecycle of one article so multi-article workflows stay clean. |
| **触发** | 文章已 publish 完成想正式结束；或写到一半放弃想归档 |
| **输入** | article slug + 可选 mode（`--published` 默认 / `--archived` / `--retro`）|
| **调用语法** | `/szw-complete [slug?] [--published\|--archived] [--retro]`<br>　- `/szw-complete` —— 默认终结当前 active article（仅一个时）；多个时 escalate 询问<br>　- `/szw-complete 2026-05-skills-vs-gsd` —— 终结指定 article（默认 published）<br>　- `/szw-complete <slug> --archived` —— 归档（写到一半放弃）<br>　- `/szw-complete <slug> --retro` —— 终结后立刻触发 `/szw-retro`（v3.0） |
| **步骤** | 1. 解析 slug；多个 active article 时若未指定则 escalate 询问<br>2. 验证 article 状态：<br>　- `--published` 模式要求当前 status ∈ {published, review_passed}<br>　- `--archived` 模式接受任意状态<br>3. 更新 `articles/<slug>/ARTICLE.md` status: completed / archived；写入 completed_at 时间戳<br>4. 若 `--archived` 且非 published：移动 `articles/<slug>/` → `articles/archived/<slug>/`<br>5. 更新 `.zero/STATE.md`：<br>　- 从 `## Active Articles` 表移除该行<br>　- 追加到 `## Recently Completed` 表（保留最近 N 条）<br>　- 更新 `Articles published` / `Articles in progress` 计数<br>6. 若 `--retro`：自动调用 `/szw-retro <slug>`（v3.0）<br>7. 若该 article 关联了某 series：更新 `series/<name>/INDEX.md` 进度 |
| **产出** | 更新后的 ARTICLE.md（终态）、STATE.md、可能的 archived 移动、可能的 series INDEX 更新 |
| **衔接** | `/szw-new-article` 起下一篇；或 `/szw-progress` 看其余 active articles；或 `/szw-retro` 复盘 |
| **Gates** | Pre-flight：article 存在；`--published` 模式 status 必须在 publish 之后；Escalation：`--archived` 一篇 status 是 published 时询问"确认归档？发布版本仍保留" |

---

### 3.7 `/szw-context` —— 维护编辑宪法

| 项 | 内容 |
|---|---|
| **Description** | Update the long-term editorial context (positioning, principles, glossary, banned patterns). Use when a recurring concept needs definition or a writing rule should apply across articles. |
| **触发** | 写文章时发现某术语反复需要重定义；某种风格问题反复出现；用户主动请求 |
| **输入** | 当前 EDITORIAL_CONTEXT.md + 修改提案 |
| **步骤** | 1. 调用 `editorial-context-curator` 子 agent<br>2. 挑战提案的模糊点（仿 mattpocock grill-with-docs）<br>3. 选定 canonical term，列出 avoid 别名<br>4. 写回 EDITORIAL_CONTEXT.md 对应 section<br>5. 询问是否需要建 ADR 记录"为什么这么定" |
| **产出** | 更新后的 `EDITORIAL_CONTEXT.md`、可能的新 ADR |
| **衔接** | 大改动 → `/szw-adr`；小改动 → 直接生效 |
| **Gates** | Pre-flight：检查 git status，提示该改动应该单独 commit；Revision：与已有 ADR 冲突要求人工裁决 |

---

### 3.8 `/szw-adr` —— 编辑决策记录

| 项 | 内容 |
|---|---|
| **Description** | Create or update an editorial Architecture Decision Record. Use when a content strategy decision will affect future articles and needs a durable rationale. |
| **触发** | 决策满足三条件（参考 [`ADR.md`](../write-progress/ADR.md) §2）：会反复影响文章方向 / 有真实取舍 / 未来会忘了为什么 |
| **输入** | 决策描述 + 触发场景 |
| **步骤** | 1. 判断是否够格做 ADR（不够就建议改去 `/szw-context`）<br>2. 用模板生成（Status / Date / Context / Decision / Consequences / Linked Context）<br>3. 编号自动递增（`editorial-adr/0009-*.md`）<br>4. 同步在 EDITORIAL_CONTEXT 对应 section 加一行 short rule（不复制 ADR 全文）<br>5. 提示用户是否要重审已发表的文章是否违反此 ADR（v3.0 由 `/szw-audit` 处理） |
| **产出** | `editorial-adr/NNNN-slug.md`、EDITORIAL_CONTEXT.md 同步条目 |
| **衔接** | `/szw-audit`（v3.0）查既往违反 |
| **Gates** | 命名重复检测；与已有 ADR 矛盾必须 escalate |

---

### 3.9 `/szw-progress` —— 进度路由（多 article）

| 项 | 内容 |
|---|---|
| **Description** | Show progress of all active articles with per-article next-step recommendations. Default route command for multi-article workflows. Recommends the highest-priority next action when invoked without args. |
| **触发** | 用户问"接下来该做啥"；想看所有 article 进度；新会话不确定 resume 路径 |
| **输入** | `.zero/STATE.md`（含 Active Articles 表）+ 各 article 的 ARTICLE.md |
| **调用语法** | `/szw-progress` —— 所有 active articles 表 + 全局推荐<br>`/szw-progress <slug>` —— 单 article 详细状态 + 阶段产物清单<br>`/szw-progress --next` —— 仅推荐当前最该做的（按 last_touched 降序，blocked 优先）<br>`/szw-progress --do "<text>"` —— 自然语言路由（仿 `/gsd-progress --do`）<br>`/szw-progress --completed` —— 列最近完成的文章 |
| **步骤** | 1. 读 STATE.md 拉 Active Articles 表（slug / status / last_touched）<br>2. 对每个 article 计算下一步建议（按 status → 命令映射，见 [`szw-help/SKILL.md`](../skills/write/szw-help/SKILL.md) 下一步推荐规则）<br>3. 默认输出多 article 进度表 + 全局"最该做"推荐（按优先级：review_failed > 时间最久未触碰 > 其他）<br>4. `<slug>` 模式：详细列该 article 各阶段产物文件 + 当前 status + 推荐 |
| **优先级排序** | (1) status: `review_failed` —— 最优先（HIGH issue 待修）<br>(2) status: `paused` —— 次之（已留 handoff，恢复成本低）<br>(3) `last_touched` 最久 —— 最后做（避免被忘记）<br>(4) 其他按 last_touched 降序 |
| **产出** | 终端显示报告（不写文件） |
| **衔接** | 用户选某 article → 调对应阶段命令；或继续 `/szw-resume <slug>` |
| **Gates** | Pre-flight：`.zero/STATE.md` 必须存在，否则提示先 `/szw-init` |

---

### 3.10 `/szw-resume` —— 跨 session 恢复（指定 article）

| 项 | 内容 |
|---|---|
| **Description** | Restore working context for a specific article. Use as the first command when starting a new conversation, or when switching between articles in multi-article workflows. |
| **触发** | 新会话刚开始；上一次工作被打断；想从一篇文章切到另一篇 |
| **输入** | `.zero/STATE.md` + 指定 article 的目录 |
| **调用语法** | `/szw-resume` —— 默认恢复"上次活跃" article（取 STATE.md last_touched 最大的 active article）<br>`/szw-resume <slug>` —— 恢复指定 article<br>`/szw-resume --list` —— 列出可 resume 的 articles（active + paused），让用户选 |
| **步骤** | 1. 读 STATE.md Active Articles 表<br>2. 路由：<br>　- 无参数 → last_touched 最大的；只有 1 个 active 时直接选它<br>　- `--list` → 多 article 时列表 + 序号让用户选<br>　- `<slug>` → 验证存在<br>3. 读该 article：<br>　- ARTICLE.md（元数据 + status + thesis）<br>　- 当前 status 对应的最新阶段产物（如 status=draft_done → 读 04-draft.md）<br>4. 读 EDITORIAL_CONTEXT.md 前 5 节（positioning / audience / principles / canonical-terms / topic-boundaries）<br>5. 报告：恢复了哪篇、上次到哪、推荐下一步 |
| **产出** | 终端显示恢复报告（不写文件） |
| **衔接** | 接 `/szw-progress --next` 或推荐的具体命令 |
| **Gates** | Pre-flight：STATE.md 存在；指定 slug 时必须在 active list 里 |

---

### 3.11 `/szw-help` —— 命令参考

| 项 | 内容 |
|---|---|
| **Description** | Show available column commands and usage guide. |
| **触发** | 用户问"有哪些命令"、"怎么用"、`/szw-help` 显式调用 |
| **输入** | 无 |
| **步骤** | 1. 渲染 `~/.szw-system/workflows/help.md`<br>2. 按当前 STATE.md 推荐"现在最该用的命令" |
| **产出** | 终端显示命令分类清单 |

---

### 3.12 `/szw-config` —— 配置

| 项 | 内容 |
|---|---|
| **Description** | Configure column workflow settings (model profile, default platforms, hooks). |
| **触发** | 首次配置；切换 model profile；调整默认行为 |
| **输入** | `.zero/szw-config.json` |
| **步骤** | 1. 显示当前配置<br>2. 子命令：`--profile`（model profile）/`--platforms`（默认目标平台）/`--hooks`（开关）/`--lang`（zh/en）<br>3. 写回 `szw-config.json` |
| **产出** | 更新后的 `.zero/szw-config.json` |
| **关键配置**（详见 §10） | `model_profile`：quality/balanced/budget；`default_platforms`：blog,wechat；`hooks`：true/false；`writing_lang`：zh/en |

---

## 4. v2.0 增强（7 个命令）

目标：补齐主流水线的研究 / 论证 / 审稿环节，加入轻量出口与系列创建。

### 4.1 `/szw-new-series` —— 创建文章系列

| 项 | 内容 |
|---|---|
| **Description** | Create a new article series. Plan multiple connected articles around a theme. A series is a higher-order project that groups several `/szw-new-article` projects. |
| **触发** | 同主题计划写 3+ 篇文章；多个 inbox 灵感聚拢成同一主题；某个长文章拆不下来想拆系列 |
| **输入** | 系列名（slug）+ 系列主题 + 计划文章数 + 可选 `--from-inbox <slug,slug,...>` |
| **步骤** | 1. **询问系列名**（强制英文短串如 `agentic-coding-2026` / `claude-code-deep-dive`）<br>2. **询问系列主题**：贯穿论点、目标读者、计划周期<br>3. 调用 `series-planner` 子 agent：<br>　- 拉相关 inbox / 已发布文章做主题分析<br>　- 起草系列大纲（3-7 篇推荐范围）<br>　- 每篇预设 thesis / 顺序 / 计划日期<br>4. **用户确认环节**：逐篇展示，"接受 / 修改 / 删除 / 调换顺序"<br>5. **创建系列目录**：`series/<name>/INDEX.md` 含完整大纲<br>6. **可选 `--with-article`**：立刻调用 `/szw-new-article --series <name>` 创建第一篇<br>7. 更新 `ROADMAP.md`，把系列计划文章登记到选题列表 |
| **产出** | `series/<name>/INDEX.md`、可能的 `articles/<slug>/ARTICLE.md`（关联系列）、ROADMAP.md 更新 |
| **衔接** | `/szw-new-article --series <name>` 创建系列内具体文章；`/szw-series` (v3.0) 管理系列进度 |
| **Gates** | Pre-flight：必须在容器目录内；同名系列已存在 → escalate；如果系列计划与已有 ADR 冲突（例如想做 benchmark 系列违反 ADR 0001）→ abort |

---

### 4.2 `/szw-research` —— 证据采集 + 判断诊断（合并，Codex）

| 项 | 内容 |
|---|---|
| **Description** | Combined evidence collection + claim diagnosis in a single Codex-driven command. Two-phase: (1) gather evidence cards for each supporting claim, (2) diagnose whether each claim is factually supported and safely worded. Internal HIGH-risk loop returns to Phase 1 for more evidence. |
| **触发** | brief 已完成；准备进入证据 + 诊断阶段 |
| **输入** | `01-brief.md` + EDITORIAL_CONTEXT §10 Evidence Standards |
| **Phase 1 — 证据采集** | 1. 调用 `evidence-researcher` 子 agent（强制走 Codex）<br>2. 按 preferred / risky 分级<br>3. 每条 claim 产出 evidence card：source / date / quote / link / confidence<br>4. 缺证据的 claim 标 `SOURCE_NEEDED`<br>5. 沉淀复用证据到 `.zero/evidence/<topic>.md` |
| **Phase 2 — 判断诊断** | 6. 调用 `claim-diagnoser` 子 agent（Codex）<br>7. 提取主要 claims，每条按模板诊断（Claim / Type / Evidence Required / Evidence Available / Counter-Evidence / Confidence / Risk / Safer Rewrite）<br>8. 给出整体可信度评分 + critical claims to fix 清单 |
| **内部 HIGH-risk 循环** | 9. Phase 2 报告 HIGH-risk ≥ 1 时：<br>　- 第一轮：自动回 Phase 1 补特定 claim 的证据，重跑 Phase 2<br>　- 第二轮仍 HIGH：escalate 给用户，可选 abort（回 `/szw-discuss` 降级表达）或人工接受<br>　- 最多内部循环 2 轮，不无限重试 |
| **产出** | `articles/<slug>/02-research.md`：<br>　- **§1 Evidence Cards**（Phase 1 全部证据卡）<br>　- **§2 Claim Diagnosis**（Phase 2 诊断报告 + H/M/L 评级）<br>　- **§3 Recommended Action**（HIGH-risk 处理建议）<br>同时沉淀 `.zero/evidence/<topic>.md` 跨文章复用 |
| **衔接** | 通过 → `/szw-outline`；HIGH 风险未消 → 回 `/szw-discuss` 重审选题或降级表达 |
| **Gates** | Pre-flight：brief 存在；Escalation：3+ claim 找不到证据 / Phase 2 第二轮仍 HIGH-risk；Revision：HIGH-risk 自动内部循环（最多 2 轮） |
| **为什么合并** | 原 `/szw-evidence` 和 `/szw-diagnose` 都跑 Codex，且诊断必然依赖证据；分两步用户切换两次命令、读两份报告。合并为单步：Codex 一次性跑完，HIGH-risk 内部循环自愈，用户只在最终结果或 escalate 时介入。参与度被 diagnose 的 HIGH-risk 决策点拉到 ★★★★ HIGH-MED。 |

---

### 4.3 `/szw-outline` —— 论证地图 + 文章拆片（合并）

| 项 | 内容 |
|---|---|
| **Description** | Two-phase outlining: (1) build argument map (thesis + supporting + counter), (2) slice into vertical section outlines with acceptance criteria. Internal loop: if Phase 2 finds a supporting can't carry an independent section, return to Phase 1. |
| **触发** | `/szw-research` 通过（diagnosis 部分无 HIGH-risk 残留） |
| **输入** | `01-brief.md` + `02-research.md`（含 evidence + diagnosis） |
| **Phase 1 — 论证地图** | 1. 调用 `thesis-mapper` 子 agent<br>2. 主 thesis 一句话锁定（用户拍板措辞）<br>3. 列出 3-5 supporting claims，每条挂 02-research.md 里的 evidence<br>4. 列出 1-2 counterargument，给出回应方式<br>5. 检查论证链是否成立（每个 claim 都能推到 reader takeaway） |
| **Phase 2 — 章节拆片** | 6. 调用 `section-planner` 子 agent<br>7. 按 vertical slice 拆 4-6 节，每节包含 title / claim / evidence / reader payoff / programmer implication / counterarg / acceptance criteria（参考 [`flow.md`](../write-progress/flow.md) §13）<br>8. 拒绝产出"背景/分析/结论"这种横向章节；优先 4-6 强 section，不要 10 弱 section |
| **内部循环** | 9. Phase 2 发现某 supporting 撑不起一节（reader payoff 弱 / claim 不够锐 / 不可独立成立）：<br>　- 第一轮：自动回 Phase 1 调整论证（合并、降级或加新 supporting）<br>　- 第二轮仍不行：escalate 给用户，可选回 `/szw-research` 补证据 / 回 `/szw-discuss` 调命题<br>　- 最多内部循环 2 轮 |
| **产出** | `articles/<slug>/03-outline.md`：<br>　- **§1 Thesis Map**（main thesis + supporting + counter + 论证链）<br>　- **§2 Section Slices**（4-6 节，每节带 acceptance criteria）<br>　- **§3 Decision Log**（Phase 1 / Phase 2 间的迭代决策记录） |
| **衔接** | `/szw-write`（v2.0 起 outline 必跑） |
| **Gates** | Pre-flight：research 完成；Revision：Phase 2 报告弱 section → 内部循环（最多 2 轮）；Escalation：第二轮仍不通过 → 回上游 |
| **为什么合并** | 原 `/szw-thesis`（论证主线）和 `/szw-slice`（章节拆片）本质是同一个"论证设计"推理链——写 thesis 时本来就在想"这条 supporting 撑得起一节吗"，slice 阶段又常回头改 thesis。合并为单步：双阶段一次跑完 + 弱 section 内部循环回 Phase 1 自愈，参与度同档（两阶段都 HIGH），合并不模糊边界。 |

---

### 4.4 `/szw-review` —— 反方审稿（Codex）

| 项 | 内容 |
|---|---|
| **Description** | Two-phase review: (1) skeptical review by an independent AI (Codex) for fact / counterargument / boundary; (2) **author style capture** by diffing current `04-draft.md` against the latest `.zero/writing-history/` AI snapshot to learn from user edits. Style insights accumulate to `.zero/style-profile.md` for future `/szw-write` calls. |
| **触发** | draft 完成（v2.0 起，每次 write 后跟一次 review） |
| **输入** | `04-draft.md` + `01-brief.md` + `02-research.md` + EDITORIAL_CONTEXT + `.zero/writing-history/<slug>/`（最近 AI 快照）+ `.zero/style-profile.md`（已有档案，可空） |
| **Phase 1 — 反方审稿（Codex）** | 1. 调用 `skeptical-reviewer` 子 agent（强制 Codex 跨 AI）<br>2. 三类审：<br>　- 技术审：术语 / 数字 / 引用<br>　- 反方审：最强反驳是什么<br>　- 边界审：是否越过 EDITORIAL_CONTEXT topic boundary、是否违反 ADR<br>3. 输出 HIGH / MEDIUM / LOW 分级 issues |
| **Phase 2 — 风格捕获（Style Capture）** | 4. 找最近一次 `.zero/writing-history/<slug>/NN-*.md`（AI 上次产出的快照）<br>5. 对比当前 `04-draft.md` vs 最近快照：<br>　- 计算 diff（按段 / 按句 / 按词）<br>　- 如果 diff < 阈值（默认 5% 修改字数）→ 跳过 Phase 2（无需学习）<br>　- 如果 diff ≥ 阈值 → 这部分修改大概率是用户手改的"作者风格"<br>6. 调用 `style-extractor` 子 agent 分析 diff，提取 5 类特征：<br>　- **词汇替换**：AI 用 X，作者改成 Y（带频次）<br>　- **句式偏好**：长句拆短 / "不是 X 而是 Y" 等结构<br>　- **节奏 / 段落**：段长 / 段首句习惯<br>　- **标点 / 中英混用**：`——` vs `--`、术语保留英文等<br>　- **Anti-patterns**：作者反复删除的词 / 句式（最高优先级喂给下次 write） |
| **风格档案累积** | 7. 把本次提取的特征追加到 `.zero/style-profile.md` 的 `## Recent Edits` 段（增量 append，带 article slug 和时间戳来源引用）<br>8. 定期合并：累计 ≥ 10 次 review 后，自动合并 Recent Edits 到 `## Stable Patterns`，按频次过滤低于 3 次的规则丢弃<br>9. 每条规则带置信度（频次）+ 来源（哪些文章贡献的） |
| **产出** | `articles/<slug>/05-review.md`（Phase 1 反审报告）<br>`.zero/style-profile.md`（Phase 2 累积更新） |
| **衔接** | HIGH ≥ 1 → 回 `/szw-write [section] --mode polish` 修；全 LOW → `/szw-publish`；style-profile 自动喂给下次 `/szw-write`，无需手动衔接 |
| **Gates** | Phase 1 review 循环最多 2 轮（沿用 GSD `gsd-plan-review-convergence` 模式）；Phase 2 diff 不显著时跳过（不强制学习每次微调） |
| **参与度** | 综合仍为 ★★ LOW-MED。Phase 1 用户决策 HIGH issue 走不走；Phase 2 完全 AI 自主，用户不参与，但效果累积到下次 write |

---

### 4.5 `/szw-capture` —— 灵感入 inbox

| 项 | 内容 |
|---|---|
| **Description** | Capture an idea, observation, or quote into the inbox without breaking current work. |
| **触发** | 写文章时蹦出新选题；看到值得记的引用；不想中断当前流程 |
| **输入** | 一段自由文本 |
| **步骤** | 1. 写到 `inbox/pending/<timestamp>-<slug>.md`<br>2. 自动 tag（来源 / 关联文章 / 候选类型）<br>3. 不动 STATE.md 的 Active Articles 表（保持当前 last_touched 不变，不抢焦点） |
| **产出** | `inbox/pending/*.md` |
| **衔接** | 后续 `/szw-new-article --from-inbox <slug>` 升级 |

---

### 4.6 `/szw-quick` —— 短评直出

| 项 | 内容 |
|---|---|
| **Description** | Write a short opinion piece (≤500 words) by skipping the full pipeline. Use for tweet-length thoughts and quick replies. |
| **触发** | 想表达观点但够不上长文；时事短评；引用别人内容加按语 |
| **输入** | 一段意图描述 |
| **步骤** | 1. 创建 `articles/quick/<slug>/`<br>2. 单步生成草稿（直接走 humanizer + EDITORIAL_CONTEXT 风格）<br>3. 直接打包到 `published/quick/<slug>/`<br>4. 跳过 grill / brief / evidence / diagnose / thesis / slice / review |
| **产出** | `published/quick/<slug>/*.md` |
| **衔接** | 发布 |
| **Gates** | Scope check：超过 800 字自动转 `/szw-new-article` 升级到完整流水线 |

---

## 5. v3.0 完整（7 个命令）

目标：复盘闭环、长期资产沉淀、系列管理、审计。

### 5.1 `/szw-retro` —— 发布后复盘

| 项 | 内容 |
|---|---|
| **Description** | Post-publication retrospective. Capture data, reader feedback, lessons. Trigger ADR/glossary updates. |
| **触发** | 文章发布后；通常发布 ≥ 1 周再跑（数据稳定后） |
| **输入** | 发布数据（手输或对接平台 API）+ 读者反馈摘要 |
| **步骤** | 1. 收集数据：阅读数 / 互动 / 关键反馈<br>2. 自检 5 问：<br>　- 哪条 claim 受质疑最多？<br>　- 哪个段落转化最高？<br>　- 标题与内容对位吗？<br>　- 有读者纠错吗？<br>　- 这次写作有重复出现的问题吗？<br>3. 输出 ADR 候选 / glossary 候选 / 流程改进候选<br>4. 写到 `articles/<slug>/RETRO.md` |
| **产出** | `RETRO.md`、可能触发 `/szw-adr` 或 `/szw-context` |
| **衔接** | 强制反哺长期资产 |

---

### 5.2 `/szw-audit` —— 专栏一致性审计

| 项 | 内容 |
|---|---|
| **Description** | Audit the column for term drift, ADR violations, and EDITORIAL_CONTEXT inconsistencies across published articles. |
| **触发** | 季度审计；新建 ADR 后回查；术语定义变更后 |
| **输入** | `published/` + EDITORIAL_CONTEXT + ADR |
| **步骤** | 1. 提取所有已发布文章的 canonical term 使用<br>2. 对照 EDITORIAL_CONTEXT.md glossary 检查一致性<br>3. 检查每篇是否违反 ADR<br>4. 报告：术语漂移点 / ADR 违反点 / 风格漂移点 |
| **产出** | `.zero/audits/AUDIT-<date>.md` |
| **衔接** | 严重违反 → `/szw-adr` 修订或新增 ADR；轻微 → 记入 backlog |

---

### 5.3 `/szw-glossary` —— 单术语维护

| 项 | 内容 |
|---|---|
| **Description** | Manage a single canonical term in `glossary/`. Use when a term needs deeper treatment than EDITORIAL_CONTEXT inline definition. |
| **触发** | 某术语反复需要长定义；术语变体多需独立澄清；术语跨文章使用频次高 |
| **输入** | 术语名 |
| **步骤** | 1. 创建 / 更新 `glossary/<term>.md`<br>2. 模板：canonical / aliases / avoid / definition / examples / counter-examples / linked-articles<br>3. 在 EDITORIAL_CONTEXT.md §4 Canonical Terms 加 1 行索引指向 glossary |
| **产出** | `glossary/<term>.md` |

---

### 5.4 `/szw-evidence-bank` —— 证据银行

| 项 | 内容 |
|---|---|
| **Description** | Manage the cross-article evidence bank. Curate, age, retire evidence cards. |
| **触发** | 季度维护；发现某证据已过期；新工具发布需新建 evidence card |
| **输入** | `.zero/evidence/` |
| **步骤** | 1. 列出 90+ 天未更新的 evidence card，标记 `STALE`<br>2. 列出过期失效的，移到 `.zero/evidence/retired/`<br>3. 检查 evidence card 与最新 EDITORIAL_CONTEXT preferred sources 标准是否一致<br>4. 输出"该补什么类型证据"建议 |
| **产出** | 更新 `.zero/evidence/`、可能的"待研究"清单 |

---

### 5.5 `/szw-stats` —— 专栏数据统计

| 项 | 内容 |
|---|---|
| **Description** | Display column statistics: published / drafting / inbox / ADR count / timeline. |
| **步骤** | 1. 扫 `articles/` 统计各 status<br>2. 扫 `published/` 统计平台覆盖<br>3. 扫 `editorial-adr/` ADR 数量与最近变更<br>4. 报告时间线 |
| **产出** | 终端显示 |

---

### 5.6 `/szw-summary` —— 周期汇总

| 项 | 内容 |
|---|---|
| **Description** | Generate a quarterly/yearly column summary for retrospection or onboarding. |
| **触发** | 季度末 / 年末；新合作者上手前 |
| **步骤** | 1. 拉指定时间段已发文章<br>2. 按 thesis 聚类，生成主题地图<br>3. 抽取贯穿性 ADR / 术语演化<br>4. 给出"该专栏在解决什么问题、回答了什么、留下什么 open questions" |
| **产出** | `summaries/<period>.md` |

---

### 5.7 `/szw-series` —— 系列管理（创建用 `/szw-new-series`）

| 项 | 内容 |
|---|---|
| **Description** | Manage existing article series. For creating a new series, use `/szw-new-series` (v2.0). Sub-commands here: `--list` / `--status` / `--reorder` / `--complete`. |
| **触发** | 系列已存在；想看进度 / 调整 / 归档 |
| **步骤** | `--list`：列出所有系列（active / completed）<br>`--status <name>`：显示某系列下文章进度（每篇 status / 发布日期 / 平台覆盖）<br>`--reorder <name>`：调整文章顺序<br>`--complete <name>`：归档系列（INDEX.md status: completed），更新主 ROADMAP |
| **产出** | 终端报告 / 更新 `series/<name>/INDEX.md` |
| **衔接** | 系列下加新文章 → `/szw-new-article --series <name>` |

---

### 5.8 `/szw-pause` —— 留 handoff

| 项 | 内容 |
|---|---|
| **Description** | Pause work mid-article. Save handoff for next session. |
| **步骤** | 1. 写 `.zero/.continue-here`：当前 article + 下一步建议命令 + 关键开放问题<br>2. 更新 `.zero/STATE.md` status: paused |
| **产出** | `.continue-here` 文件 |
| **衔接** | 下次 `/szw-resume` 自动读 |

---

## 6. 命名空间路由（meta-skill）

仿 GSD 的 6 个 `gsd-ns-*`，可建 3 个 meta-skill 帮助两阶段路由（SKILL 不直接执行，让模型从 27 个里挑）：

| Meta-skill | 路由到 |
|---|---|
| `szw-ns-pipeline` | grill / brief / evidence / diagnose / thesis / slice / draft / review / edit / package |
| `szw-ns-assets` | new / context / adr / glossary / evidence-bank / audit |
| `szw-ns-meta` | progress / resume / pause / capture / quick / stats / summary / help / config |

仅当 27 个命令在自动加载列表里造成噪音时才加 meta-skill。MVP 阶段不需要。

---

## 7. 子 agent 注册表

仿 GSD `references/agent-contracts.md`，6 个写作专用子 agent：

| Agent | 角色 | 调用 skill | Completion marker | 跑在 |
|---|---|---|---|---|
| `column-positioner` | 起草 COLUMN.md / 初版 EDITORIAL_CONTEXT（Mode A） | szw-init | `## COLUMN INIT COMPLETE` | Claude |
| `column-reviewer` | 扫描已有文件，反推定位 / 风格 / 术语建议（Mode B） | szw-init | `## REVIEW COMPLETE` | Claude |
| `series-planner` | 系列大纲规划 | szw-new-series | `## SERIES PLAN COMPLETE` | Claude |
| `topic-grill-interviewer` | 选题拷问（szw-discuss Phase 1） | szw-discuss | `## GRILL COMPLETE` / `## GRILL ABORTED` | Claude |
| `evidence-researcher` | 证据采集（szw-research Phase 1） | szw-research | `## EVIDENCE COMPLETE` / `## EVIDENCE BLOCKED` | **Codex** |
| `claim-diagnoser` | 判断诊断（szw-research Phase 2） | szw-research | `## DIAGNOSIS PASSED` / `## DIAGNOSIS HIGH-RISK` | **Codex** |
| `thesis-mapper` | 论证地图（szw-outline Phase 1） | szw-outline | `## THESIS MAP COMPLETE` / `## THESIS NEEDS REWORK` | Claude |
| `section-planner` | 文章拆片（szw-outline Phase 2） | szw-outline | `## SLICES COMPLETE` / `## SLICES NEEDS REWORK` | Claude |
| `skeptical-reviewer` | 反方审稿（szw-review Phase 1） | szw-review | `## REVIEW COMPLETE` 含 H/M/L | **Codex** |
| `style-extractor` | 风格捕获（szw-review Phase 2，对比 draft vs history 提取作者偏好） | szw-review | `## STYLE CAPTURED` / `## DIFF NOT SIGNIFICANT` | Claude |
| `humanizer-editor` | 润色（szw-write Phase 2） | szw-write | `## HUMANIZED` / `## NEEDS MANUAL EDIT` | Claude |
| `editorial-context-curator` | 宪法维护 | szw-context | `## CONTEXT UPDATED` / `## ADR NEEDED` | Claude |

每个 agent 在独立子 session 跑，主对话只看 markdown 产物，不看过程。

---

## 8. Hooks 配置

写入 `.claude/settings.json`（项目级）或全局：

### 8.1 PreToolUse（保护性）

```json
{
  "PreToolUse": [
    {
      "matcher": "Write|Edit",
      "filePathPattern": "**/EDITORIAL_CONTEXT.md",
      "command": "echo '⚠️  EDITORIAL_CONTEXT.md 是宪法文件，建议走 /szw-context 或建 ADR'; exit 1"
    },
    {
      "matcher": "Write|Edit",
      "filePathPattern": "**/published/**",
      "command": "echo '⚠️  published/ 是流水线产物，请走 /szw-publish'; exit 1"
    }
  ]
}
```

### 8.2 PostToolUse（自动化）

```json
{
  "PostToolUse": [
    {
      "matcher": "Write",
      "filePathPattern": "**/articles/*/04-draft.md",
      "command": "~/.szw-system/bin/update-state.sh draft_done"
    },
    {
      "matcher": "Write",
      "filePathPattern": "**/editorial-adr/*.md",
      "command": "~/.szw-system/bin/sync-adr-index.sh"
    },
    {
      "matcher": "Write",
      "filePathPattern": "**/articles/*/RETRO.md",
      "command": "echo '📊 复盘已写。是否要 /szw-adr 或 /szw-context 更新长期资产？'"
    }
  ]
}
```

### 8.3 Stop（会话结束）

```json
{
  "Stop": [
    {
      "command": "~/.szw-system/bin/check-pause-needed.sh"
    }
  ]
}
```

`check-pause-needed.sh` 逻辑：检查 STATE.md 当前 article 状态，若为 in_progress 且超过 1h 无写入，提示 `/szw-pause`。

### 8.4 路径锚定（重要）

由于 `EDITORIAL_CONTEXT.md` / `published/` / `articles/` / `editorial-adr/` 这些目录现在都在容器目录的显性层，glob `**/EDITORIAL_CONTEXT.md` 可能会匹配到非专栏路径下的同名文件。

**推荐**：每个 hook command 在执行前检测文件同级（或上层）是否存在 `.zero/szw-config.json`，作为"这是专栏目录"的锚点：

```bash
# ~/.szw-system/bin/check-is-column.sh
TARGET_FILE="$1"
DIR=$(dirname "$TARGET_FILE")
while [ "$DIR" != "/" ]; do
  if [ -f "$DIR/.zero/szw-config.json" ]; then
    echo "$DIR"; exit 0  # 找到容器根
  fi
  DIR=$(dirname "$DIR")
done
exit 1  # 不在专栏目录里
```

每个 hook 的 command 先调用它判断，再决定是否触发实际逻辑。

### 8.5 不需要 hook

- 字数统计（写完看就够）
- 拼写检查（humanizer 阶段统一）
- 自动 commit（按文章里程碑节奏，不要按每个 skill 跑）

---

## 9. 目录最终布局

**双层结构**：显性容器目录（用户起名，默认 `Column/`）+ 隐藏系统状态目录 `.zero/`。

- **显性层**：用户会直接读、改、获取启发的所有内容文件 —— 写作宪法、决策、术语、证据、灵感、文章过程产物、成品
- **隐藏层 `.zero/`**：纯系统状态（活记忆、配置、暂停 handoff）—— 机器读写为主，用户不需要日常翻看

```
Column/                                ← 显性容器目录（用户起名，默认 Column）
│
├── COLUMN.md                          ← 专栏定位（一次性，用户会偶尔读）
├── EDITORIAL_CONTEXT.md               ← 写作宪法（长期演进，用户高频翻阅 / 修改）
├── ROADMAP.md                         ← 待写选题列表（用户主动管理）
│
├── published/                         ← 已发布成品（对外）
│   ├── 2026-05-skills-vs-gsd/
│   │   ├── blog.md
│   │   ├── wechat.md
│   │   ├── x.md
│   │   └── xhs.md
│   └── quick/<slug>/
│
├── articles/                          ← 单篇文章过程目录（用户高频读 / 改 / 获取启发）
│   ├── 2026-05-skills-vs-gsd/
│   │   ├── ARTICLE.md
│   │   ├── 01-brief.md            ← /szw-discuss 产出（含 grill 拷问附录）
│   │   ├── 02-research.md         ← /szw-research 产出（evidence + diagnosis 合并）
│   │   ├── 03-outline.md          ← /szw-outline 产出（thesis map + section slices 合并）
│   │   ├── 04-draft.md            ← /szw-write 产出（最新版，覆盖式更新；draft + polish 合并）
│   │   ├── 05-review.md
│   │   ├── 06-platform-package.md
│   │   └── RETRO.md
│   ├── quick/<slug>/                  ← /szw-quick 过程产物
│   └── archived/                      ← 弃稿（保留启发价值）
│
├── editorial-adr/                     ← 决策记录（用户会读、新增、引用）
│   ├── INDEX.md
│   ├── 0001-no-benchmark-dumping.md
│   ├── 0002-tool-review-needs-action.md
│   └── ...
│
├── glossary/                          ← 单术语长定义（用户会查、改、扩）
│   ├── ai-agent.md
│   ├── agentic-coding.md
│   └── ...
│
├── inbox/                             ← 灵感库（用户会刷、挑选、补充）
│   ├── pending/                       ← /szw-capture 入口
│   └── done/                          ← 已升级为正式 article 的存根
│
├── series/                            ← 系列连载组织（用户主动管理）
│   └── agentic-coding-2026/INDEX.md
│
├── summaries/                         ← /szw-summary 周期汇总（用户会读 / 引用）
│   └── 2026-Q2.md
│
└── .zero/                             ← 隐藏，系统状态 + AI 内部参考资料 + 写作迭代日志 + 作者风格档案
    ├── STATE.md                       ← 活记忆（Active Articles 表 + Recently Completed + 计数）
    ├── szw-config.json                 ← 工作流配置（profile / hooks / limits）
    ├── .continue-here                 ← /szw-pause 暂停 handoff
    ├── style-profile.md               ← 作者风格档案（szw-review 累积，szw-write 加载）
    │
    ├── evidence/                      ← AI 修宪法/起稿时参考的证据银行
    │   ├── 2026-05-claude-code-skills.md
    │   └── retired/
    │
    ├── audits/                        ← AI 修宪法时参考的一致性审计报告
    │   └── AUDIT-2026-05.md
    │
    └── writing-history/               ← /szw-write 每次调用的快照与迭代轨迹
        └── 2026-05-skills-vs-gsd/
            ├── INDEX.md                       ← 时间线：mode / target / diff 摘要
            ├── 01-both-full-2026-05-06T10-15.md
            ├── 02-polish-S2-2026-05-06T11-30.md
            └── 03-polish-all-2026-05-06T15-20.md
```

### 9.0 `.zero/style-profile.md` 结构示例

```markdown
# Author Style Profile
> Auto-generated by /szw-review Phase 2; consumed by /szw-write Phase 1+2.
> Last updated: 2026-05-06; sample size: 12 articles, 247 edit instances.

## Stable Patterns（频次 ≥ 3，已合并）

### Vocabulary Substitutions
| AI 倾向 | 作者偏好 | 频次 | 来源 |
|---|---|---|---|
| "或许 / 可能" | 多删除（倾向断言） | 23 | 8 articles |
| "随着" | 改为具体动词 | 11 | 5 articles |
| "工程师" | "程序员" | 47 | 12 articles |

### Sentence / Rhythm
- 偏好"不是 X 而是 Y"句式（频次 19）
- 倾向短句（< 30 字）超过长句
- 段首多用具体观察句开场

### Anti-Patterns（用户反复删除）
- "在某种程度上" / "不可否认" / "在当今时代"
- 三段并列结构（"既要...也要...还要..."）

## Recent Edits（待合并的增量，每次 review 追加）
- 2026-05-06 | article: skills-vs-gsd | edit: AI 写"显著影响"被改成"重写规则"
- ...
```

### 9.1 为什么这样分？

核心原则：**用户会直接交互的内容上显性层；纯系统状态留 `.zero/`**。写作是重交互过程，中间产物本身有启发价值，让它们可见、可手改，比藏起来更符合直觉。

| 文件 / 目录 | 放哪 | 用户会直接交互吗？ | 理由 |
|---|---|---|---|
| `COLUMN.md` `EDITORIAL_CONTEXT.md` `ROADMAP.md` | 显性根 | ✅ 高频读改 | 写作宪法和路线图是长期资产，用户会反复修订 |
| `published/<slug>/` | 显性 | ✅ 拷贝 / build | 对外成品 |
| `articles/<slug>/` | 显性 | ✅ 读改启发 | 中间产物本身是思考资产；用户可直接修改 brief / draft / 拆片 |
| `editorial-adr/` | 显性 | ✅ 读 / 新增 | 决策记录要随手翻、随手引用 |
| `glossary/` | 显性 | ✅ 查 / 改 / 扩 | 术语演进是用户主动行为 |
| `inbox/` | 显性 | ✅ 刷 / 挑 / 升级 | 灵感库的价值就在于用户主动浏览 |
| `series/` `summaries/` | 显性 | ✅ 读 / 管理 | 跨周期产物，用户会回看引用 |
| `STATE.md` | `.zero/` | ❌ 机器主写 | 活记忆，每次 skill 跑都改，用户不该手动维护 |
| `szw-config.json` | `.zero/` | ❌ 通过 `/szw-config` 改 | 配置走命令，不该手改 JSON |
| `.continue-here` | `.zero/` | ❌ pause 临时态 | 下次 resume 自动消费，无需用户介入 |
| `evidence/` | `.zero/` | ❌ AI 内部参考 | 修宪法 / 起稿时 AI 自行查证；用户更关心结论而非原始证据卡 |
| `audits/` | `.zero/` | ❌ AI 内部参考 | 一致性审计报告主要喂回给 AI 修订宪法用，不需要常态展示 |
| `writing-history/` | `.zero/` | ❌ AI 写历史日志 | `/szw-write` 每次调用产生的快照；用户复盘 / 回滚时按需查阅，日常不打扰 |
| `style-profile.md` | `.zero/` | ❌ AI 累积学习 | `/szw-review` Phase 2 自动从 draft vs history diff 提取作者风格；`/szw-write` 加载时按 profile 调整。用户可读但不需要主动维护 |

### 9.2 与 git 的关系

- 整个 `Column/` 目录纳入 git 跟踪（包括 `.zero/`）
- `.zero/` 隐藏但核心资产 STATE.md 仍随仓库同步（跨设备 / 多人协作时保留状态）
- 推荐 `.gitignore` 加入：
  - `Column/.zero/.continue-here`（pause 临时态）
  - 可选：`Column/inbox/pending/`（过于碎片化的灵感不入版本）
  - 可选：`Column/.zero/writing-history/*/0[2-9]-*.md`（保留 INDEX.md 和首版快照即可，过细的迭代日志不入版本控制）

---

## 10. `szw-config.json` 配置项

```json
{
  "version": "1.0",
  "model_profile": "balanced",
  "writing_lang": "zh",
  "default_platforms": ["blog", "wechat"],
  "hooks": {
    "pre_tool_use": true,
    "post_tool_use": true,
    "stop": true
  },
  "subagents": {
    "evidence_researcher": "codex",
    "claim_diagnoser": "codex",
    "skeptical_reviewer": "codex"
  },
  "limits": {
    "review_revision_max": 2,
    "diagnose_revision_max": 2,
    "quick_word_limit": 800
  },
  "style_capture": {
    "enabled": true,
    "diff_threshold_pct": 5,
    "merge_after_n_reviews": 10,
    "min_pattern_frequency": 3
  },
  "gates": {
    "block_draft_on_missing_brief": true,
    "block_publish_on_missing_review": true,
    "auto_archive_grill_failed": false
  }
}
```

---

## 11. 与现有 skills 的集成

| 已有 | 处置 | 理由 |
|---|---|---|
| `skills/write/szw-topic-grill/` | **保留为基础**（已改名 topic-grill→szw-topic-grill），作为 `szw-discuss` Phase 1 的拷问模块 | 已写好的拷问逻辑直接复用 |
| `skills/basic/new-skills/` | 用它批量建剩余 11 个 v1.0 skill | 现成工具 |
| `skills/basic/update-skills/` | 用它迭代 skill description / trigger | 现成工具 |
| superpowers `humanizer` | `szw-write` Phase 2 内部调用 | 不重复造 |
| superpowers `episodic-memory` | 跨项目检索过往讨论 | 与专栏显性层资产（articles / glossary / evidence）互补 |
| superpowers `writing-skills` | 建本工作流 27 个 skill 时直接用 | 元工具 |
| GSD 全套 | **不在写作项目里跑** | 全局指令明确反对 |

---

## 12. 实施顺序（可执行清单）

> **核心原则**：长期资产（容器目录、COLUMN.md、EDITORIAL_CONTEXT.md、ADR、STATE.md、szw-config.json 等）由 `/szw-init` 命令自动生成——不要先手动建。所以**先写 skills，再用 skills 初始化资产**。

### Week 1：v1.0 创建入口与配置 skills

先建启动专栏所需的 skills，让 `/szw-init` 能跑起来。

- [ ] `szw-init`（最复杂，先建；含 Mode A 空目录构造 + Mode B review 已有文件；自动产出全部长期资产）
- [ ] `szw-config` / `szw-help`（配置和命令查阅基础设施）
- [ ] `szw-progress`（多 article 进度表 + 全局推荐 + `<slug>` 详情 + `--next` / `--do` / `--completed`）
- [ ] `szw-resume`（默认恢复 last_touched / `<slug>` 指定 / `--list` 多 article 切换）

### Week 2：v1.0 主流水线 skills

补齐文章流水线和长期资产维护命令。

- [ ] `szw-new-article`（文章项目化创建入口；写入 STATE.md Active Articles 表）
- [ ] `szw-discuss`（合并拷问 + 结构化两阶段，Phase 1 复用已有 szw-topic-grill 逻辑，Phase 2 产出 01-brief.md 含拷问附录）
- [ ] `szw-write`（合并 draft + edit；支持全文 / 章节模式 / `--mode draft|polish|both`；接 humanizer；写 .zero/writing-history/ 日志；加载 style-profile）
- [ ] `szw-publish`
- [ ] `szw-complete`（终结文章流水线；从 Active 移到 Recently Completed；支持 `--published` / `--archived` / `--retro`）
- [ ] `szw-context`（维护 EDITORIAL_CONTEXT 的命令，配合 szw-init 后续修订）
- [ ] `szw-adr`

### Week 3：用 `/szw-init` 初始化专栏 + 跑通真实文章

skills 就绪后再启动专栏——长期资产由 `/szw-init` 自动生成，不需要手建。

- [ ] 在目标目录下跑 `/szw-init`：
  - Mode A（空目录）→ 深度问答生成 COLUMN.md / EDITORIAL_CONTEXT.md / ADR 0001-0003 / STATE.md / szw-config.json
  - Mode B（已有散稿）→ 扫描已有内容，反推定位，逐节确认后生成
  - **可选**：若想用 [`write-progress/EDITORIAL_CONTEXT.md`](../write-progress/EDITORIAL_CONTEXT.md) 的初稿做种子，在 init 提问环节直接粘贴使用
- [ ] 选一个真实选题，从 `/szw-new-article` → `/szw-discuss` → `/szw-write` → `/szw-publish` 走完闭环（v1.0 跳过证据/诊断/拆片，直接起稿）
- [ ] 期间记录每个 skill 的产出质量、需要的修订、补丁
- [ ] 不要追求一次完美，先把闭环跑通

### Week 4：v2.0 增强 + 风格学习闭环

补齐研究 / 论证 / 反审 / 风格学习能力。

- [ ] `szw-research`（合并 evidence + diagnosis 两阶段，接 Codex；含 HIGH-risk 内部循环）
- [ ] `szw-outline`（合并 thesis-mapper + section-planner 双阶段，含弱 section 内部循环）
- [ ] `szw-review`（接 Codex；含 Phase 2 Style Capture，启动 .zero/style-profile.md 累积）
- [ ] `szw-capture` + `szw-quick`
- [ ] `szw-new-series`（系列创建入口）
- [ ] **再跑一篇文章**：完整流水线 + 验证风格学习开始累积

### Month 2：v3.0 + Hooks

- [ ] 加 hooks（保护宪法 / published / 自动同步 STATE / 检测专栏锚点）
- [ ] `szw-retro` + `szw-audit`
- [ ] `szw-glossary` + `szw-evidence-bank`
- [ ] `szw-series`（系列管理：list/status/reorder/complete）+ `szw-pause`
- [ ] `szw-stats` + `szw-summary`

---

## 13. 反模式速查

| # | 反模式 | 立即该做 |
|---|---|---|
| 1 | v1.0 还没跑通就追求 v3.0 | 把 v1.0 12 个 skill 用真实文章跑通先 |
| 2 | 把 EDITORIAL_CONTEXT 当垃圾桶 | 短规则进去；详细推理进 ADR；术语扩展进 glossary/ |
| 3 | 评审循环超过 2 轮还在修 | 升级给人裁决，不要无限回环 |
| 4 | quick 写到 1500 字硬塞 | 升级 `/szw-new-article`，走完整流水线 |
| 5 | 为了"完整"每篇都跑全 11 步 | 短评 `/szw-quick`；常规文章可以跳 evidence/diagnose 的灵活 |
| 6 | 跨 session 不读 STATE 直接动手 | 强制 `/szw-resume` 第一步 |
| 7 | published/ 文件被手改 | 回 `/szw-write` 修源稿，重跑 `/szw-publish` 重新生成各平台版本 |
| 8 | ADR 编号撞车 | INDEX.md 自动维护编号，禁止手改 |
| 9 | 灵感打断当前文章 | `/szw-capture` 入队 |
| 10 | hooks 报警就关 hooks | 报警就处理；hooks 是质量保险 |

---

## 14. 与 GSD 的对齐速查

| GSD 命令 | col 等价物 | 备注 |
|---|---|---|
| `/gsd-new-project` | `/szw-init` | 一次性初始化（含 Mode A 空目录 / Mode B review 已有文件双模式） |
| `/gsd-discuss-phase` + `/gsd-plan-phase`（部分） | `/szw-discuss` | 拷问 + brief 结构化合并到一步 |
| `/gsd-plan-phase`（剩余） | `/szw-outline` | 论证设计（thesis + slice 合并） |
| `/gsd-execute-phase` | `/szw-write` | 执行（draft + edit 合并；支持全文 / 章节模式 + 写作历史日志） |
| `/gsd-verify-work` | `/szw-research` + `/szw-review` | 验证（research 包含 evidence + diagnosis） |
| `/gsd-ship` | `/szw-publish` | 发布 |
| `/gsd-progress` | `/szw-progress` | 路由 |
| `/gsd-resume-work` | `/szw-resume` | 恢复 |
| `/gsd-pause-work` | `/szw-pause` | 暂停 |
| `/gsd-capture` | `/szw-capture` | 捕获 |
| `/gsd-quick` | `/szw-quick` | 轻量 |
| `/gsd-help` | `/szw-help` | 参考 |
| `/gsd-config` | `/szw-config` | 配置 |
| `/gsd-review` | `/szw-review` | 反审 |
| `/gsd-extract-learnings` | `/szw-retro` | 复盘 |
| `/gsd-audit-milestone` | `/szw-audit` | 审计 |
| `/gsd-stats` | `/szw-stats` | 统计 |
| `/gsd-milestone-summary` | `/szw-summary` | 汇总 |
| `/gsd-new-milestone` | `/szw-new-series` | 系列创建（管理用 `/szw-series`） |

GSD 65 个 skill → col 27 个 skill。差距来自：

- 写作不需要 worktree / wave 并行（论证强串联）
- 写作不需要 60% 覆盖率 / nyquist / security audit（不是代码）
- 写作不需要 PR branch 过滤 / inbox triage（发布 = 复制粘贴或对接 API）

---

## 15. 决策原因（meta）

为什么不直接用 GSD 处理写作？

1. **`.planning/` 噪声**：用户全局指令明确反对在 vault/写作场景跑 GSD
2. **Phase/Plan/Task 错位**：写作的层级感是 Article > Section > Claim，强行套 phase 模型反而误导
3. **wave 并行无 ROI**：论证有强先后顺序，并行省不了时间
4. **atomic commits 频率不匹配**：写作是迭代式打磨，不是任务点状交付

为什么不直接用 superpowers？

1. **没有持久化记忆**：每次会话从零开始，术语漂移
2. **没有专栏概念**：每篇文章孤立，没有长期资产
3. **brainstorming 太通用**：写作选题需要专门的拷问框架（szw-topic-grill）

所以建一套**专为技术专栏设计**的 27 个命令，借用 GSD 的"持久化 + 子 agent + gates"思想，但绕开它的过度工程。

---

## 16. 下一步

阅读完本文档后，建议：

1. **确认命名前缀**：用 `/szw-*` 还是 `/write-*` 或其他？（影响所有后续 skill 名）
2. **确认 v1.0 范围**：12 个命令是否正好？要不要再砍到 8-10 个？
3. **确认中文 vs 英文 skill name**：description 用英文（agent 路由匹配更稳），但 SKILL.md 内部内容可以中英混排
4. **确认实施顺序**：是按 Week 1-4 顺序，还是先建几个最高频的（grill / draft / edit / package）跑起来再扩

确认后即可进入 `~/.claude/skills/szw-*/SKILL.md` 批量创建阶段。

---

## 附 A：参考资料

- 本 repo 的 GSD 调研：[`gsd-research.md`](./gsd-research.md) §4（命令分类）+ §5（核心机制）
- 本 repo 的写作建议：[`writing-workflow-proposal.md`](./writing-workflow-proposal.md)
- 写作流程草稿：[`../write-progress/flow.md`](../write-progress/flow.md)
- 写作宪法草稿：[`../write-progress/EDITORIAL_CONTEXT.md`](../write-progress/EDITORIAL_CONTEXT.md)
- 决策记录草稿：[`../write-progress/ADR.md`](../write-progress/ADR.md)
- GSD 命令权威：`~/.claude/get-shit-done/workflows/help.md`
- GSD agent 协议：`~/.claude/get-shit-done/references/agent-contracts.md`
- mattpocock/skills（grill-me / CONTEXT / ADR / diagnose / to-issues / caveman / write-a-skill）
