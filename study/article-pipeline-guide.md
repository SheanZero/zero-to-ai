# 文章主流水线深度指南

> 配套文档：[`writing-workflow-blueprint.md`](./writing-workflow-blueprint.md)
> 范围：v1.0 + v2.0 文章主流水线 7 步（不含 `/szw-new-article` 创建入口、不含轻量出口 `/szw-quick`）。
> 编写日期：2026-05-06
> 修订记录：
> - 2026-05-06 a：原 `szw-grill` + `szw-brief` 合并为单步，参与度合并取高（★★★★★）
> - 2026-05-06 b：合并后命令改名为 `/szw-discuss`（更准确反映"讨论拷问"动作语义）；产物文件名仍为 `01-brief.md`
> - 2026-05-06 c：原 `szw-evidence` + `szw-diagnose` 合并为 `/szw-research`（双 Codex 阶段 + HIGH-risk 内部循环）；产物 `02-research.md` 替代原 `02-evidence-cards.md` + `03-claim-diagnosis.md`；后续阶段产物文件序号统一向前 -1
> - 2026-05-06 d：原 `szw-thesis` + `szw-slice` 合并为 `/szw-outline`（双阶段：thesis-mapper + section-planner，弱 section 内部循环）；产物 `03-outline.md` 替代原 `03-thesis-map.md` + `04-section-slices.md`；后续阶段产物文件序号再次向前 -1
> - 2026-05-06 e：原 `szw-draft` + `szw-edit` 合并为 `/szw-write`（支持全文 / 章节模式 + `--mode draft|polish|both`）；产物 `04-draft.md` 覆盖式更新，每次调用快照写入 `.zero/writing-history/<slug>/`；07-platform-package.md → 06-platform-package.md
> - 2026-05-06 f：`/szw-review` 新增 Phase 2 Style Capture——对比 draft vs 最近 history 快照检测人工修改，提取作者风格特征累积到 `.zero/style-profile.md`，下次 `/szw-write` 加载使用。形成"作者风格隐式学习闭环"。
> - 2026-05-06 g：新增 `/szw-complete` 作为流水线终结节点（publish 之后或放弃时触发），STATE.md 从单 current article 改为 active list 模型，支持多 article 并行（progress / resume 接受 `<slug>` 参数定位具体文章）。

---

## TL;DR

7 步流水线从**用户参与度**看，呈"哑铃"分布：

```
szw-discuss ★★★★★  ← 拷问 + brief 合并，用户必须主导（含 9 问拷问环节）
   ↓
szw-research ★★★★  ← evidence + diagnosis 合并，Codex 双阶段；HIGH-risk 内部循环
   ↓
szw-outline ★★★★★  ← thesis 论证地图 + section 拆片合并，用户主导论证设计
   ↓
szw-write ★★★★★    ← draft + polish 合并；全文 / 章节模式；写作历史日志
   ↑   ↓
   └── szw-review ★★  ← 反审让 AI 跑；HIGH issue 回 szw-write [section] --mode polish
       ↓
szw-publish ★★      ← 多平台打包模板化
   ↓
szw-complete ★      ← 流水线终结：active 移到 completed；可选 archive / retro
```

**核心模式**：
- 三个 ★★★★★ HIGH 节点（discuss / outline / write）= 用户精力主战场，关于"写什么"、"怎么排"、"听起来怎么样"，必须作者拍板
- `szw-research` 和 `szw-review` 是 Codex 委派环节 —— 但 research 含 HIGH-risk 决策点，参与度高于 review
- `szw-write` 与 `szw-review` 形成自然循环：write → review → write polish → review，直到 HIGH issue 清零
- 整个流水线 6 步里 3 步真正需要深度投入，其余可放手

---

## 0. 评分维度说明

每步从 3 个维度打分（各 1-5 分），综合给一个总评级。

| 维度 | 含义 | 1 分 | 5 分 |
|---|---|---|---|
| **决策权重**（Decision Weight） | 用户对核心判断有多少话语权 | AI 完全自主，用户只看结论 | 用户必须拍板，AI 只做候选 |
| **审阅强度**（Review Depth） | 用户需要多仔细审阅产出 | 扫一眼即可 | 必须逐句看 |
| **修改可能**（Edit Likelihood） | 产出后用户大概率会改吗 | 几乎不改，直接进下一步 | 必然手改，AI 产出只是脚手架 |

**综合评级**：
- ★★★★★ HIGH —— 用户必须深度参与，跳过等于劣稿
- ★★★★ HIGH-MED —— 关键节点必须看 / 决策
- ★★★ MEDIUM —— 审阅 + 局部决策
- ★★ LOW-MED —— AI 主跑，用户偶尔确认
- ★ LOW —— 模板化产出，用户只兜底

---

## 1. `szw-discuss` —— 选题讨论拷问 + 文章 brief（合并）

| 项 | 内容 |
|---|---|
| **本质** | 一步合并两件事：(1) **Phase 1 拷问**——逼自己回答"这篇真的值得写吗？反驳什么？读者看完该改变什么？" (2) **Phase 2 结构化**——把拷问答案落成文章 brief（读者预期、核心判断、3-5 supporting、out-of-scope）。一次产出 `01-brief.md`，拷问 Q&A 作为附录可追溯。 |
| **数据流** | 用户一句话选题描述 → 9 问拷问（Phase 1）→ 按 EDITORIAL_CONTEXT §6 模板结构化（Phase 2）→ `01-brief.md`：<br>　- **正文**：thesis / reader-payoff / supporting-claims (3-5) / counterargument / evidence-needed / out-of-scope / target-platform<br>　- **附录 A**：Topic Grill Q&A 9 问完整记录<br>　- **附录 B**：宪法对齐检查（vs ADR / EDITORIAL_CONTEXT） |
| **AI 做** | Phase 1：提问、挑战回答中的模糊词、与宪法/ADR 自动比对；Phase 2：按选定的 article type 自动结构化 |
| **用户做** | Phase 1 诚实回答每一问（不让 AI 替你想"读者是谁"）；Phase 2 浏览结构化结果，确认 supporting 都能挂证据 |

| 维度 | 分 | 解释 |
|---|---|---|
| 决策权重 | **5** | Phase 1 命题/读者/反驳目标都是用户判断；Phase 2 决策权重低但被 Phase 1 主导 |
| 审阅强度 | **4** | Phase 1 9 问每问认真看；Phase 2 通读结构化结果 |
| 修改可能 | **3** | Phase 1 拷问通常微调 1-2 轮；Phase 2 大改说明 Phase 1 没拷透 |
| **综合** | **★★★★★ HIGH** | 取两阶段最高分，因为合并步参与度由"必须深度参与"的 Phase 1 决定 |

**关键动作**：
- Phase 1 诚实地说"我也不知道"——这恰好是 grill 该 catch 的信号，要么深挖要么放弃
- Phase 2 检查 supporting claims 是否每条都能挂证据；挂不上立刻回 Phase 1 改命题，不要带病走下去

**失败模式**：囫囵吞枣点过 9 问，让 AI 自动填完 brief 就走人。后果：evidence / draft 全部建立在虚假命题上，最终发现 thesis 撑不下要推翻重来。

**省力策略**：选题已经在 `inbox/` 里磨过几个月、思路非常清晰时，Phase 1 可以快速过；Phase 2 模板高度标准化让 AI 自动填。但 Phase 1 即使快速过也要走完 9 问，不要跳。

**为什么合并**：原 `/szw-grill` 和 `/szw-brief` 是连续两步、中间产物 `00-grill.md` 几乎从不被独立引用。合并并改名为 `/szw-discuss` 后用户少切一次命令，brief 自带"如何得出此判断"附录，对后续 audit / retro 反而更友好。

---

## 2. `szw-research` —— 证据采集 + 判断诊断（合并，Codex）

| 项 | 内容 |
|---|---|
| **本质** | 一步合并两件事：(1) **Phase 1 证据采集**——为每条 supporting claim 收集证据卡；(2) **Phase 2 判断诊断**——检查每条 claim 是否被证据撑住，给 H/M/L 风险评级。HIGH-risk 自动内部循环回 Phase 1 补证据（最多 2 轮），都不通过才 escalate 给用户。 |
| **数据流** | `01-brief.md` → Phase 1 Codex 跑 `evidence-researcher` → 中间产出 evidence cards → Phase 2 Codex 跑 `claim-diagnoser` → 诊断报告 → 合并产出 `02-research.md`（§1 Evidence / §2 Diagnosis / §3 Recommended Action）+ 沉淀 `.zero/evidence/` |
| **AI 做** | 全自主两阶段：检索 / 筛选 / 分级 → 诊断 / 评级 / 安全改写建议 → 内部 HIGH-risk 循环重跑 |
| **用户做** | 跑完看 §3 Recommended Action 决定走 / 不走；若被 escalate（2 轮内部循环仍 HIGH），决定回 `/szw-discuss` 降级表达还是人工接受 |

| 维度 | 分 | 解释 |
|---|---|---|
| 决策权重 | **4** | HIGH-risk 决策点（escalate 时）拉高合并步参与度；其余时间 AI 全自主 |
| 审阅强度 | **3** | 重点看 §3 Recommended Action 与 §2 HIGH/MED 评级 |
| 修改可能 | **2** | 不直接改诊断报告，根据结论决定上游回滚 |
| **综合** | **★★★★ HIGH-MED** | 取两阶段最高分，被 diagnose 的决策属性决定 |

**关键动作**：
- 跑完优先看 §3 Recommended Action：若提示"通过"直接进 thesis；若提示"escalate"必须停下来
- HIGH-risk ≥ 1 即使两轮内部循环消化掉了，也要瞥一眼 §1 Evidence 看证据等级——内部循环可能引入了 risky 来源

**失败模式**：
- 跑完看到很多 HIGH 烦了，点"接受"硬过 —— 文章发出去被读者打脸，事后更难改
- 反方向：用户对证据查证太用力，自己跑去 Google / 翻 GitHub 仓库，浪费时间，这恰好是 Codex 强项

**省力策略**：跑 Codex，洗澡 / 喝咖啡，回来看 §3 Recommended Action 一段即可。这是流水线里"最值得放手"的步骤——内部 HIGH-risk 循环会自愈，用户只在最终 escalate 时决策。

**为什么合并**：原 `/szw-evidence` 和 `/szw-diagnose` 都跑 Codex 且诊断必然依赖证据；分两步用户切换两次命令、读两份报告，HIGH-risk 时还得手动调度回头补证据。合并为单步：Codex 一次性跑完两阶段 + 内部 HIGH-risk 循环，用户只在最终结果或 escalate 时介入，参与度被 diagnose 的决策属性拉到 ★★★★ HIGH-MED。

---

## 3. `szw-outline` —— 论证地图 + 文章拆片（合并）

| 项 | 内容 |
|---|---|
| **本质** | 一步合并两件事：(1) **Phase 1 论证地图**——main thesis + 3-5 supporting + 1-2 counterargument + 论证链；(2) **Phase 2 章节拆片**——按 vertical slice 拆 4-6 节，每节独立成立、有 reader payoff。Phase 2 发现弱 section 时自动回 Phase 1 调整论证（最多 2 轮）。 |
| **数据流** | `01-brief.md` + `02-research.md` → Phase 1 `thesis-mapper` 子 agent → Phase 2 `section-planner` 子 agent → `03-outline.md`（§1 Thesis Map / §2 Section Slices / §3 Decision Log） |
| **AI 做** | Phase 1 起草论证地图候选 + 检查论证链；Phase 2 起草 slice 候选 + 拒绝横向"背景/分析/结论"章节 + Phase 间内部循环 |
| **用户做** | Phase 1 拍板 main thesis 一句话措辞、调整 supporting 顺序、决定 counterargument 怎么回应；Phase 2 调整节序、合并 / 拆分弱 section、确认每节 acceptance criteria |

| 维度 | 分 | 解释 |
|---|---|---|
| 决策权重 | **5** | Phase 1 主论证用户拍板；Phase 2 骨架结构用户拍板 |
| 审阅强度 | **4** | Phase 1 每条 supporting 仔细看；Phase 2 每节看 acceptance criteria |
| 修改可能 | **4** | Phase 1 通常调 1-2 轮论证；Phase 2 调一轮节序 |
| **综合** | **★★★★★ HIGH** | 取两阶段最高分；论证设计是文章灵魂 |

**关键动作**：
- Phase 1 自问 main thesis 一句话能不能让一个**怀疑你的读者**点头。如果不能，回 `/szw-discuss` 重新拷问"读者要相信什么"
- Phase 2 把每节当一个独立小论证，自问"读者只看这节，能拿走什么 takeaway"。如果某节只是"过渡"，删掉它或并入别节
- 优先 4-6 强 section，不要 10 弱 section

**失败模式**：
- thesis 写得太"安全"（"AI 会改变开发流程"——废话），导致全篇没有判断锐度
- 接受 AI 默认的"背景 → 分析 → 结论"横向结构，文章变成报告而非有锐度的判断

**省力策略**：无。这一步和 discuss / write 并列，是流水线**省不得**的 3 步之一；省时间通常意味着省思考，最后用 review / write polish 阶段加倍偿还。

**为什么合并**：原 `/szw-thesis` 和 `/szw-slice` 本质是同一个"论证设计"推理链——写 thesis 时本来就在想"这条 supporting 撑得起一节吗"，slice 阶段又常回头改 thesis。合并为单步：双阶段一次跑完 + 弱 section 内部循环回 Phase 1 自愈，参与度同档（两阶段都 HIGH），合并不模糊边界。

---

## 4. `szw-write` —— 起稿 + 润色（合并；支持全文 / 章节模式）

| 项 | 内容 |
|---|---|
| **本质** | 一步合并三件事：(1) **Phase 1 Draft** 按 outline 写文字；(2) **Phase 2 Polish** 去 AI 腔 / 锐化判断 / 过 humanizer；(3) **写作历史日志** 每次调用快照写入 `.zero/writing-history/<slug>/`。支持全文模式和章节模式两种粒度。 |
| **数据流** | `03-outline.md` + EDITORIAL_CONTEXT + ADR + glossary + **`.zero/style-profile.md`**（作者风格档案）+ 当前 `04-draft.md`（如有） → Phase 1 + Phase 2 → 覆盖更新 `04-draft.md` + 追加 `.zero/writing-history/<slug>/NN-{mode}-{target}-{ts}.md` |
| **调用语法** | `/szw-write [section_id?] [--mode draft\|polish\|both]`<br>　- `/szw-write` —— 全文 + both（默认；初次起稿）<br>　- `/szw-write --mode polish` —— 全文润色（review 后修复）<br>　- `/szw-write S2` —— 仅 outline 第 2 节，both（章节级迭代）<br>　- `/szw-write S3 --mode polish` —— 仅章节 S3 润色 |
| **AI 做** | Phase 1：按拆片产出文字、自检 banned patterns、标 evidence 引用、**按 style-profile 调整词汇 / 句式 / 节奏**<br>Phase 2：humanizer + humanizer-editor 子 agent + EDITORIAL_CONTEXT §11/§12/§15 检查 + style-profile anti-patterns 检查 + 锐化判断<br>每次调用：写快照到 `.zero/writing-history/<slug>/`，更新 `INDEX.md` |
| **用户做** | 全文模式：通读找"AI 偷懒"段落（铺垫过长 / 收尾仓促 / 偏离 thesis）；句句过，按语感改；调标题 / 小标题 / 金句<br>章节模式：聚焦单节迭代，更省力 |

| 维度 | 分 | 解释 |
|---|---|---|
| 决策权重 | **5** | Phase 2 风格调性必须用户拍板（draft 阶段决策权 2，polish 阶段 5，取最高） |
| 审阅强度 | **5** | Polish 阶段必须逐句看 |
| 修改可能 | **5** | 必然手改，AI 产出只是起点 |
| **综合** | **★★★★★ HIGH** | 取两阶段最高分；章节模式可降为 ★★★★（范围缩小，深度不变） |

**关键动作**：
- 初次起稿：`/szw-write` 后通读，拿一支笔（或在 markdown 里加 `<!-- TODO -->`），标出三类问题：① 偏离 thesis 的段落、② AI 套话、③ 论据不够撑判断的句子
- review 后修复：用 `/szw-write S<N> --mode polish` 精准回到具体章节，不重写全文
- humanizer 跑完后**再自己过一遍**——AI 自检的"AI 腔"不全，作者语感才是最后一道关
- 利用 `.zero/writing-history/INDEX.md` 看每次改了什么，不要在脑子里记

**失败模式**：
- 接受 humanizer 全部修改建议直接进 package → 发出去读者说"还是 AI 味"
- review 后用全文 polish（`--mode polish` 不带 section_id）→ AI 把没问题的章节也改了，引入新错
- 不看 `.zero/writing-history/INDEX.md`，反复同节改不同问题，最后乱套

**省力策略**：
- 初稿用 `--mode draft` 快速过一版（跳 polish），通读后再决定哪些节需要 polish，针对性 `/szw-write S<N> --mode polish`
- 章节模式比全文模式快 5-10x，review 报某节有问题时优先用章节模式
- 写作历史日志由系统自动记录，不需要手动维护

**为什么合并**：原 `/szw-draft` 和 `/szw-edit` 分两步，但实际写作是迭代过程：写一段改一段、回头修前面、review 后某节重写、有时只想调一个段落。合并为单命令多模式后：(a) 自然支持"指定章节迭代"；(b) draft / polish 可独立调用也可一次跑完；(c) `.zero/writing-history/` 留下完整迭代轨迹，便于复盘和回滚。

---

## 5. `szw-review` —— 反方审稿 + 风格捕获（Codex）

| 项 | 内容 |
|---|---|
| **本质** | 一步合并两件事：(1) **Phase 1 反方审稿**——独立 AI（Codex）做技术审 + 反方质疑 + 边界审；(2) **Phase 2 风格捕获**——对比 04-draft.md vs 最近 history 快照，识别用户手改的部分，提炼作者风格特征，累积到 `.zero/style-profile.md` 喂给下次 write。 |
| **数据流** | Phase 1：`04-draft.md` + brief + research + EDITORIAL_CONTEXT → Codex `skeptical-reviewer` → `05-review.md`<br>Phase 2：`04-draft.md` vs `.zero/writing-history/<slug>/` 最近快照 → diff → `style-extractor` 子 agent → 追加 `.zero/style-profile.md` |
| **AI 做** | Phase 1：找事实漏洞、提反驳、查 ADR 违反<br>Phase 2：diff 检测 → 词汇 / 句式 / 节奏 / 标点 / anti-patterns 5 类特征提取 → 增量 append 到 style-profile（含来源引用 + 频次） |
| **用户做** | Phase 1：决定 HIGH issue 接不接、是否回 write 修；Phase 2：完全不参与（AI 自学，效果累积到下次 write） |

| 维度 | 分 | 解释 |
|---|---|---|
| 决策权重 | **2** | Codex 跑，用户决定走 / 不走；Phase 2 全自动 |
| 审阅强度 | **2** | 只看 Phase 1 HIGH/MED 列表 |
| 修改可能 | **1** | 不改 review / style-profile 报告本身 |
| **综合** | **★★ LOW-MED** | Phase 2 不增加用户负担 |

**关键动作**：
- Phase 1：HIGH issue ≥ 1 → 用 `/szw-write [section_id] --mode polish` 精准回该节修复（不要全文重写）。最多 2 轮 review-write 循环
- Phase 2：用户**不需要做任何事**——只要在 review 之前手改了 04-draft.md，Phase 2 就会自动学习

**失败模式**：
- 自审取代反审。用户用主对话的 Claude 自己审自己的稿，逻辑容易闭环
- 关闭 Phase 2（`style_capture.enabled=false`）—— 失去随时间积累的"AI 写得越来越像我"红利

**省力策略**：跑 Codex 然后做别的事。LOW 全跳过；MED 看是否只影响某节，是的话用章节模式精准修。Phase 2 是后台自动学习，不需要管。

**风格学习闭环**（这是流水线最有复利的环节）：
```
write 起稿 → 用户手改 04-draft.md → review Phase 1 反审 + Phase 2 学风格
                                              ↓
style-profile.md 累积 ←──────────────────────┘
       ↓
下次 write Phase 1 加载 → AI 起稿就更像作者 → 用户手改更少 → ...
```

文章数累积越多，AI 起稿一遍过的概率越高。

---

## 6. `szw-publish` —— 多平台打包

| 项 | 内容 |
|---|---|
| **本质** | 同一篇 v2 稿件按平台特性产出 4 套版本：blog 全文 / wechat 拆段加钩子 / x thread / xhs 首屏 |
| **数据流** | `04-draft.md` + target platforms → `06-platform-package.md` + `published/<slug>/{blog,wechat,x,xhs}.md` |
| **AI 做** | 按各平台模板自动产出版本 |
| **用户做** | 公众号标题 / X thread 第一条 / 小红书首屏 5 行 拍板 |

| 维度 | 分 | 解释 |
|---|---|---|
| 决策权重 | **1** | 内容已定，只是模板化产出 |
| 审阅强度 | **2** | 各平台首屏 / 标题确认即可 |
| 修改可能 | **2** | 平台特定细节调一下 |
| **综合** | **★★ LOW** | |

**关键动作**：钩子句（公众号开头、X 第一条、xhs 首屏）必须人工拍板。AI 写的钩子普遍偏弱。

**失败模式**：用 AI 默认钩子直接发布，公众号点击率比正文质量该有的低 50%。

**省力策略**：blog / 长文版本完全自动，只在钩子句上花 5 分钟。

---

## 7. 汇总对比表

| # | 步骤 | 决策权重 | 审阅强度 | 修改可能 | 综合 | 用户必做的关键动作 |
|---|---|---|---|---|---|---|
| 1 | `szw-discuss`（grill + brief） | 5 | 4 | 3 | **★★★★★ HIGH** | Phase 1 诚实回答 9 问；Phase 2 确认 supporting 都能挂证据 |
| 2 | `szw-research`（evidence + diagnosis） | 4 | 3 | 2 | ★★★★ HIGH-MED | 看 §3 Recommended Action；escalate 时回 discuss 降级或人工接受 |
| 3 | `szw-outline`（thesis + slice） | 5 | 4 | 4 | **★★★★★ HIGH** | Phase 1 main thesis 能否说服怀疑读者；Phase 2 拒绝横向"背景/分析/结论" |
| 4 | `szw-write`（draft + polish） | 5 | 5 | 5 | **★★★★★ HIGH** | 全文通读 + 逐句过 + humanizer 之后自己再过；review 后用章节模式精准修复 |
| 5 | `szw-review` | 2 | 2 | 1 | ★★ LOW-MED | HIGH issue ≥ 1 必回 szw-write [section] --mode polish |
| 6 | `szw-publish` | 1 | 2 | 2 | ★★ LOW | 钩子句人工拍板 |

**3 个 HIGH 节点（discuss / outline / write）= 全流水线 70% 的质量来源**。这三步省，全篇报废。

**2 个 LOW-MED 节点（review / package）+ 1 个 HIGH-MED 决策点（research）= 全流水线 70% 的可委派工作量**。research 内部 HIGH-risk 自动循环 2 轮自愈，用户只在 escalate 时介入。

**合并后特征**：流水线从 10 步精简到 6 步，但 3 个 HIGH 节点（≈ 70% 质量来源）保留完整。每个合并步内部都有 phase 间循环（discuss 拷问↔结构化、research evidence↔diagnosis、outline thesis↔slice、write draft↔polish），自愈大部分边角情况，escalate / review 才打扰用户。`szw-write` 与 `szw-review` 之间形成显式循环（write → review → write polish [section]），章节模式让回头修复成本极低。

---

## 8. 参与度模式建议

按文章重要性 / 用户精力，三套策略：

### 策略 A：重磅文章（每月 1-2 篇，传播 / 收入预期高）

每步按推荐参与度走，不省。预计周期：跨 3-5 天。

```
Day 1: discuss（深度 1h，含 9 问拷问 + 结构化）+ research（Codex 后台跑双阶段）
Day 2: outline（深度 2h，论证地图 + 章节拆片合并）
Day 3: write --mode draft（一稿快速过）+ 通读标问题
Day 4: review（Codex）→ write [section] --mode polish 精准修（深度 2h）
Day 5: package + 钩子拍板 + 发布
```

### 策略 B：日常文章（每周 1-2 篇）

HIGH 节点照做，LOW 节点加速：

- research 直接接受 Codex 全部产出，不补查证据；只看 §3 Recommended Action 一段
- write 用 `--mode both` 一次跑完 draft + polish；review 后只针对 HIGH section 用章节模式精修
- review 只看 HIGH，MED/LOW 跳
- package 只手改钩子，正文版本全自动

预计周期：1-2 天。

### 策略 C：时事短评（≤ 800 字，热点跟进）

**走 `/szw-quick`**，跳过 research / outline / review。

只保留：discuss（仅 Phase 1 简化拷问，跳 Phase 2）→ write（一次 both 模式）→ package。

不要硬塞进完整流水线，否则时效性丢了。

---

## 9. 反模式：参与度倒挂

观察到一种反复出现的失败模式：**HIGH 节点甩手，LOW 节点死磕**。

| 倒挂表现 | 真实后果 |
|---|---|
| discuss 的 Phase 1 拷问 5 分钟点过，research 自己手动查 2h | 命题虚假，证据再扎实也救不回来 |
| outline 的 thesis 让 AI 决定，write 通读 5 遍 | 反复读一篇没有判断锐度的文章 |
| write polish 阶段全盘接受 humanizer 自动修，package 钩子改 1h | 正文 AI 腔，钩子再强也是反差 |
| review 报某节问题，用 `--mode polish` 全文重写 | AI 把没问题的章节也改了，引入新错；应该用章节模式 `/szw-write S<N> --mode polish` |
| review 跳过 / 自审，diagnose 死磕 LOW issue | HIGH 被忽略，LOW 浪费时间 |

**参与度的本质是分配注意力的预算**。把预算花在 AI 不能替你做的事上：

- AI 不能替你做：**判断什么值得写、判断读者要相信什么、判断声音听起来对不对**
- AI 可以替你做：**查证据、找反例、写第一稿、产出多平台版本**

记住这个分工，HIGH 节点深度投入是赚的，LOW 节点深度投入是亏的。

---

## 10. 与 GSD 对应步骤的参与度对比

| 写作步 | GSD 对应 | 写作参与度 | GSD 参与度 | 差异 |
|---|---|---|---|---|
| szw-discuss（Phase 1 拷问 + Phase 2 结构化） | gsd-discuss-phase + gsd-plan-phase（部分） | HIGH | HIGH | 拷问环节决定参与度上限 |
| szw-outline（thesis + slice 合并） | gsd-plan-phase（剩余） | HIGH | MED | 写作论证骨架更敏感，参与度更高 |
| szw-research（evidence + diagnosis） | gsd-phase-researcher + gsd-plan-checker | HIGH-MED | LOW-MED | 合并步因含 HIGH-risk 决策点参与度高于 GSD 同位 |
| szw-write（draft + polish 合并） | gsd-execute-phase + 无对应（polish） | HIGH | MED | 写作合并步含独有的 polish 阶段（风格调性），参与度被 polish 决定 |
| szw-review | gsd-review (cross-AI) | LOW-MED | LOW | 一致：都委派 |
| szw-publish | gsd-ship | LOW | MED | 写作打包模板化更彻底 |

**核心差异**：`szw-write` 的 polish 阶段是 GSD 没有的 HIGH 节点。这是技术专栏的写作灵魂——风格调性必须作者拍板，不是工程任务可以替代的环节。合并到 `szw-write` 后通过 `--mode polish [section]` 让"局部精修"成为流程一等公民。

---

## 附 A：完整 8 步全景图（含创建入口与终结节点）

```
┌──────────────────┐
│ /szw-new-article  │  ← 创建项目，参与度 ★★★ MED
└────────┬─────────┘
         ↓
┌──────────────────┐
│ /szw-discuss      │  ← ★★★★★ HIGH （Phase 1 拷问 + Phase 2 结构化）
└────────┬─────────┘
         ↓
┌──────────────────┐
│ /szw-research     │  ← ★★★★ HIGH-MED （Codex 双阶段，HIGH-risk 内部循环）
│   ┌─Phase 1      │
│   │ evidence     │
│   ├─Phase 2      │
│   │ diagnosis    │
│   └─loop ≤2      │
└────────┬─────────┘
         ↓ escalate 时回 /szw-discuss
┌──────────────────┐
│ /szw-outline      │  ← ★★★★★ HIGH （Phase 1 论证地图 + Phase 2 章节拆片）
│   ┌─Phase 1      │
│   │ thesis-map   │
│   ├─Phase 2      │
│   │ section-slice│
│   └─loop ≤2      │
└────────┬─────────┘
         ↓ escalate 时回 /szw-research 补证据 / /szw-discuss 调命题
┌──────────────────┐ ←──┐
│ /szw-write        │    │  ← ★★★★★ HIGH （Phase 1 draft + Phase 2 polish）
│   ┌─load profile │    │     全文模式 / 章节模式 (S1, S2, ...)
│   ├─Phase 1 draft│    │     `--mode draft|polish|both`
│   ├─Phase 2 polish    │     每次调用快照写 .zero/writing-history/
│   └─history log  │    │     ← style-profile 反馈环
└────────┬─────────┘    │
         ↓              │
   [用户手改 04-draft.md] (可选，自由插入)
         ↓              │
┌──────────────────┐    │ HIGH issue → /szw-write [section] --mode polish
│ /szw-review       │ ───┘
│   ┌─Phase 1      │    Codex 反审，参与度 ★★ LOW-MED
│   │ skeptical    │
│   └─Phase 2      │    AI 后台学风格（diff vs history）
│     style-capture│ ──→ .zero/style-profile.md（累积，喂下次 write）
└────────┬─────────┘
         ↓
┌──────────────────┐
│ /szw-publish      │  ← ★★ LOW （模板化）
└────────┬─────────┘
         ↓
┌──────────────────┐
│ /szw-complete     │  ← ★ LOW （终结：active → completed；可选 archive / retro）
│   --published     │     从 STATE.md Active Articles 移到 Recently Completed
│   --archived      │     更新 ARTICLE.md status 为终态
│   --retro         │     可选触发 /szw-retro（v3.0）
└──────────────────┘
```

**多 article 并行**：以上 8 步的每一步都接受 `<slug>` 参数定位具体文章；STATE.md 的 `Active Articles` 表同时记录多篇文章的 status。`/szw-progress` 列全部进度，`/szw-resume <slug>` 在文章间切换。同一专栏可以有多篇 article 处于不同 phase。

3 个 ★★★★★ 节点（discuss / outline / write）+ 1 个 ★★★★ 决策点（research escalate）= 用户精力主要去处。

**风格学习闭环**：用户每次手改 04-draft.md（在调 review 之前）都会被 review Phase 2 自动学进 `.zero/style-profile.md`，下次 write 直接加载使用。文章数累积越多，AI 起稿一遍过的概率越高——这是流水线最有复利的隐式机制，用户不需要主动维护。

---

## 附 B：参考资料

- [`writing-workflow-blueprint.md`](./writing-workflow-blueprint.md) §3 v1.0 + §4 v2.0 各 skill 的完整定义
- [`writing-workflow-proposal.md`](./writing-workflow-proposal.md) §6 子 agent 设计原则
- [`gsd-research.md`](./gsd-research.md) §5.1 GSD agent 注册表（参考完成 marker 协议）
- [`../write-progress/flow.md`](../write-progress/flow.md) §7 升级后写作工作流
