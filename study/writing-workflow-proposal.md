# 技术专栏写作工作流建议

> 综合来源：
> - 调研报告 [`gsd-research.md`](./gsd-research.md) / [`gsd-workflow-guide.md`](./gsd-workflow-guide.md)
> - 写作流程草稿 [`../write-progress/flow.md`](../write-progress/flow.md)
> - 写作宪法草稿 [`../write-progress/EDITORIAL_CONTEXT.md`](../write-progress/EDITORIAL_CONTEXT.md)
> - 决策记录草稿 [`../write-progress/ADR.md`](../write-progress/ADR.md)
>
> 目标：把 GSD 的「流程纪律 + 跨 session 记忆」机制，迁移到「技术行业分析 + 给程序员的建议」长期写作场景，但**不用 GSD 本身**。
>
> 编写日期：2026-05-06

---

## TL;DR

1. **不要在写作项目里跑 GSD**。GSD 是为代码工程设计的，phase/plan/task 模型对单篇文章过重；vault 全局指令也明确禁止。
2. **借用 GSD 的三件核心装备**：(a) 文件持久化的活记忆，(b) 子 agent 完成 marker 协议，(c) 梯度入场。
3. **核心心智模型**：`Column → Article → Section → Claim` 四层（对应 GSD 的 `Project → Milestone → Phase → Plan`）。
4. **持久化目录** `.column/`（对应 GSD 的 `.planning/`）：长期资产 + 每篇文章独立目录 + 跨 session 状态。
5. **三类 skill**：长期资产维护（editorial-context / editorial-adr）、单篇流水线（topic-grill / industry-brief / evidence-research / claim-diagnose / thesis-map / section-slicer / draft / skeptical-review / human-editor / dense-summary / platform-packager）、复盘归档（editorial-retro / extract-learnings）。
6. **梯度入场**：碎片想法 `/capture` → 短评 `/dense-summary` 直出 → 标准文章走完整流水线 → 系列文章升级到 milestone 层。

---

## 1. 为什么需要一套写作工作流（而不是直接写）

技术专栏长期运行会撞上和 GSD 设计动机几乎一样的几个问题：

| GSD 解决的代码场景问题 | 写作场景的对应问题 |
|---|---|
| Context rot：单一 session 写久了质量衰减 | 单次对话写文章，到尾段 AI 容易走风、漂术语 |
| session 间无共享记忆 | 上一篇定的"AI Agent"定义，下一篇被 AI 重写 |
| 缺乏可审计的开发记录 | 半年后回看不知道某条选题策略为什么定 |
| 多任务并行混乱 | 选题、起稿、审稿、复盘混在一个会话里互相污染 |
| trivial 任务也走重流程 | 一句话短评和长篇行业分析用同一套开销 |

写作的特殊难点（GSD 没有的）：

- **观点漂移**：同一个词跨文章定义不一致
- **取舍漂移**：以前定下"不写焦虑文"，几个月后忘了又写了一篇
- **证据腐烂**：去年的 benchmark 不能直接当今天的事实
- **多平台差异**：博客版 / 公众号版 / 小红书版需要不同包装但同一套事实

所以写作系统不是简化版 GSD，而是一个**侧重"长期世界观维护 + 单篇严格论证"**的工作流。

---

## 2. 心智模型：四层结构

```
Column（专栏）                   ← 一次性建立，长期演进
├── EDITORIAL_CONTEXT.md         ← 世界观/术语/边界（"宪法正文"）
├── editorial-adr/               ← 决策记录（"立法记录"）
└── Series（系列，可选）         ← 同主题多篇文章
    └── Article（单篇文章）      ← /article-new 触发
        ├── 00-topic-grill.md
        ├── 01-brief.md
        ├── 02-evidence-cards.md
        ├── 03-claim-diagnosis.md
        ├── 04-thesis-map.md
        ├── 05-section-slices.md
        ├── 06-draft-v1.md
        ├── 07-review.md
        ├── 08-draft-v2.md
        └── 09-platform-package.md
            └── Section（节）    ← 一个独立可成立的论证切片
                └── Claim（判断）← 一节里 1 个核心 claim
```

对应 GSD：

| 写作 | GSD | 含义 |
|---|---|---|
| Column | Project | 长期愿景 + 价值主张，一次定型基本不动 |
| Series | Milestone | 同主题多篇连载（可选） |
| Article | Phase | 一篇文章 = 一个完整工作单元 |
| Section | Plan | 一篇内部可并行处理的论证切片 |
| Claim | Task | 一节内部可单独验证的判断单位 |

**关键差异**：写作的 Section 之间逻辑串联强、并行价值低（一个论证依赖前一个铺垫），所以不需要 GSD 那种 wave-based 真并行；但单节内部的 evidence 收集、reviewer 对照可以并行。

---

## 3. 持久化目录约定

模仿 GSD 的 `.planning/`，建议在博客 repo 根建：

```
.column/
├── COLUMN.md                ← 专栏定位（一次写就基本不动）= GSD 的 PROJECT.md
├── EDITORIAL_CONTEXT.md     ← 写作宪法 = GSD 的 STATE.md + 术语表
├── ROADMAP.md               ← 待写选题列表 + 优先级（可选）
├── STATE.md                 ← 当前在写哪篇 / 当前阶段 / 待办（活记忆）
├── editorial-adr/           ← 决策记录
│   ├── 0001-no-benchmark-dumping.md
│   ├── 0002-tool-review-needs-action.md
│   └── ...
├── glossary/                ← 术语单独建文件（避免 EDITORIAL_CONTEXT 太长）
│   ├── ai-agent.md
│   ├── agentic-coding.md
│   └── ...
├── evidence/                ← 跨文章可复用的证据卡
│   ├── 2026-05-claude-code-skills.md
│   └── ...
├── inbox/                   ← /capture 进来的碎片想法
│   ├── pending/
│   └── done/
├── series/                  ← 系列连载（可选）
│   └── agentic-coding-2026/
│       └── INDEX.md
├── articles/                ← 每篇文章独立目录
│   ├── 2026-05-skills-vs-gsd/
│   │   ├── ARTICLE.md       ← 元数据（status / thesis / target_platform）
│   │   ├── 00-topic-grill.md
│   │   ├── 01-brief.md
│   │   ├── 02-evidence-cards.md
│   │   ├── 03-claim-diagnosis.md
│   │   ├── 04-thesis-map.md
│   │   ├── 05-section-slices.md
│   │   ├── 06-draft-v1.md
│   │   ├── 07-review.md
│   │   ├── 08-draft-v2.md
│   │   ├── 09-platform-package.md
│   │   └── RETRO.md         ← 发布后复盘
│   └── ...
├── published/               ← 已发布版本（按平台分版本）
│   └── 2026-05-skills-vs-gsd/
│       ├── blog.md
│       ├── wechat.md
│       └── xhs.md
└── archived/                ← 弃稿（保留以便回顾）
```

**核心设计原则**（沿用 GSD 思想）：

1. **STATE.md 是活记忆**：跨 session 第一件事读它，不要重读所有文章。
2. **每篇文章一个目录**：阶段产物全留档，方便 forensics（"为什么这篇 thesis 改了三次"）。
3. **长期资产与单次产物分离**：`EDITORIAL_CONTEXT.md` / `editorial-adr/` / `glossary/` / `evidence/` 跨文章共享。
4. **published/ 与 articles/ 分离**：drafts 留全过程，published 只留可直接发布的成品。

---

## 4. 主流程（happy path）

完整一篇行业分析文从想法到发布，11 步流水线（参考 [`flow.md`](../write-progress/flow.md) §7）：

| 步 | 命令 | 实际做什么 | 关键产物 | 衔接 |
|---|---|---|---|---|
| 0 | `/capture "<想法>"` | 灵感入 inbox，不打断当前工作 | `.column/inbox/pending/<slug>.md` | 后续 `/article-new --from-inbox` |
| 1 | `/article-new "<标题>"` | 创建文章目录 + ARTICLE.md 元数据 | `.column/articles/<slug>/ARTICLE.md` | 进入 topic-grill |
| 2 | `/topic-grill` | 拷问选题，逼出真正命题 | `00-topic-grill.md` | 不通过则 → archived/ |
| 3 | `/industry-brief` | 生成文章 brief：读者/误解/核心判断/边界 | `01-brief.md` | 进入证据 |
| 4 | `/evidence-research` | 收集证据卡（建议用 Codex 跑） | `02-evidence-cards.md` + 复用 `.column/evidence/` | 进入诊断 |
| 5 | `/claim-diagnose` | 诊断判断是否站得住（建议用 Codex 跑） | `03-claim-diagnosis.md` | 不通过 → 回 4 补证据 |
| 6 | `/thesis-map` | 形成论证地图 | `04-thesis-map.md` | 进入拆片 |
| 7 | `/section-slicer` | 拆成多个独立成立的 section slices | `05-section-slices.md` | 进入起稿 |
| 8 | `/article-draft` | 写初稿 | `06-draft-v1.md` | 进入审稿 |
| 9 | `/skeptical-review` | 反方审稿（建议用 Codex / 跨 AI） | `07-review.md` | 有 HIGH 问题 → 回 8 |
| 10 | `/human-editor` | 二稿润色，过 humanizer | `08-draft-v2.md` | 进入打包 |
| 11 | `/platform-packager` | 输出博客 / 公众号 / X / 小红书版本 | `09-platform-package.md` + `published/<slug>/*` | 发布 |
| 12 | `/editorial-retro` | 发布后复盘，必要时更新 EDITORIAL_CONTEXT 或建 ADR | `RETRO.md` + 可能的 ADR/术语更新 | 闭环 |

**Gate 设计**（沿用 GSD 思想）：

- **Pre-flight gate**：`/article-draft` 之前必须完成 topic-grill + brief + section-slicer（拒绝跳步起稿）
- **Revision gate**：`/claim-diagnose` 报 HIGH 风险 → 回 evidence-research（最多 2 轮，超出升级给人）
- **Escalation gate**：术语在文章里和 EDITORIAL_CONTEXT 冲突 → 暂停问人："是改文章还是改宪法？"
- **Abort gate**：topic-grill 后发现选题与 ADR 0001（不做 benchmark 搬运）冲突 → 直接归档到 archived/

---

## 5. Skills 清单

按优先级和角色分组。每个 skill 应该是 `~/.claude/skills/<name>/SKILL.md` 单独文件，frontmatter 写清触发条件。

### 5.1 必备最小集（5 个，第一阶段就建）

来源：[`flow.md`](../write-progress/flow.md) §10。

| Skill | 角色 | 描述 | 跑在 |
|---|---|---|---|
| `topic-grill` | 选题拷问 | 写前一对一拷问选题，逼出核心命题（已有，[skills/write/topic-grill](../skills/write/topic-grill/SKILL.md)） | Claude |
| `editorial-context` | 宪法维护 | 维护 `.column/EDITORIAL_CONTEXT.md` 和 `glossary/`，挑战模糊词 | Claude |
| `evidence-research` | 证据采集 | 查官方文档 / 源码 / 发布说明，产出可复用 evidence cards | **Codex** |
| `claim-diagnose` | 判断诊断 | 拆每个 claim，分类（fact/interpretation/opinion/prediction/advice），降级表达 | **Codex** |
| `human-editor` | 二稿润色 | 过 humanizer 风格，去 AI 腔，加判断锐度 | Claude |

### 5.2 进阶集（6 个，跑顺最小集后加）

| Skill | 角色 | 描述 | 跑在 |
|---|---|---|---|
| `industry-brief` | 文章 brief | 把拷问结果产出结构化 brief（读者/误解/核心判断/边界） | Claude |
| `thesis-map` | 论证地图 | 把 brief 转成主线论证图（thesis + 3-5 supporting + counter） | Claude |
| `section-slicer` | 文章拆片 | 按 vertical slice 拆成可独立成立的 section（不是横向 background/analysis） | Claude |
| `article-draft` | 初稿 | 按 section-slices 写初稿，每节自带 acceptance criteria 自检 | Claude |
| `skeptical-review` | 反方审稿 | 技术审稿 + 反方质疑 + 事实边界审查 | **Codex** |
| `editorial-adr` | 决策记录 | 创建 / 更新长期内容策略 ADR，同步 EDITORIAL_CONTEXT | Claude |

### 5.3 平台化与复盘（3 个，稳定后加）

| Skill | 角色 | 描述 | 跑在 |
|---|---|---|---|
| `dense-summary` | 高密度摘要 | TL;DR / 公众号首屏 / X thread 第一条 / 小红书首屏 | Claude |
| `platform-packager` | 多平台打包 | 同一事实 + 多套包装（博客/公众号/X/小红书），分版本写到 `published/` | Claude |
| `editorial-retro` | 发布复盘 | 数据 + 反馈整理；触发 ADR 候选 / 术语更新 / 选题策略调整 | Claude |

### 5.4 长期可选（4 个，按需加）

| Skill | 用途 |
|---|---|
| `capture` | 灵感入 inbox（仿 `gsd-capture`），不打断当前工作 |
| `zoom-out-topic` | 从单工具跳到行业结构（仿 mattpocock zoom-out） |
| `extract-learnings` | 从已发布文章抽 patterns / 失败 / 复用的桥段 |
| `series-orchestrator` | 多篇连载主线 + 节奏管理（对应 GSD milestone） |

### 5.5 路由 / 进度 skill（仿 gsd-progress）

| Skill | 用途 |
|---|---|
| `column-progress` | 默认显示当前 STATE.md + 推荐下一步；`--next` 自动推进；`--do "<text>"` 自然语言路由到对应 skill |
| `column-resume` | 跨 session 第一件事，读 STATE.md + 当前 article 的最近一份 .md，恢复上下文 |

---

## 6. 子 agent 建议

GSD 注册了 ~20 个专用子 agent，每个有完成 marker。写作场景规模小很多，建议只设计 **6 个**（参考 GSD `agent-contracts.md`）：

| Agent | 角色 | Completion marker | 触发 skill |
|---|---|---|---|
| `topic-grill-interviewer` | 选题拷问，最多 N 轮 | `## GRILL COMPLETE / ABORTED` | topic-grill |
| `evidence-researcher` | 证据采集，独立子上下文（避免污染主稿） | `## EVIDENCE COMPLETE / BLOCKED` | evidence-research |
| `claim-diagnoser` | 判断诊断，独立子上下文 | `## DIAGNOSIS PASSED / ISSUES FOUND` | claim-diagnose |
| `section-planner` | 拆片 + 验证每节自洽 | `## SLICES COMPLETE / NEEDS REWORK` | section-slicer |
| `skeptical-reviewer` | 反方审稿（建议跑 Codex 拿独立视角） | `## REVIEW COMPLETE` 含 HIGH/MED/LOW 分类 | skeptical-review |
| `humanizer-editor` | 风格审，去 AI 腔 | `## HUMANIZED / NEEDS MANUAL` | human-editor |

**关键纪律**（来自 GSD `references/agent-contracts.md`）：

- 每个 agent 在独立子 session 里跑，主对话只看产物 markdown，不看过程，避免上下文翻倍
- 完成 marker 必须是 H2 标题，主对话用 regex 匹配判断完成
- 失败要写明 reason，不能只说"failed"

---

## 7. Hooks 建议

GSD 没有显式用 Claude Code hooks，但写作场景有几个**确定性事件**适合 hook 化（参考 `~/.claude/rules/common/hooks.md`）：

### 7.1 PreToolUse hooks（保护性）

| 触发 | 动作 | 理由 |
|---|---|---|
| Write/Edit 即将写到 `.column/EDITORIAL_CONTEXT.md` | 提示"这是宪法文件，确认要直接改？建议走 `/editorial-context` 或建 ADR" | 防止主稿过程中误改长期资产 |
| Write/Edit 即将写到 `published/` | 阻止 + 提示走 `/platform-packager` | published/ 应该是流水线产物，不该手改 |
| Bash 即将跑 `git push` 而当前 article status ≠ `published` | 提示确认 | 防止半成品上 GitHub Pages |

### 7.2 PostToolUse hooks（自动化）

| 触发 | 动作 | 理由 |
|---|---|---|
| Write 写入 `.column/articles/<slug>/06-draft-v1.md` | 自动更新 `STATE.md` 把该 article 推进到 `draft_done` | 替代手动维护状态 |
| Write 写入 `editorial-adr/NNNN-*.md` | 自动追加链接到 EDITORIAL_CONTEXT 的相关 section | ADR 与宪法同步 |
| Write 写入任何 `articles/*/RETRO.md` | 触发提示"是否要新建 ADR / 更新术语？" | 复盘强制反哺长期资产 |

### 7.3 Stop hook（会话结束）

| 触发 | 动作 |
|---|---|
| session 结束 | 检查 STATE.md 是否反映当前进度；若 article 在 in_progress 状态但近 1h 无写入，提示 `/column-pause` 留 handoff |

### 7.4 不需要 hook 的场景

- 文章字数统计（写完再看就够）
- 拼写检查（humanizer 阶段统一处理）
- 自动 commit（写作场景每个阶段一个 commit 没意义，按文章里程碑 commit 即可）

---

## 8. 其他工具

### 8.1 episodic-memory（已装）

**用法**：写"上一篇我是怎么处理 XX 主题的？" / "之前讨论过 Skills 定义吗？" 时优先查。
**与 EDITORIAL_CONTEXT 的关系**：episodic-memory 是过程记忆（讨论了什么），EDITORIAL_CONTEXT 是结论记忆（决定了什么）。

### 8.2 humanizer skill（已装）

**用法**：`/human-editor` 流水线步骤里调用，去 AI 腔，避免对外内容里出现 list 化、平行化、装饰性表达。

### 8.3 跨 AI 评审（仿 `gsd-review`）

**Claude 写主稿，Codex 做 evidence-research / claim-diagnose / skeptical-review** 的分工已经在 [`flow.md`](../write-progress/flow.md) 里建议过。理由：

- Codex 的查证、找反例、核对来源能力更强
- 跨 AI 视角能避免 Claude 被自己的论证逻辑套牢
- 写作 ≠ 编码，证据偏离比代码 bug 更难自检

具体实现可以借助本 repo 已有的 `codex:rescue` 子 agent 或 `gsd-review` skill 的跨 AI 调用机制（哪怕不用 GSD 主流程）。

### 8.4 git commit 节奏

不用 GSD 的"每 task 一 commit"。建议节奏：

| Commit 时机 | 消息格式 |
|---|---|
| 文章目录创建 | `article: start <slug>` |
| brief / thesis-map / section-slices 三阶段产物完成 | `article(<slug>): plan` |
| draft v1 / v2 完成 | `article(<slug>): draft v1` / `draft v2` |
| 发布 | `article(<slug>): publish` |
| 长期资产更新 | `editorial: add ADR 0009` / `editorial: update glossary <term>` |

---

## 9. 跨 session 记忆机制

这是从 GSD 借来最有价值的部分。

### 9.1 三层记忆

| 层 | 文件 | 寿命 | 跨 session |
|---|---|---|---|
| L1 活记忆 | `.column/STATE.md` | 当前进行中 | ✅ 必读 |
| L2 决策记忆 | `.column/EDITORIAL_CONTEXT.md` + `editorial-adr/` + `glossary/` | 长期 | ✅ 选读 |
| L3 过程记忆 | `articles/<slug>/*.md` 历史阶段产物 | 永久归档 | ✅ 按需 |

### 9.2 STATE.md 模板

```markdown
# Column STATE

> Updated: 2026-05-06

## Current Article
- Slug: 2026-05-skills-vs-gsd
- Status: section-slicer-done → article-draft 待启动
- Path: .column/articles/2026-05-skills-vs-gsd/
- Thesis: Skills 是轻量可组合的 agent 能力单元，与 GSD 的"接管流程"形成互补关系

## Pending
- [ ] /article-draft 起初稿
- [ ] 等 Codex 完成 evidence-cards 二轮补证（缺 mattpocock skills 的 README 引用）

## Recent Decisions
- (2026-05-06) ADR 0009: AI coding tool 对比优先比 workflow fit，不比模型强弱

## Backlog（接下来想写的选题）
- AGENTS.md 会成为跨 AI 工具的标准吗？
- 程序员的"AI 协作能力"到底指什么？
```

### 9.3 跨 session 启动 SOP

新会话第一件事（仿 `/gsd-resume-work`）：

```
/column-resume
↓
读 .column/STATE.md
读 当前 article 的最新一份 .md
读 EDITORIAL_CONTEXT.md（前 5 节）
↓
报告：当前在哪、推荐下一步
```

不要做：从 0 开始重新读 COLUMN.md / 全部 ADR / 所有文章。STATE.md 已经是浓缩活记忆。

---

## 10. 梯度入场

模仿 GSD 的 fast/quick/full 梯度，写作有 4 档：

```
碎片想法            短评 / 推文                标准文章                      系列连载
≤30 字             ≤500 字                   1500-3500 字                  3+ 篇连载
1 分钟             10 分钟                   2-5 小时（跨 session）        多周

/capture     →     /dense-summary 直出   →   完整 11 步流水线         →   /series-orchestrator
```

### 10.1 何时升档

- `/capture` 攒到 5+ 条同主题 → 升 `/article-new`
- 一个 brief 写到一半发现要拉 3+ 个证据点、要批驳 2+ 个流行误解 → 走完整流水线（不要硬塞短评）
- 一个文章已经写到 v2 发现 thesis 撑不下要拆 → 升 series

### 10.2 不要做（反模式）

- ❌ trivial 想法跑完整 11 步流水线（拷问 1 分钟想法浪费时间）
- ❌ 标准文章跳过 topic-grill 直接 draft（会写到一半发现命题不成立）
- ❌ 同主题 5 篇文章不建 series，每篇重新建立术语和论证基线

---

## 11. 模型 profile 建议

参考 GSD `gsd-config --profile` 的思路：

| 阶段 | 推荐模型 | 理由 |
|---|---|---|
| topic-grill / brief / thesis-map | **Opus** | 决定文章基调，质量优先 |
| evidence-research | **Codex / Sonnet** | 查证密集，需要 Codex 的检索能力 |
| claim-diagnose | **Codex / Opus** | 反例与核查，要深度推理 |
| section-slicer | **Opus** | 论证拆片是文章核心，质量优先 |
| article-draft | **Sonnet** | 大量产出，性价比最优 |
| skeptical-review | **Codex** | 跨 AI 拿独立视角，避免自洽偏差 |
| human-editor | **Opus** | 风格判断敏感 |
| dense-summary / platform-packager | **Sonnet / Haiku** | 模板化产出 |
| editorial-retro | **Sonnet** | 整理为主 |

**默认配置**：日常 `balanced`（Opus 规划阶段 + Sonnet 执行阶段）；商业关键专栏起步阶段 `quality`（处处 Opus）；预算紧 `budget`（Sonnet + Haiku，evidence/claim 仍跑 Codex）。

---

## 12. 与 GSD / superpowers 的关系

### 12.1 不要叠用 GSD

- GSD 的 PROJECT/REQUIREMENTS/PHASE/PLAN/TASK 模型对单篇文章过重
- `.planning/` 目录在 vault/写作项目里只产生噪声（用户全局指令明确反对）
- GSD 的 wave-based 并行在写作场景没有 ROI（论证强串联）
- GSD 的 atomic commits 强度不适合写作节奏

### 12.2 不要叠用 superpowers 的工程化 skill

| superpowers skill | 在写作场景的等价物 / 替代 |
|---|---|
| `brainstorming` | `topic-grill`（已经更针对写作） |
| `test-driven-development` | 不适用（"写测试再写代码"在写作里换成"先 thesis 后 evidence"，由 brief→evidence 流程承担） |
| `verification-before-completion` | `claim-diagnose` + `skeptical-review` |
| `writing-plans` | `thesis-map` + `section-slicer` |
| `requesting-code-review` | `skeptical-review`（反方审稿，跨 AI） |

### 12.3 仍然有价值的 superpowers / 工具

- `humanizer` —— `/human-editor` 内部调用
- `episodic-memory` —— 跨项目检索过往讨论
- `writing-skills` —— 创建本工作流里的 12 个 skill 时直接用
- `dispatching-parallel-agents` —— evidence-research 拆并行子查询时用

### 12.4 何时彻底放弃工作流

- 一句话短评（直接 `/dense-summary`）
- 临时回复别人评论
- 转载附短按语
- 5 分钟内能写完的东西

不要为了"统一"硬上流水线。

---

## 13. 反模式速查

按"后悔率"从高到低排序。识别到立即停下。

| # | 反模式 | 立即该做 |
|---|---|---|
| 1 | 写作项目里跑 GSD（建 `.planning/`） | 立刻 `rm -rf .planning/`，回 `.column/` |
| 2 | 跳过 topic-grill 直接 draft | 回 topic-grill；直接起稿的文章 80% 后期会推翻 thesis |
| 3 | 单篇文章里直接改 EDITORIAL_CONTEXT | 走 `/editorial-context` 或建 ADR；宪法不该被某篇文章污染 |
| 4 | evidence-research 用主对话（Claude 自查自证）| 切 Codex；自查容易自我合理化 |
| 5 | claim-diagnose 报 HIGH 还是硬发 | 回补证据或降级表达，不要赌读者发现不了 |
| 6 | 同主题 5 篇没建 series 也没建 ADR | 至少建 ADR 锁定关键术语和论证边界 |
| 7 | 每次新会话从头读所有文章 | 用 `/column-resume`，STATE.md 是浓缩活记忆 |
| 8 | published 文件被手改 | 走 `/platform-packager` 重新生成；published 是流水线产物 |
| 9 | 灵感不入 inbox 直接打断当前文章 | `/capture` 入队，写完手头再处理 |
| 10 | 一篇文章拖 2 周不发，状态没更新 | 要么 `/column-pause` 留 handoff，要么直接 archived/ |
| 11 | 复盘后不更新长期资产 | retro 必须导出 ADR 候选 / 术语候选 / 选题策略候选 |
| 12 | 用流水线写 100 字短评 | `/dense-summary` 直出 |

---

## 14. 学习路径

第一次搭建写作系统的顺序建议：

1. **必读 3 篇**（已在本 repo）：
   - [`flow.md`](../write-progress/flow.md) §1-7（流程框架）
   - [`EDITORIAL_CONTEXT.md`](../write-progress/EDITORIAL_CONTEXT.md) §1-9（宪法核心）
   - [`ADR.md`](../write-progress/ADR.md) §1-5（决策记录机制）

2. **建立长期资产**（1 天内做完）：
   - 写 `.column/COLUMN.md`（参考 EDITORIAL_CONTEXT §1 Column Positioning）
   - 写 `.column/EDITORIAL_CONTEXT.md` 最小版本（7 节即可）
   - 建 3 条核心 ADR（不做 benchmark / 工具评测落到行动 / 不做焦虑文）

3. **建立最小 skills**（5 个，已在 [`flow.md`](../write-progress/flow.md) §10 列出）：
   - topic-grill（已有）
   - editorial-context
   - evidence-research（Codex）
   - claim-diagnose（Codex）
   - human-editor

4. **跑通一篇文章**：用真实选题走完 11 步流水线，期间补 STATE.md 模板

5. **稳定后扩**：补进阶集 + 平台化集，建立跨 session SOP

不要一上来就建 12 个 skill + 4 类 hook，会被淹没在工具搭建里反而不写文章。

---

## 15. 与现有 repo 的衔接

当前 [`zero-to-ai`](..) repo 已有：

| 已有 | 建议下一步 |
|---|---|
| `skills/write/topic-grill/SKILL.md` | 保留，作为最小集第 1 个 |
| `skills/basic/new-skills/` `update-skills/` | 用它们来批量建剩余 11 个 skill |
| `study/gsd-research.md` `gsd-workflow-guide.md` | 本文档作为第三个研究产物 |
| `write-progress/{flow,EDITORIAL_CONTEXT,ADR}.md` | 整理后迁到 `.column/`（flow 进 study/，EDITORIAL_CONTEXT 和 ADR 模板成为正式资产） |

建议优先级：

1. **第一周**：建 `.column/` 目录骨架 + 写 COLUMN.md / EDITORIAL_CONTEXT.md / 3 条核心 ADR
2. **第二周**：补齐最小 5 个 skill（用 `skills/basic/new-skills`）
3. **第三周**：跑通 1 篇真实文章流水线，建立 STATE.md 模板
4. **第四周**：复盘 + 补进阶 skill + 加 hooks

---

## 附 A：与 GSD 的对比速查

| 维度 | GSD | 本写作工作流 |
|---|---|---|
| 适用 | 多周代码项目 | 长期技术专栏 |
| 持久化目录 | `.planning/` | `.column/` |
| 心智层级 | Project → Milestone → Phase → Plan → Task | Column → Series → Article → Section → Claim |
| 活记忆 | STATE.md | STATE.md（同名） |
| 长期决策 | RETROSPECTIVE.md | EDITORIAL_CONTEXT.md + editorial-adr/ |
| 阶段产物 | CONTEXT/SPEC/PLAN/SUMMARY/VERIFICATION | topic-grill/brief/evidence/diagnosis/thesis/slices/draft/review/package |
| 子 agent 数 | ~20 | 6 |
| Wave 并行 | wave-based 真并行 | 不用（论证强串联） |
| Atomic commits | 每 task 一 commit | 文章里程碑级 commit |
| Worktree 隔离 | 默认开 | 不用（写作不冲突） |
| 跨 AI 评审 | gsd-review | skeptical-review（同思想） |
| Gates | pre-flight / revision / escalation / abort | 同 4 类 |
| 模型 profile | quality/balanced/budget/inherit | 阶段化分配（见 §11） |
| 梯度 | fast/quick/full/autonomous | capture/dense-summary/full/series |

---

## 附 B：MVP 快速启动清单

把本文落到行动，最小可用版本如下：

```
zero-to-ai/
├── .column/
│   ├── COLUMN.md                           ← 参考 EDITORIAL_CONTEXT.md §1
│   ├── EDITORIAL_CONTEXT.md                ← 7 节最小版（拷贝 write-progress/EDITORIAL_CONTEXT.md §八）
│   ├── STATE.md                            ← 参考本文 §9.2 模板
│   ├── editorial-adr/
│   │   ├── 0001-no-benchmark-dumping.md
│   │   ├── 0002-tool-review-needs-action.md
│   │   └── 0003-no-anxiety-farming.md
│   ├── inbox/pending/
│   └── articles/
└── skills/write/
    ├── topic-grill/                        ← 已有
    ├── editorial-context/                  ← 待建
    ├── evidence-research/                  ← 待建（Codex）
    ├── claim-diagnose/                     ← 待建（Codex）
    └── human-editor/                       ← 待建
```

跑通一篇真实文章后再决定要不要扩到 12 skill / 4 hook 完整体系。

---

## 附 C：参考资料

- 本 repo 的 GSD 调研：[`gsd-research.md`](./gsd-research.md) / [`gsd-workflow-guide.md`](./gsd-workflow-guide.md)
- 写作流程草稿：[`../write-progress/flow.md`](../write-progress/flow.md)
- 写作宪法草稿：[`../write-progress/EDITORIAL_CONTEXT.md`](../write-progress/EDITORIAL_CONTEXT.md)
- 决策记录草稿：[`../write-progress/ADR.md`](../write-progress/ADR.md)
- mattpocock/skills（flow.md 里多次引用）：grill-me / CONTEXT.md / ADR / diagnose / to-issues / caveman / write-a-skill
- GSD 命令权威参考：`~/.claude/get-shit-done/workflows/help.md`
- GSD agent 注册表：`~/.claude/get-shit-done/references/agent-contracts.md`
- 全局指令：`~/.claude/CLAUDE.md`（项目类型识别 + 反模式速查）
