# GSD（Get Shit Done）插件深度调研

> 调研对象：`gsd-build/get-shit-done`（npm 包 `get-shit-done-cc`），本地版本 **v1.40.0**
> 数据源：本地 `~/.claude/skills/gsd-*/`（65 个 SKILL）+ `~/.claude/get-shit-done/`（workflows / templates / references / bin）+ GitHub README
> 调研日期：2026-05-06

---

## 1. GSD 是什么 / 解决什么问题

**一句话定位**（README 原文）：
> *"A light-weight meta-prompting, context engineering, and spec-driven development system for Claude Code, OpenCode, Gemini CLI, Kilo, Codex, Copilot, Cursor, Windsurf, and more."*

一个面向 **solo agentic developer** 的轻量级元提示 / 上下文工程 / 规格驱动开发框架，跨多个 AI CLI 运行时通用。

### 1.1 为什么需要它（README 阐述的动机）

作者是单兵开发者，"用 Claude Code 写代码而不是自己写代码"。他需要一套工作流来对抗以下 Claude Code 原生不解决的问题：

- **Context rot（上下文腐烂）**："The quality degradation that happens as your AI fills its context window" —— 单一 200k 主上下文跑久了质量必然衰减。
- 现有 spec-driven 工具（如企业级敏捷工具）目标是 50+ 工程师团队，对 solo builder 太重。
- 缺乏 **session 之间的共享记忆**。
- 需要"不用手动 debug 的自动化"。

### 1.2 与原生 Claude Code 的差异

来源：README + `references/agent-contracts.md` + `references/git-integration.md`。

| 维度 | 原生 Claude Code | GSD |
|---|---|---|
| 上下文管理 | 单一会话，线性堆积 | 主窗口保持 30–40%，重活 fork 给 fresh-200k 子 agent |
| 记忆 | session 结束即丢 | `.planning/` 目录持久化（PROJECT/REQUIREMENTS/ROADMAP/STATE/CONTEXT/PLAN/SUMMARY/VERIFICATION） |
| 任务粒度 | 自由对话 | Project → Milestone → Phase → Plan → Task 五层结构 |
| Verification | 由用户提示 | 内置 verifier loop + UAT 持久化 + Nyquist 采样审计 |
| 并行 | 偶发 Task tool | wave-based 并行执行 + git worktree 隔离 |
| Git 集成 | 由用户驱动 | 每个 task 一个原子 commit；conventional 格式；规划文档与代码可分流（gsd-pr-branch） |
| 提示工程 | 手工编写 | 内置 XML 块、`gsd-sdk query` 命令注入结构化 init JSON |

### 1.3 与 superpowers 的差异

README 没有显式对比 superpowers，但从本地已加载的 skill 列表可以直接观察重叠：

| 概念 | superpowers 提供 | GSD 等价物 | 重复 / 互补 |
|---|---|---|---|
| 创意前思考 | `brainstorming` | `gsd-discuss-phase`、`gsd-explore`、`gsd-spec-phase` | **重复** |
| TDD | `test-driven-development` | `plan-phase --tdd` + `references/tdd.md` + `gsd-add-tests` | **重复** |
| 完成前验证 | `verification-before-completion` | `gsd-verify-work` + verifier 子 agent + gates 体系 | **重复** |
| 子 agent 并行 | `dispatching-parallel-agents` | `execute-phase` 的 wave-based 并行 + 9+ 个 GSD 专属子 agent | **重复** |
| 写 plan | `writing-plans` | `gsd-plan-phase` + `templates/phase-prompt.md` | **重复** |
| 执行 plan | `executing-plans` / `subagent-driven-development` | `gsd-execute-phase` | **重复** |
| Worktree 隔离 | `using-git-worktrees` | `execute-phase` 内置 `USE_WORKTREES` 配置 | **重复** |
| 收尾上线 | `finishing-a-development-branch` | `gsd-ship` + `gsd-pr-branch` | **重复** |
| Code review | `requesting-code-review` / `receiving-code-review` | `gsd-code-review`、`gsd-review`（cross-AI）、`gsd-ns-review` | **重复**（GSD 更重） |
| 系统化调试 | `systematic-debugging` | `gsd-debug`（持久化）、`gsd-forensics` | **重复**（GSD 跨 session） |
| 写 skill | `writing-skills` | 无对应 | superpowers 独有 |

**结论**：GSD 是 superpowers 整套理念的"重型版" —— 把同样的 brainstorm → plan → TDD → execute → verify → ship 概念全部具象化为命名的 `/gsd-*` 命令，并加上文件持久化和 phase 层级。两者叠用会重复触发同一类工作流。

---

## 2. 核心心智模型

来源：`workflows/help.md` 的 *Files & Structure* 章节、`templates/roadmap.md`、`templates/state.md`。

### 2.1 概念层级

```
Project (一次)
└── Milestone v1.0, v1.1, v2.0 ...   ← /gsd-new-milestone
    └── Phase 1, 2, 3 ...             ← ROADMAP.md 中的有序节点
        ├── Plan 01-01, 01-02, ...    ← 一个 phase 可有多个 plan
        │   └── Task                  ← 一个 plan 内的有序任务，每 task 一个 commit
        └── Wave 1, 2, ...            ← plan 通过 frontmatter `wave:` 分组并行
```

特殊节点：
- **Decimal phase**（如 7.1）：`/gsd-phase --insert 7` 在已规划进度中插入紧急工作，不破坏后续编号
- **999.x backlog phase**：`/gsd-capture --backlog` 占位，未来 milestone 再升级
- **Quick task**：游离于 phase 之外，存于 `.planning/quick/NNN-slug/`
- **Workstream / Thread**：跨 phase 的并行工作流 / 跨 session 的对话上下文（独立索引）

### 2.2 `.planning/` 目录约定（来源 help.md）

```
.planning/
├── PROJECT.md            ← 项目愿景，一次写就基本不动
├── REQUIREMENTS.md       ← 带 REQ-ID 的需求清单（v1/v2/out-of-scope 分级）
├── ROADMAP.md            ← phases 列表 + 每个 phase 的 success criteria + 依赖
├── STATE.md              ← 项目活记忆（current phase / progress / decisions / pending todos）
├── RETROSPECTIVE.md      ← 跨 milestone 累积的回顾
├── config.json           ← 工作流模式（interactive / yolo）+ 各种 toggle
├── todos/                ← /gsd-capture
│   ├── pending/          ← 待处理 todo
│   └── done/
├── notes/                ← /gsd-capture --note
├── spikes/               ← /gsd-spike 实验目录 + MANIFEST.md
├── sketches/             ← /gsd-sketch HTML mockups + themes/
├── debug/                ← /gsd-debug 跨 /clear 持久化的调查会话
│   └── resolved/
├── codebase/             ← /gsd-map-codebase 产出 7 份分析（STACK/ARCHITECTURE/...）
├── intel/                ← /gsd-map-codebase --query 索引
├── graphs/               ← /gsd-graphify 知识图谱
├── research/             ← 项目级研究产出
├── quick/NNN-slug/       ← /gsd-quick 任务目录
├── milestones/           ← 已 archive 的 milestone snapshot
│   ├── v1.0-ROADMAP.md
│   ├── v1.0-REQUIREMENTS.md
│   └── v1.0-phases/      ← 旧 phase 目录归档
└── phases/
    └── 01-foundation/
        ├── 01-CONTEXT.md          ← discuss-phase 产出
        ├── 01-RESEARCH.md         ← phase-researcher 产出
        ├── 01-SPEC.md             ← spec-phase 产出（可选）
        ├── 01-UI-SPEC.md          ← ui-phase 产出（可选）
        ├── 01-AI-SPEC.md          ← ai-integration-phase 产出（可选）
        ├── 01-01-PLAN.md          ← planner 产出
        ├── 01-01-SUMMARY.md       ← executor 产出
        ├── 01-VERIFICATION.md     ← verifier 产出
        ├── 01-UAT.md              ← verify-work 产出（可恢复）
        ├── 01-REVIEWS.md          ← gsd-review cross-AI 评审结果
        └── 01-DEBUG.md            ← debug 会话
```

---

## 3. 主流程（happy path）

完整 greenfield 项目从想法到交付，按 `workflows/help.md` 的 *Common Workflows* + 实际工作流文件还原：

| 步 | 命令 | 实际做了什么 | 关键产物 | 衔接 |
|---|---|---|---|---|
| 0 | （可选）`/gsd-map-codebase` | brownfield 扫描，4 个 mapper agent 并行 | `.planning/codebase/{STACK,ARCHITECTURE,STRUCTURE,CONVENTIONS,TESTING,INTEGRATIONS,CONCERNS}.md` | new-project 会自动检测到 |
| 1 | `/gsd-new-project` | 深度问答 → 4 个 researcher 并行 → 综合 → roadmapper 产出 phase 列表 | `PROJECT.md` `REQUIREMENTS.md` `ROADMAP.md` `STATE.md` `config.json` `research/` | 第 1 个 commit `docs: initialize ...` |
| 2 | `/clear` + `/gsd-discuss-phase 1` | 识别 gray areas，用户作为"愿景方"决定 HOW，Claude 作为"建造方"记录决策 | `01-CONTEXT.md` + 可选 `01-SPEC.md` | locked decisions 喂给下游 |
| 3 | `/gsd-plan-phase 1` | researcher → planner → plan-checker（最多 3 轮 revision loop）→ verifier loop | `01-RESEARCH.md` + `01-01-PLAN.md`（含 frontmatter `wave/depends_on/files_modified`）+ `01-REVIEWS.md`（如果走 cross-AI） | PLAN 通过 plan-checker 才进入下步 |
| 4 | `/gsd-execute-phase 1` | 按 `wave` 字段分组，wave 内并行（默认走 git worktree 隔离），每 task 一个原子 commit | `01-01-SUMMARY.md`（commits 表 + deviations + self-check）+ 真实代码 commits | wave-by-wave，全完后跑 verifier |
| 5 | `/gsd-verify-work 1` | 对话式 UAT，"展示预期，问现实是否匹配"，逐项 yes/no | `01-UAT.md`（可跨 /clear 恢复）+ `01-VERIFICATION.md`（status: passed / gaps_found / human_needed） | gaps_found → `/gsd-plan-phase 1 --gaps` 回到第 3 步 |
| 6 | `/gsd-ship 1` | preflight（verification passed？clean tree？on feature branch？gh ready？）→ 推 remote → 用 SUMMARY/VERIFICATION/REQUIREMENTS 自动写 PR body | GitHub PR | 可选 `--draft`、可选 cross-AI review |
| 7 | （重复 2–6 直到 milestone 所有 phase 完成） | | | |
| 8 | `/gsd-complete-milestone 1.0.0` | 写 `MILESTONES.md` 条目，archive 到 `milestones/v1.0-*`，打 git tag | 历史 snapshot + tag | 进入下一版本 |
| 9 | `/gsd-new-milestone "v2.0 Features"` | 重复 1 的 questioning → research → requirements → roadmap，但是 brownfield | 新一轮 ROADMAP/REQUIREMENTS（可选 `--reset-phase-numbers`） | 回到第 2 步 |

**自动化出口**：`/gsd-autonomous [--from N --to N]` 把 2 → 5 串成无人值守循环；`/gsd-progress --next` 每次自动推进一步；`/gsd-progress --do "<text>"` 自然语言路由到正确命令。

---

## 4. 命令分类（全 65 个 skill）

来源：本地 `~/.claude/skills/` 目录 + 6 个 `gsd-ns-*` 命名空间索引（揭示作者的官方分类）。

### 4.1 项目生命周期（5）

| 命令 | 用途 |
|---|---|
| `gsd-new-project` | 初始化项目（问答 + 研究 + 需求 + 路线图） |
| `gsd-new-milestone` | 启动新 milestone 版本 |
| `gsd-complete-milestone` | 归档当前 milestone + 打 tag |
| `gsd-audit-milestone` | 审计 milestone 完成度 vs 原始意图 |
| `gsd-milestone-summary` | 生成 milestone 汇总（团队 onboarding 用） |

### 4.2 Phase 流水线（核心 6 步）

| 命令 | 用途 |
|---|---|
| `gsd-spec-phase` | 用 ambiguity scoring 澄清 phase 交付什么（产出 SPEC.md） |
| `gsd-discuss-phase` | 用问答捕获实现决策（产出 CONTEXT.md） |
| `gsd-plan-phase` | researcher + planner + plan-checker 三段式产出 PLAN.md |
| `gsd-execute-phase` | wave-based 并行执行，原子 commits |
| `gsd-verify-work` | 对话式 UAT，diagnose → fix |
| `gsd-ship` | 创建 PR，自动写 body |

### 4.3 Roadmap 与 phase CRUD（2）

| 命令 | 用途 |
|---|---|
| `gsd-phase` | 添加 / 插入 / 删除 / 编辑 phase（合并了原 add/insert/remove/edit-phase） |
| `gsd-review-backlog` | review 999.x backlog 并提升到当前 milestone |

### 4.4 轻量出口 / 快速通道（2）

| 命令 | 用途 |
|---|---|
| `gsd-fast` | trivial 任务内联执行（≤3 文件 + ≤1 分钟），无 PLAN，无 subagent |
| `gsd-quick` | 中等任务，spawn planner+executor，跳过 researcher/checker/verifier；可用 `--full` 完整品控 |

### 4.5 高级 phase 类型 / 专门规格（3）

| 命令 | 用途 |
|---|---|
| `gsd-ui-phase` | 产出 UI-SPEC.md（前端 phase 设计契约） |
| `gsd-ai-integration-phase` | 产出 AI-SPEC.md（AI 系统设计契约） |
| `gsd-ultraplan-phase` | [BETA] 把 plan-phase 卸载到 Claude Code ultraplan 云 |

### 4.6 计划质量与跨 AI 评审（4）

| 命令 | 用途 |
|---|---|
| `gsd-review` | 调外部 AI CLI（Gemini/Codex/CodeRabbit/OpenCode/Qwen/Cursor）独立评审 phase plan |
| `gsd-plan-review-convergence` | replan ↔ review 收敛循环，直到无 HIGH 级别 concern |
| `gsd-import` | 摄取外部 plan，与项目决策做冲突检测 |
| `gsd-ingest-docs` | 从仓库已有 ADR/PRD/SPEC 文档 bootstrap `.planning/` |

### 4.7 验证与审查 quality gates（10，对应 `gsd-ns-review`）

| 命令 | 用途 |
|---|---|
| `gsd-code-review` | 审查 phase 期间改动的源文件（`--fix` 自动修） |
| `gsd-secure-phase` | 回溯式安全审查（威胁缓解验证） |
| `gsd-validate-phase` | 回溯式 Nyquist 验证覆盖审计 |
| `gsd-ui-review` | 6 维度视觉审查 |
| `gsd-eval-review` | AI phase 的 evaluation 覆盖率审查 |
| `gsd-audit-uat` | 跨 phase 的 UAT 与验证待办审计 |
| `gsd-audit-fix` | audit → 分类 → 修 → 测 → commit 的全自动管线 |
| `gsd-add-tests` | 基于 UAT 标准为已完成 phase 生成测试 |
| `gsd-debug` | 持久化调试会话（跨 /clear） |
| `gsd-forensics` | 失败 GSD 工作流的 post-mortem |

### 4.8 探索 / 想法捕获（5，对应 `gsd-ns-ideate`）

| 命令 | 用途 |
|---|---|
| `gsd-explore` | Socratic 思辨，把想法路由到合适的下一步 |
| `gsd-sketch` | UI 草图（多 variant HTML mockup） |
| `gsd-spike` | 时间盒技术 spike |
| `gsd-spec-phase` | （见 4.2） |
| `gsd-capture` | 通用捕获入口（`--note` / `--seed` / `--backlog` / `--list`） |

### 4.9 知识 / 代码库智能（5，对应 `gsd-ns-context`）

| 命令 | 用途 |
|---|---|
| `gsd-map-codebase` | 4-mapper 并行扫描，产出 7 份 codebase/*.md（含 `--fast` `--query` 子模式） |
| `gsd-graphify` | 构建 / 查询知识图谱 `.planning/graphs/` |
| `gsd-docs-update` | 生成 / 更新文档并对照代码验证 |
| `gsd-extract-learnings` | 从已完成 phase 抽 decisions / lessons / patterns / surprises |
| `gsd-ingest-docs` | （见 4.6） |

### 4.10 进度 / 路由 / 自动化（4）

| 命令 | 用途 |
|---|---|
| `gsd-progress` | 默认显示进度报告 + 路由；`--next` 推进；`--forensic` 6 维健康；`--do "<text>"` 自然语言路由 |
| `gsd-autonomous` | 把剩余 phases 全自动跑完 |
| `gsd-manager` | 多 phase 同时管理的交互式控制台 |
| `gsd-stats` | 统计 phases / plans / git metrics / timeline |

### 4.11 会话与并行管理（5，对应 `gsd-ns-manage`）

| 命令 | 用途 |
|---|---|
| `gsd-pause-work` | 创建 `.continue-here` handoff |
| `gsd-resume-work` | 从 STATE.md 恢复上次会话 |
| `gsd-thread` | 跨 session 持久化对话上下文 |
| `gsd-workstreams` | 并行工作流 list/create/switch/status/progress/complete/resume |
| `gsd-workspace` | 工作区 isolated 环境管理（new/list/remove） |

### 4.12 配置与运维（6）

| 命令 | 用途 |
|---|---|
| `gsd-help` | 命令参考 |
| `gsd-config` | 统一配置入口（`--profile` / `--advanced` / `--integrations`，吸收了原 settings/settings-advanced/settings-integrations） |
| `gsd-settings` | 基本 toggle 与 model profile（仍保留作为快捷） |
| `gsd-update` | 升级 GSD（`--sync` / `--reapply`） |
| `gsd-cleanup` | 归档累积的 phase 目录 |
| `gsd-health` | 诊断 `.planning/` 目录健康，`--repair` 修复 |
| `gsd-undo` | 用 phase manifest 做安全 revert（带依赖检查） |

### 4.13 Git / PR 集成（2）

| 命令 | 用途 |
|---|---|
| `gsd-pr-branch` | 把 `.planning/` commits 过滤掉，做出干净 PR 分支 |
| `gsd-inbox` | triage GitHub issues / PRs |

### 4.14 用户画像与归档（2）

| 命令 | 用途 |
|---|---|
| `gsd-profile-user` | 生成开发者行为 profile，注入 Claude 可发现的 artifact |
| `gsd-extract-learnings` | （见 4.9） |

### 4.15 命名空间 meta-skill（6，作者明确说明"primarily for the model to perform two-stage hierarchical routing"）

| 命令 | 路由到 |
|---|---|
| `gsd-ns-workflow` | discuss / spec / plan / execute / verify / phase / progress |
| `gsd-ns-project` | new-project / new-milestone / complete-milestone / audit-milestone / milestone-summary |
| `gsd-ns-context` | map-codebase / graphify / docs-update / extract-learnings |
| `gsd-ns-ideate` | explore / sketch / spike / spec-phase / capture |
| `gsd-ns-manage` | config / workspace / workstreams / thread / pause / resume / update / ship / inbox / pr-branch / undo |
| `gsd-ns-review` | code-review / debug / forensics / audit-uat / secure / eval / ui-review / validate |

合计：5 + 6 + 2 + 2 + 3 + 4 + 10 + 5 + 5 + 4 + 5 + 6 + 2 + 2 + 6 = **65 skill**（与本地 `ls` 一致，含 1 个 `add-tests`、1 个 `audit-fix` 等单独条目）。

---

## 5. 核心工具与机制

### 5.1 子 agent 注册表

来源：`references/agent-contracts.md`。GSD 注册了约 **20 个专用子 agent**，每个有固定的 completion marker（H2 标题），orchestrator 用 regex 匹配判断完成。

| Agent | 角色 | Completion marker |
|---|---|---|
| `gsd-planner` | 创建 PLAN.md | `## PLANNING COMPLETE` |
| `gsd-executor` | 执行 plan、写 commits、产 SUMMARY.md | `## PLAN COMPLETE`, `## CHECKPOINT REACHED` |
| `gsd-phase-researcher` | phase 级技术研究 | `## RESEARCH COMPLETE / BLOCKED` |
| `gsd-project-researcher` | 项目级研究 | `## RESEARCH COMPLETE / BLOCKED` |
| `gsd-research-synthesizer` | 多研究综合 | `## SYNTHESIS COMPLETE / BLOCKED` |
| `gsd-plan-checker` | 计划质量审查 | `## VERIFICATION PASSED / ISSUES FOUND` |
| `gsd-verifier` | 执行后验证 | `## Verification Complete`（title case） |
| `gsd-debugger` | 调试调查 | `## DEBUG COMPLETE / ROOT CAUSE FOUND` |
| `gsd-roadmapper` | 路线图创建 / 修订 | `## ROADMAP CREATED / REVISED / BLOCKED` |
| `gsd-codebase-mapper` | 代码库分析 | 直接写文件，无 marker |
| `gsd-pattern-mapper` | 现有模式分析（PATTERNS.md） | — |
| `gsd-integration-checker` | 跨 phase 集成检查 | `## Integration Check Complete` |
| `gsd-nyquist-auditor` | 采样审计 | `## PARTIAL / ESCALATE` |
| `gsd-security-auditor` | 安全审计 | `## OPEN_THREATS / ESCALATE` |
| `gsd-ui-researcher` | UI-SPEC 创建 | `## UI-SPEC COMPLETE / BLOCKED` |
| `gsd-ui-checker` | UI 实现验证 | `## ISSUES FOUND` |
| `gsd-ui-auditor` | UI 设计审计 | `## UI REVIEW COMPLETE` |
| `gsd-assumptions-analyzer` | 假设抽取 | 返回 `## Assumptions` 段 |
| `gsd-doc-writer` / `gsd-doc-verifier` | 文档生成 / 验证 | 写 artifact / JSON |
| `gsd-advisor-researcher` | 顾问式研究 | utility |
| `gsd-user-profiler` | 用户画像 | 返回 JSON |
| `gsd-intel-updater` | codebase 智能更新 | `## INTEL UPDATE COMPLETE / FAILED` |

### 5.2 关键产物文件类型

| 文件 | 创建命令 | 内容 | 持久化层级 |
|---|---|---|---|
| `PROJECT.md` | new-project | 愿景 + 核心价值 | 项目级 |
| `REQUIREMENTS.md` | new-project | REQ-ID 化的需求（v1/v2/out-of-scope） | milestone 级 |
| `ROADMAP.md` | new-project / new-milestone | phases + success criteria + 依赖 | milestone 级 |
| `STATE.md` | new-project | 活记忆（current phase / progress bar / decisions / metrics / pending todos） | 项目级，session 间共享 |
| `config.json` | new-project | mode（interactive/yolo）+ workflow toggles + 模型 profile | 项目级 |
| `CONTEXT.md` | discuss-phase | locked 决策（feeds planner） | phase 级 |
| `SPEC.md` | spec-phase | WHAT 契约 + ambiguity score | phase 级 |
| `UI-SPEC.md` / `AI-SPEC.md` | ui-phase / ai-integration-phase | 专门规格 | phase 级 |
| `RESEARCH.md` | plan-phase --research | researcher 产出 | phase 级 |
| `PATTERNS.md` | pattern-mapper | 现有代码模式 | phase 级 |
| `PLAN.md`（多个 `XX-YY-PLAN.md`） | plan-phase | frontmatter（wave/depends_on/files_modified/autonomous/requirements）+ tasks + verification + success_criteria | plan 级 |
| `SUMMARY.md` | execute-phase | commits 表 + deviations + self-check（PASSED/FAILED） | plan 级 |
| `VERIFICATION.md` | execute-phase / verify-work | status: passed / gaps_found / human_needed | phase 级 |
| `UAT.md` | verify-work | 测试逐项进度，**支持跨 /clear 恢复** | phase 级 |
| `REVIEWS.md` | gsd-review | per-reviewer 反馈 + 共识 | phase 级 |
| `DEBUG.md` | gsd-debug | 调查时间线（evidence → hypothesis → test） | 跨 session |
| `MILESTONES.md` + `milestones/v*-*` | complete-milestone | 历史 snapshot | 项目级 |

### 5.3 状态管理机制

- **STATE.md 即活记忆**：每个工作流入口都先 `gsd-sdk query state-snapshot` 拉取结构化片段，避免读全文
- **Checkpoints**（`references/checkpoints.md`）：长操作里的可恢复点；executor 用 `## CHECKPOINT REACHED` 暂停
- **gsd-sdk query**（来自 `bin/gsd-tools.cjs`）：所有 workflow 通过这个 CLI 工具拉取 init JSON、roadmap 分析、commit 操作；让 prompt 只接收 path + 元数据，把 **静态 prompt 开销** 减到最小
- **Gates 体系**（`references/gates.md`）：4 类 gate —— Pre-flight（拒绝进入）/ Revision（带迭代上限的回环）/ Escalation（升级给人）/ Abort（保护性终止）。每个 workflow 都对应 gate matrix
- **Atomic commits**（`references/git-integration.md`）：每 task 一 commit，conventional 格式 `{type}({phase}-{plan}): {task}`；plan 完成另起一个 metadata commit；并行 executor 也走 pre-commit hook（除非 `worktree_skip_hooks=true`）
- **Worktree 隔离**：默认 `workflow.use_worktrees=true`，wave 内 plan 走独立 worktree 真并行；遇到 git submodule 时按 plan 是否触及 submodule path 做 per-plan 判断

### 5.4 Model profile（`gsd-config --profile`）

| Profile | 分配 |
|---|---|
| `quality` | 处处用 Opus（除 verification） |
| `balanced`（默认） | Opus 规划、Sonnet 执行 |
| `budget` | Sonnet 写、Haiku 研究/验证 |
| `inherit` | 全部继承当前 session 模型（OpenCode `/model`） |

### 5.5 跨运行时支持

`new-project.md` 第 1 步会探测 `RUNTIME=claude|codex|gemini|opencode`，并切换 `INSTRUCTION_FILE`（CLAUDE.md vs AGENTS.md）。`AskUserQuestion` 在不支持的运行时降级为 plain-text 编号列表（`workflow.text_mode=true`）。

---

## 6. GSD vs superpowers 对比

| 维度 | superpowers | GSD |
|---|---|---|
| 形态 | 一组 trigger-driven skill（无目录约定） | 65 个 `/gsd-*` 显式命令 + 强制 `.planning/` 目录 |
| 触发方式 | description-based 自动激活 | 用户显式 `/gsd-*` 调用（少数命名空间 skill 是模型自路由） |
| 持久化 | 不内置（依赖外部 episodic-memory） | 强制持久化到 `.planning/` |
| 子 agent 池 | 通用 dispatching-parallel-agents | 20 个专用 agent + 完成 marker 协议 |
| 适用规模 | 任意大小 | 多 phase / 多 milestone 项目 |
| 学习成本 | 低 | 中（需理解 phase / wave / gate 模型） |

**重叠的 9 项工作流**已在 §1.3 表中列出。**GSD 全局指令明确告诫："GSD 项目不要叠用 superpowers"**（`~/.claude/CLAUDE.md`）。

**互补关系**：
- superpowers 的 `writing-skills` / `humanizer` / `episodic-memory` 在 GSD 里没有对应 → 可以并存
- GSD 的 phase 流水线 / cross-AI review / 持久化 UAT / forensics / Nyquist 审计 / atomic commits + pr-branch 在 superpowers 里没有对应 → GSD 在"工程纪律"维度更厚

**如何选**：
- 单文件改 / 探索性调研 / 小工具脚本 → superpowers（或 GSD 的 fast/quick）
- 有 milestone 概念、需要多人查阅历史、需要跨 session 续接 → GSD
- GSD 项目内部不要再叠 superpowers 的 brainstorming/TDD/verification/plans —— 已被 GSD 等价物覆盖

---

## 7. 适用场景与反模式

### 7.1 适合 GSD

来源：README + `gsd-fast` / `gsd-quick` 的 scope check 反推。

- 持续多周以上的 solo 项目，跨多个 session
- 需要 milestone / 版本概念（v1.0 → v2.0 演进）
- 需要可审计的开发记录（每步 commit、planning artifact 全留档、可生成 onboarding summary）
- 多 phase 之间有依赖、需要并行执行同 phase 内的独立 plan
- brownfield 接手陌生代码（先 `/gsd-map-codebase` 建索引）

### 7.2 不适合 GSD（反模式）

来源：`gsd-fast.md` 自带的 scope check + `gsd-quick.md` 的设计意图。

- **trivial 任务**：typo 修复 / 配置改动 / 加 .gitignore 一行 / 忘了 commit —— 用 `/gsd-fast`，不用建 phase
- **中等 ad-hoc 任务**：单一改动但多文件 —— 用 `/gsd-quick`，写到 `.planning/quick/` 不进 ROADMAP
- **vault / 知识库**：用户全局指令明确 "GSD 是为代码项目设计，vault 用了只产生 `.planning/` 噪声"
- **GSD 项目里再叠 superpowers**：重复触发 brainstorming / TDD / verification / plans
- **每次新对话都 `/gsd-new-project`**：PROJECT.md 是一次性的，后续用 `/gsd-resume-work` 或 `/gsd-progress`
- **跳过 discuss-phase 直接 plan**：会失去 CONTEXT.md 锁定的决策，researcher 与 planner 容易产出不符合愿景的方案。如果已有 PRD 可用 `--prd` 旁路

### 7.3 GSD 内部的"轻量出口"梯度

```
/gsd-fast       (≤3 文件 / ≤1 分钟，无 PLAN，无 subagent)
   ↓ 超出
/gsd-quick      (有 PLAN，跳 researcher/checker/verifier)
   ↓ 加 --discuss --research --validate 或 --full
/gsd-quick --full   (完整品控但仍在 .planning/quick/)
   ↓ 升级到正式 phase
/gsd-phase + /gsd-plan-phase + /gsd-execute-phase + /gsd-verify-work + /gsd-ship  (完整流水线)
   ↓ 串成无人值守
/gsd-autonomous
```

---

## 附：关键文件路径速查

| 内容 | 路径 |
|---|---|
| 命令权威参考（`gsd-help` 实际渲染的内容） | `~/.claude/get-shit-done/workflows/help.md` |
| Agent 注册表与 marker 协议 | `~/.claude/get-shit-done/references/agent-contracts.md` |
| Git 集成与 commit 格式 | `~/.claude/get-shit-done/references/git-integration.md` |
| Gates 分类法 | `~/.claude/get-shit-done/references/gates.md` |
| 65 个 SKILL（薄 wrapper） | `~/.claude/skills/gsd-*/SKILL.md` |
| 主流程 workflow 全文 | `~/.claude/get-shit-done/workflows/{new-project,discuss-phase,plan-phase,execute-phase,verify-work,ship,autonomous,quick,fast,progress}.md` |
| 文件模板 | `~/.claude/get-shit-done/templates/*.md` |
| 6 个命名空间路由（揭示官方分类） | `~/.claude/skills/gsd-ns-{workflow,project,context,ideate,manage,review}/SKILL.md` |
| SDK 工具 | `~/.claude/get-shit-done/bin/gsd-tools.cjs`（被 `gsd-sdk query` 调用） |
| 版本号 | `~/.claude/get-shit-done/VERSION` |
