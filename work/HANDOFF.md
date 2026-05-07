# szw 写作工作流 —— 上下文恢复 Handoff

> Last updated: 2026-05-07（追加 LLM wiki 集成：fan-llm-wiki-extension.md v2.1 + szw-init 大改 orchestrator 模式 + 4 个 init/wiki sub-skill 完成）
> **2026-05-06**：szw-progress / szw-new-article / szw-discuss / szw-outline / szw-research / szw-write / szw-review 全部完成；v2.0 主流水线 discuss → research → outline → write → review 已闭环；风格学习闭环已落地。
> **审计补充 2026-05-06**：见 `work/REVIEW-2026-05-06.md` —— 已发现 P0/P1 一致性问题（next_action 带 slug 不一致 / fan.md ↔ EDITORIAL_CONTEXT 模板节号错位 / 函数签名分歧）+ 16 个未完成 skill 优先级清单。
> **LLM wiki 集成 2026-05-07**：设计文档 `study/fan-llm-wiki-extension.md` v2.1（约 1000 行）；新增 4 个 skill 完成：`szw-init`（升级为 orchestrator）、`szw-claude-init`、`szw-wiki-init`、`szw-wiki-import`（含三向 diff 链接重写 / 索引重建 / 6 场景烟囱测试通过）。下一步开发 `/szw-wiki-ingest` —— 详见 `work/PLAN-szw-wiki-ingest.md`（自包含开发蓝图）。
> Purpose: clear context 后能从这一份文档完整恢复工作上下文
> 阅读顺序：本文 → `study/fan.md` → `study/fan-llm-wiki-extension.md`（如做 wiki 命令族）→ `skills/write/` 各已完成 skill

---

## 1. 项目大局

正在构建一套**专为技术专栏写作**设计的 Claude Code skills 生态，命名空间 `szw-`（"专注写作的空间"）。

灵感来自 GSD（`/gsd-*` 工程项目流水线）和 mattpocock skills，但**专门优化写作场景**：作者风格学习闭环、多 article 并行、Codex 委派查证 / 反审、写作历史日志。

**根仓库**：`/Users/xinz/Development/zero-to-ai/`

---

## 2. 关键设计决策（已锁定）

### 2.1 命名空间 / 目录模型

- 所有命令前缀 `/szw-*`
- 容器目录 = cwd（v1.0 单 Column）；多 Column 管理留给 v3.0
- 显性子目录（用户高频交互）：`published/` `articles/{,quick,archived}/` `editorial-adr/` `glossary/` `inbox/{pending,done}/` `series/` `summaries/`
- 根文件：`COLUMN.md` `EDITORIAL_CONTEXT.md` `ROADMAP.md`
- 隐藏 `.zero/`（仅装系统状态 + AI 内部资料）：
  - `STATE.md`（活记忆）
  - `szw-config.json`（配置）
  - `.continue-here`（pause handoff）
  - `style-profile.md`（作者风格档案，由 review Phase 2 累积）
  - `evidence/`（证据银行）
  - `audits/`（一致性审计报告）
  - `writing-history/<slug>/`（write 每次调用的快照）

### 2.2 文章流水线（v2.0 完整 7 步）

```
discuss → research → outline → write ←→ review → publish → complete
```

经历过 4 次合并优化：
- grill + brief → **discuss**
- evidence + diagnose → **research**
- thesis + slice → **outline**
- draft + edit → **write**

每个合并步内部都有双 phase + 内部循环 + escalate 出口。

### 2.3 Article Status 状态机（11 个枚举值）

| Status | 由哪个命令进入 | 是否 active |
|---|---|---|
| `created` | `/szw-new-article` | ✅ |
| `brief_done` | `/szw-discuss` | ✅ |
| `research_done` | `/szw-research` | ✅ |
| `outline_done` | `/szw-outline` | ✅ |
| `draft_done` | `/szw-write` | ✅ |
| `review_failed` | `/szw-review` | ✅（最优先级） |
| `review_passed` | `/szw-review` | ✅ |
| `published` | `/szw-publish` | ✅ |
| `paused` | `/szw-pause`（v3.0） | ✅ |
| `completed` | `/szw-complete --published` | ❌（终态） |
| `archived` | `/szw-complete --archived` | ❌（终态） |

### 2.4 多 article 并行模型

- 每个 article 在 ARTICLE.md 里独立维护 status
- STATE.md 维护 `Active Articles` 表（slug / status / last_touched / next action）+ `Recently Completed` 表
- 所有流水线命令接受 `<slug>` 参数定位具体文章
- 不指定 slug 时按 `last_touched` 取默认
- progress 全局优先级：`review_failed` > `paused` > `last_touched` 久 > 其他

### 2.5 风格学习闭环（最有复利的环节）

```
write 起稿 → 用户手改 04-draft.md → review Phase 1 反审 + Phase 2 学风格
                                              ↓
style-profile.md 累积 ←──────────────────────┘
       ↓
下次 write Phase 1 加载 → AI 起稿就更像作者 → 用户手改更少 → ...
```

风格特征 5 类：词汇替换 / 句式偏好 / 节奏段落 / 标点中英混用 / **anti-patterns**。

### 2.6 用户参与度（哑铃分布）

3 个 ★★★★★ HIGH 节点（**discuss / outline / write**）= 70% 质量来源，省不得。
2 个 ★★ LOW-MED 节点（review / publish）+ 1 个 ★ LOW（complete）= 委派为主。
research ★★★★ HIGH-MED（HIGH-risk decision point）。

### 2.7 命令总数

**26 个** = v1.0 (12) + v2.0 (7) + v3.0 (7)，分 8 类。详见 `skills/write/szw-help/references/commands-catalog.md`。

---

## 3. 已完成的工作

### 3.1 设计文档（`study/`）

| 文件 | 内容 |
|---|---|
| `gsd-research.md` | GSD 65 个 skill 体系调研（早期产物） |
| `gsd-workflow-guide.md` | GSD 使用建议（早期产物） |
| `writing-workflow-proposal.md` | 写作工作流总体建议（早期产物） |
| **`fan.md`** | **核心设计文档**（原 `writing-workflow-blueprint.md` 改名）—— 26 个命令完整设计 + 子 agent 表 + hooks + 目录布局 + 实施清单 |
| **`article-pipeline-guide.md`** | **流水线深度指南** —— 7 步详解 + 参与度评分 + 三套策略 + 反模式 |

`fan.md` §3.0 有完整的 **Article 状态机定义**；§3-§5 是各命令的逐项详解；§9 是目录布局；§12 是实施清单。

### 3.2 已建 Skills（`skills/write/`）

```
skills/write/
├── szw-topic-grill/                        (改名自 topic-grill，被 szw-discuss Phase 1 引用 9 问模板)
│   └── SKILL.md
│
├── szw-init/                               ✅ Week 1 核心
│   ├── SKILL.md                            (267 行：Step 0 检测模式 + Mode A/B 流程)
│   ├── scripts/
│   │   └── create-skeleton.sh              (3 道 gate：参数 / 防覆盖 / 写权限；创建 13 个目录 + .gitkeep)
│   └── templates/
│       ├── README.md                       (模板系统说明 + 占位符约定 + 迭代指南)
│       ├── COLUMN.md                       (专栏定位)
│       ├── EDITORIAL_CONTEXT.md            (写作宪法 7 节)
│       ├── ROADMAP.md                      (空 stub)
│       ├── STATE.md                        ✨ 已升级支持多 article（Active + Recently Completed）
│       ├── szw-config.json                 (含 style_capture / gates 块)
│       ├── ADR.md                          (通用 ADR 脚手架)
│       └── adrs/
│           ├── 0001-no-benchmark-dumping.md
│           ├── 0002-tool-review-needs-action.md
│           └── 0003-no-anxiety-farming.md
│
├── szw-help/                               ✅ Week 1
│   ├── SKILL.md                            (5 种调用形式 + 多 article 优先级推荐)
│   └── references/
│       └── commands-catalog.md             (26 个命令分类清单 + 流水线示意 + 多 article 模型)
│
├── szw-config/                             ✅ Week 1
│   ├── SKILL.md                            (5 个子命令：show/get/set/validate/reset)
│   ├── references/
│   │   └── config-schema.md                (9 类字段语义 + 合法值 + 修改后果)
│   └── scripts/
│       └── edit-config.py                  (Python；schema 集中；类型 coercion；嵌套 dotted path)
│
├── szw-progress/                          ✅ Week 1（2026-05-06 追加）
│   ├── SKILL.md                            (5 种调用形式 + 优先级排序 + NL 路由 AI 侧约定)
│   ├── references/
│   │   └── state-schema.md                 (STATE.md 表 schema + JSON 输出契约 + 同步更新清单)
│   └── scripts/
│       └── parse-state.py                  (Python；4 个子命令 active/completed/article/validate；JSON 输出)
│
├── szw-new-article/                       ✅ Week 1（2026-05-06 追加）
│   ├── SKILL.md                            (4 种调用形式 + 7 步交互流程 + 失败处理表)
│   ├── references/
│   │   └── article-md-schema.md            (ARTICLE.md frontmatter 字段契约 + 不变性矩阵 + 下游消费者表)
│   ├── templates/
│   │   └── ARTICLE.md                      (frontmatter 占位符 + Thesis/Source Material/Status Log 骨架)
│   └── scripts/
│       └── new-article.py                  (Python；非交互；slug/type/platforms 校验 + STATE.md 表插入 + 失败回滚)
│
├── szw-discuss/                           ✅ Week 1（2026-05-06 追加）
│   ├── SKILL.md                            (3 种调用形式 + 4 phase 流程 + escalation/abort gate + 3 个对话示例)
│   ├── references/
│   │   ├── brief-schema.md                 (01-brief.md 渲染契约 + stdin JSON 字段 + 同步清单)
│   │   └── article-type-emphasis.md        (4 种 type 在 brief 阶段的侧重提示 + 反模式速查)
│   └── scripts/
│       ├── prepare-discuss.py              (Phase 0：路由 slug + 解析 ARTICLE.md frontmatter + 列 ADR + 返回 context_paths)
│       └── finalize-discuss.py             (Phase 3：commit / abort 子命令；commit 通过 stdin 收 brief JSON)
│
├── szw-research/                          ✅ Week 1（2026-05-06 追加完成）
│   ├── SKILL.md                            (2 调用形式 + 4 phase + HIGH-risk 内部循环 + 三态 verdict gate + 与上下游集成表)
│   ├── references/
│   │   ├── research-schema.md              (stdin JSON 契约 + verdict gate 表 + claim ID 一致性约定)
│   │   └── evidence-bank.md                (.zero/evidence/<topic>.md schema + 创建/追加行为 + 跨 skill 用法)
│   └── scripts/
│       ├── prepare-research.py             (Phase 0：解析 01-brief.md + 分配 claim ID C1..Cn + 列已有 .zero/evidence/* )
│       └── finalize-research.py            (Phase 3：commit；三态 verdict gate；evidence bank 创建/追加；high_risk 一致性强校验)
│
├── szw-outline/                           ✅ Week 1（2026-05-06 追加）
│   ├── SKILL.md                            (2 种调用形式 + 4 phase + 内部循环 + verdict gate + 3 个示例 + 与上下游集成表)
│   ├── references/
│   │   ├── outline-schema.md               (stdin JSON 契约 + thesis_map / Slice / Decision 子结构 + mode 自动检测)
│   │   └── section-slice-pattern.md        (vertical slice 7 字段 + 4 条规则 + 横向章节例外 + 拆片自查清单)
│   └── scripts/
│       ├── prepare-outline.py              (Phase 0：解析 01-brief.md + 02-research.md 检测 + claim ID 分配 + mode 标注)
│       └── finalize-outline.py             (Phase 3：commit；verdict gate；mode 自动判定；改 ARTICLE.md/STATE.md)
│
├── szw-write/                             ✅ Week 1（2026-05-06 追加）
│   ├── SKILL.md                            (4 种调用形式 2×2 矩阵 + 4 phase + 与上下游集成表 + 3 示例)
│   ├── references/
│   │   ├── write-schema.md                 (stdin JSON 契约 + 状态推进决策表 + history snapshot 文件结构)
│   │   └── section-naming.md               (## §<n>. <title> 节标记约定 + section 替换边界 + 反模式)
│   └── scripts/
│       ├── prepare-write.py                (Phase 0：解析 brief/outline/research/sections + 列长期资产 + history + mode 推荐)
│       └── finalize-write.py               (Phase 3：commit；full / S<n> 替换；history snapshot + INDEX；status 自动+显式 advance)
│
└── szw-review/                            ✅ Week 1（2026-05-06 追加）
    ├── SKILL.md                            (2 调用形式 + 4 phase + Phase 1 内部循环 + verdict gate + 风格闭环说明 + 与上下游集成表 + 4 示例)
    ├── references/
    │   ├── review-schema.md                (stdin JSON 契约 + verdict gate + Issue/Phase2 子结构 + 状态推进 + next_action 规则)
    │   └── style-profile-schema.md         (.zero/style-profile.md 4 段语义 + Detail 模板 + write 必读约定)
    └── scripts/
        ├── prepare-review.py               (Phase 0：路由 + diff 计算 + style_capture config + skip 推荐 + 列长期资产)
        └── finalize-review.py              (Phase 3：verdict gate + 渲染 05-review.md + style-profile.md 创建/追加 + 智能 next_action)
```

**所有脚本经过测试通过**：
- `create-skeleton.sh`：13 目录创建 + 防覆盖 + 命名校验三种 gate
- `edit-config.py`：show/get/set/validate/reset 全部子命令；non-enum 值 exit 3；嵌套路径
- `parse-state.py`：active / completed / article / validate；占位行过滤；优先级排序（review_failed → paused → stale → most_recent）；缺失 STATE.md exit 1；slug 不存在 exit 2；表损坏 exit 3
- `new-article.py`：8 个退出码（slug 冲突/格式/type/platform/inbox/series/column/STATE.md 损坏）；inbox 升级（pending→done）；series INDEX 追加 bullet；STATE.md 写入失败时自动 rmtree 已创建目录回滚
- `prepare-discuss.py`：默认 last_touched 路由 / 显式 slug / 不存在 slug exit 2 / 不在专栏 exit 1；frontmatter 解析（支持 list/null）；ADR 列表带 ID + H1 标题
- `finalize-discuss.py`：commit 渲染 01-brief.md（含附录 A/B）+ 改 ARTICLE.md（status/Thesis/Status Log）+ 改 STATE.md Active 行；alignment_check.conflicts 非空 exit 5；abort 移到 archived/ + Active 删行 + 加 Recently Completed 行（清占位）
- `prepare-research.py`：默认按 brief_done 优先路由 / 解析 01-brief.md 6 个主节 + 分配 C1..Cn / 列 .zero/evidence/* 复用候选
- `finalize-research.py`：commit 渲染 02-research.md（§1 cards / §2 diagnosis / §3 action）+ 三态 verdict gate（passed / passed_with_high_risk+accept / 其他都拒绝）+ high_risk_claims 必须严格等于 diagnosis 中 risk='H' 集合（否则 exit 4）+ evidence bank 自动创建/追加 .zero/evidence/<topic>.md + 改 ARTICLE.md/STATE.md（next=`/szw-outline`）
- `prepare-write.py`：默认按 STATUS_PRIORITY 路由（outline_done > research_done > brief_done > draft_done > review_failed > review_passed）/ 解析 outline section 7 字段 / brief 派生 sections（v1.0 兜底）/ --section 模式提取当前 04-draft.md 中该节内容 / 列 style-profile / EDITORIAL_CONTEXT / ADR / glossary / writing-history 最近 5 个 snapshot
- `finalize-write.py`：commit；2×2 矩阵（mode={draft,polish,both} × target={full,S<n>}）；section 替换强校验 content 必须以 `## §<n>` heading 开头；status 自动决策（target=full + draft/both + status ∈ {brief_done,research_done,outline_done} → draft_done）；显式 advance_status_to 仅接受 'draft_done'，非法转移 exit 6；writing-history snapshot NN 自增 + INDEX 表新行插顶部
- `prepare-review.py`：默认按 STATUS_PRIORITY (draft_done > review_failed > review_passed) 路由；用 difflib.SequenceMatcher 计算 04-draft.md vs 最近 writing-history snapshot 的 diff_pct；读 style_capture 配置；输出 should_skip 推荐；列长期资产
- `finalize-review.py`：commit 渲染 05-review.md（§1 Phase1 issues by severity / §2 Phase2 features 或 skip / §3 Notes）+ verdict gate（HIGH 与 review_passed 不能共存 exit 5）+ ARTICLE.md status 推进 + STATE.md next_action 智能（review_failed 时从 first HIGH issue.location 提取 S\<n\>）+ style-profile.md 创建/追加（meta 复数 + 累计 + Recent Edits 表追加）
- `prepare-outline.py`：默认按 research_done > brief_done 优先级路由 / 复用 prepare-research 的 brief 解析 + claim ID 分配 / 检测 02-research.md 存在 → mode=brief_plus_research|brief_only
- `finalize-outline.py`：commit 渲染 03-outline.md（§1 Thesis Map + §2 Section Slices + §3 Decision Log）+ verdict gate（weak_section_unresolved 拒绝 exit 5）+ section count 软约束 WARN（< 3 或 > 8）+ mode 自动判定（不接受 stdin 撒谎）

---

## 4. 下一步计划（Week 1 剩余）

### 4.1 优先建：剩余 skills

按推荐顺序：

1. ~~**`szw-progress`** —— 多 article 进度展示器~~ ✅ **2026-05-06 完成**
   - 实现要点：4 个子命令脚本 + AI 侧 NL 路由
   - state-schema.md 是后续 resume / complete 共用的 STATE.md 解析契约

2. ~~**`szw-new-article`** —— 创建新文章项目~~ ✅ **2026-05-06 完成**
   - 实现要点：非交互脚本 + AI 侧问答
   - 首次出现"写 STATE.md"逻辑（仅插入新行，含原子回滚）
   - article-md-schema.md 定义 ARTICLE.md frontmatter 契约

3. ~~**`szw-discuss`** —— 选题拷问 + brief 合并~~ ✅ **2026-05-06 完成**
   - 实现要点：AI 主导 grill 对话，脚本管 IO（prepare 收集 / finalize 落盘）
   - alignment_check.conflicts 非空时 commit 拒绝（exit 5），强制走 abort 或修 brief
   - abort 路径完整：移 archived/ + Active 删行 + Recently Completed 加行（首次实现"移行"语义，szw-complete 可拷贝）
   - 引用 `szw-topic-grill/SKILL.md` 的 9 问题模板，不重复定义

4. ~~**`szw-outline`** —— 论证地图 + 章节拆片合并~~ ✅ **2026-05-06 完成**
   - 实现要点：AI 主导论证设计，脚本管 IO；首次实现"内部循环 + verdict gate"模式
   - **双 mode**：`brief_plus_research`（v2.0 完整）/ `brief_only`（v1.0 兜底，02-research.md 缺失）
   - claim ID 稳定接口：与 prepare-research.py 共享 `C1..Cn` 分配规则
   - section count 软约束（4-6 最佳，3-8 接受，外则 WARN）
   - 与 discuss / research / write 的集成点写在 SKILL.md "与上下游紧密集成"表

5. ~~**`szw-research`** —— 证据采集 + 判断诊断~~ ✅ **2026-05-06 完成**
   - 实现要点：AI（建议路由 Codex）跑 evidence + diagnosis；脚本管 IO + verdict gate + evidence bank 同步
   - **三态 verdict gate**（首次）：passed / passed_with_high_risk(+user_decision=accept) / 其他都拒绝
   - HIGH-risk 自愈：内部循环 ≤ 2 轮；2 轮仍 HIGH 必须显式 user_decision（accept 或 downgrade）
   - downgrade → exit 5 提示回 `/szw-discuss` 改 brief；needs_rework → exit 5 escalate
   - high_risk_claims 与 diagnosis 中 risk='H' 集合必须严格一致（exit 4）
   - evidence bank 自动沉淀：`.zero/evidence/<topic>.md` 创建/追加；backlink "Used in: <slug> (claim Cn)"

6. ~~**`szw-write`** —— 起稿 + 润色合并~~ ✅ **2026-05-06 完成**
   - 实现要点：AI 提交真实 markdown（不是结构化 JSON）；脚本管 IO + section 替换 + history snapshot + 状态推进
   - **2×2 矩阵**：mode={draft, polish, both} × target={full, S<n>}
   - section ID `S<n>` ↔ outline `§<n>` ↔ draft `## §<n>` 三处对齐（首次跨产物 ID 对齐）
   - history snapshot：`.zero/writing-history/<slug>/NN-<mode>-<target>-<ts>.md` + INDEX.md（最新优先）
   - status 推进矩阵：full+draft/both+brief_done/research_done/outline_done → draft_done；其他默认不动；显式 advance 受合法性校验
   - 风格学习闭环锚点：必读 `.zero/style-profile.md`（review Phase 2 累积）

7. ~~**`szw-review`** —— 反方审稿 + 风格捕获~~ ✅ **2026-05-06 完成**
   - 实现要点：Phase 1 AI(Codex) 反审 H/M/L issues；Phase 2 difflib 对比 draft vs writing-history snapshot 提取 5 类风格特征
   - **第 4 种 verdict gate 模式**：HIGH issues 与 review_passed 不能共存（exit 5）
   - **风格学习闭环已落地**：累积到 `.zero/style-profile.md` 4 段结构（meta + Stable Patterns + Recent Edits）；下次 write 必读
   - 智能 next_action：review_failed + first HIGH issue.location 含 S\<n\> → `/szw-write <slug> S<n> --mode polish`
   - Phase 2 自动 skip：diff_pct < `style_capture.diff_threshold_pct`（默认 5%）/ no snapshot / config disabled

8. **`szw-publish`** —— 多平台打包（**下一个推荐**，v1.0 流水线收尾节点）
   - 设计已完整，见 `study/fan.md` §3.5
   - 接受 04-draft.md → 按 target_platforms 切多份（blog / wechat / x / xhs）
   - 输出到 `published/<slug>/{blog,wechat,x,xhs}.md`
   - status: review_passed → published

9. **`szw-resume`** —— 多 article 上下文恢复
   - 设计已完整，见 `study/fan.md` §3.10
   - 3 种调用形式：`/` / `<slug>` / `--list`
   - 复用 `parse-state.py`：建议直接拷贝 szw-progress 的脚本（self-contained）
   - 新增需要：读 ARTICLE.md frontmatter + 阶段产物 + EDITORIAL_CONTEXT.md 前 N 节

10. **`szw-complete`** —— 流水线终结节点
   - 设计已完整，见 `study/fan.md` §3.6
   - 4 种调用形式：默认 / `<slug>` / `--archived` / `--retro`
   - 步骤：验证 status → 更新 ARTICLE.md → 更新 STATE.md（Active 移到 Recently Completed）→ 可选 archive 移动 → 可选 series INDEX 更新
   - 写 STATE.md 的"删行"+"加 completed 行"逻辑可以参考 `szw-new-article/scripts/new-article.py` 的 `append_to_active_table()`

### 4.2 架构决策（已锁定）：self-contained skills

考虑过 `_shared/scripts/` 共享路线，最终选择 **self-contained**（每个 skill 独立 scripts/）。理由：

1. **可移植性** —— skill 应能独立工作，符合 mattpocock 风格
2. **当前重复成本低** —— `parse-state.py` ~300 行；最多 3 份副本（progress / resume / complete）
3. **schema 单点维护** —— STATE.md 解析契约文档化在 `szw-progress/references/state-schema.md`，所有解析器对齐这一份文档而非共享代码
4. **未来若痛感真实** —— 再 refactor 到 `_shared/`，沉没成本可控

**操作约定**：
- szw-resume 直接拷贝 szw-progress 的 `parse-state.py`，按需扩展（如加 `frontmatter` 子命令读 ARTICLE.md）
- 任何对解析逻辑的修改，先改 `state-schema.md`，再同步各 skill 的 parse-state.py
- 写 STATE.md 的逻辑各 skill 自己实现（szw-new-article 已有 `append_to_active_table()`；szw-complete 实现"移行"操作；szw-pause 实现 status 改 paused）。共同遵守：仅改目标 section，保留其他 section 原状

### 4.3 Week 2 之后

参考 `study/fan.md` §12 实施清单：

**Week 2**（v1.0 主流水线 skills，6 个）：
- szw-new-article
- szw-discuss（包装现有 szw-topic-grill）
- szw-write
- szw-publish
- szw-context
- szw-adr

**Week 3**：用 `/szw-init` 真实初始化专栏 + 跑通第一篇文章

**Week 4**：v2.0 增强（research / outline / review Phase 2 风格捕获 / capture / quick / new-series）

**Month 2**：v3.0 + Hooks

---

## 5. 关键文件路径速查

### 设计文档
- 主蓝图：`study/fan.md`
- 流水线深度指南：`study/article-pipeline-guide.md`

### 已建 skills
- 共同根：`skills/write/`
- 已完成：`szw-init/` `szw-help/` `szw-config/` `szw-progress/` `szw-new-article/` `szw-discuss/` `szw-research/` `szw-outline/` `szw-write/` `szw-review/`
- 现成可复用：`szw-topic-grill/`（改名自 topic-grill；被 szw-discuss Phase 1 引用 9 问题模板）

### v2.0 主流水线已闭环到 review（2026-05-06 里程碑）
- init → new-article → discuss → research → outline → write → **review** → publish（待）→ complete（待）
- 端到端可跑前 6 步：从专栏初始化到出 05-review.md + 风格档案累积
- 4 种 verdict gate 模式已落地：
  - **二态**（outline）：passed / weak_section_unresolved
  - **三态**（research）：passed / passed_with_high_risk(+user_decision=accept) / 其他
  - **状态推进自动+显式 override**（write）：advance_status_to 双轨
  - **HIGH/passed 互斥**（review）：HIGH 存在不能 passed
- claim ID `C1..Cn` 在 prepare-discuss / prepare-research / prepare-outline 三处共享同一规则
- section ID `S1..Sn` 在 outline §<n> ↔ write target ↔ draft `## §<n>` ↔ review issue.location 四处对齐
- **风格学习闭环已落地**：write 写 history snapshot → review Phase 2 用 difflib diff → append .zero/style-profile.md → write 下次 prepare 必读 → AI 起稿越像作者

### STATE.md 解析契约（重要）
- `skills/write/szw-progress/references/state-schema.md` 是 STATE.md 表结构与 JSON 输出的**单一真相**
- 后续 szw-resume / szw-complete 的解析器必须对齐此文档（不需要共享代码，只需共享契约）
- **写 STATE.md 的逻辑**已在两处实现，均遵循"只动目标 section"原则：
  - `szw-new-article/scripts/new-article.py` 的 `append_to_active_table()` —— Active 表插行 + 清占位
  - `szw-discuss/scripts/finalize-discuss.py` 的 `update_active_row()` / `remove_from_active_and_add_to_completed()` —— 改 Active 行 / 移行到 Completed
  - **szw-complete 直接拷贝** finalize-discuss.py 的 `remove_from_active_and_add_to_completed()`，做 published 时 disposition='published'

### ARTICLE.md 字段契约
- `skills/write/szw-new-article/references/article-md-schema.md` 定义所有 frontmatter 字段
- 下游 skill（szw-discuss / szw-write / szw-publish 等）读 ARTICLE.md 时须遵守此契约
- type 4 选 1：industry-analysis / programmer-advice / product-analysis / tech-blog
- platform 子集 of [blog, wechat, x, xhs]

### Brief / Outline 字段契约
- `skills/write/szw-discuss/references/brief-schema.md` 定义 01-brief.md 渲染结构 + commit JSON
- `skills/write/szw-outline/references/outline-schema.md` 定义 03-outline.md 渲染结构 + commit JSON
- 两个 schema 共享 **claim ID 规则**：prepare-* 脚本按 brief.supporting_claims 顺序分配 `C1..Cn`；下游 outline / research / write 按此 ID 引用
- 修改任一 schema 须查另一个的同步清单（避免 ID 错位）

### 内部循环 / 弱节 escape 机制
- szw-outline 首次实现"弱 section 内部循环 + verdict gate"：`weak_section_unresolved` → exit 5
- szw-research 扩展为**三态 verdict gate**：passed / passed_with_high_risk(+user_decision=accept) / needs_rework
- 模板：内部最多 2 轮自愈；2 轮仍未解 → 必须显式 user_decision，不允许默认通过
- szw-review（v2.0）的 review_failed 循环可参考此模式

### 跨 prepare-* 脚本的解析共享
- `parse_active_table_rows()` / `pick_default_slug()`：在 prepare-discuss / prepare-research / prepare-outline 各有一份，规则一致
- `parse_frontmatter()`：解析 ARTICLE.md frontmatter；同上
- `parse_brief()` / `extract_section_lines()` / `parse_bullet_list()`：解析 01-brief.md；prepare-research / prepare-outline 共用
- `assign_claim_ids()`：C1..Cn 顺序分配；prepare-research / prepare-outline 共用
- 修任一规则须同步多文件；架构决策（HANDOFF §4.2）：当前不抽 _shared/，复制成本可控

### 早期参考
- 写作流程草稿：`write-progress/flow.md`
- 写作宪法草稿：`write-progress/EDITORIAL_CONTEXT.md`
- 决策记录草稿：`write-progress/ADR.md`

### Handoff（本文）
- `work/HANDOFF.md`

---

## 6. 工作偏好与协作约定

来自之前对话的累积约定：

1. **目录命名**：cwd 即 Column 根（不再询问容器名）
2. **路径风格**：fan.md 用 `Column/` 作占位符，但实际指 cwd
3. **命名前缀**：所有命令 `szw-` 前缀
4. **产物文件名**：与命令名脱钩（如 `01-brief.md` 来自 `/szw-discuss`）
5. **模板独立维护**：所有 templates 在 `<skill>/templates/` 子目录，可独立迭代
6. **薄 wrapper 风格**：SKILL.md 描述流程；scripts/ 承担确定性操作；references/ 放 schema / catalog
7. **设计文档优先**：先改 `study/fan.md`，再同步实现
8. **Mac 兼容**：脚本要兼容 macOS（如 `realpath` 不存在的 fallback）
9. **中文表述 + 英文 frontmatter**：description 用英文（便于 skill 路由），正文中文
10. **退出码语义清晰**：scripts 的退出码要分情况编号（参考 create-skeleton.sh / edit-config.py）

---

## 7. 进入下一轮 session 的 quick-start

clear context 后，按此序恢复：

```
1. 读 work/HANDOFF.md（本文）—— 5 分钟
2. 读 study/fan.md §2 速查表 + §3.0 状态机 —— 3 分钟
3. 读 skills/write/szw-init/SKILL.md 看一个完整 skill 范例 —— 5 分钟
4. 决定下一步要建的 skill（推荐 szw-progress 先）
5. 读对应 §3.X 设计 → 实现
```

或直接告诉新 session：

> 继续 szw 写作工作流建设。clear 前 v2.0 主流水线已跑到 review：10 个 /szw 命令 + szw-topic-grill 已建；风格学习闭环已落地。**新审计已出**：读 `work/REVIEW-2026-05-06.md` 看现状 + P0/P1 一致性问题 + 16 个未完成 skill 优先级。两条推荐路径：(a) **快**：先修 P0-2（next_action 带 slug，5 处一行改）+ 建 szw-publish + szw-complete，让 v1.0 端到端跑通到 published/；(b) **稳**：决定 EDITORIAL_CONTEXT 模板扩展（P0-1 完整修），先把根基理顺再继续。读 work/HANDOFF.md + work/REVIEW-2026-05-06.md 恢复上下文。

---

## 8. 累计的高频反模式（避免重犯）

1. **不要为 SKILL.md 内嵌大段模板** —— 抽到 `templates/` 子目录，便于迭代
2. **不要让用户手动建长期资产** —— 全部由 `/szw-init` 自动产出
3. **不要在 STATE.md 维护单个 current article** —— 多 article 并行需要 list 模型
4. **不要把所有内容塞 .zero/** —— 用户会交互的内容（articles / glossary / inbox / editorial-adr 等）必须显性
5. **不要让 Edit 工具替换长字符串** —— 中英文标点细节差异会导致 mismatch；用 sed 删除 + Edit 插入
6. **不要在脚本里硬编码 schema** —— 集中到 `references/<*>-schema.md` 让 AI 和人都能查

---

## 9. 当前 git 状态（参考）

整个 `Column/` 容器（包括 `.zero/`）应纳入 git 跟踪。
推荐 `.gitignore`：
- `Column/.zero/.continue-here`（pause 临时态）
- 可选 `Column/.zero/writing-history/*/0[2-9]-*.md`（细碎迭代日志不入版本）
- 可选 `Column/inbox/pending/`（碎片灵感不入版本）

注意：本项目 `zero-to-ai/` repo 当前不是 Column 容器（它是 skills 仓库），不要把这两个混淆。
