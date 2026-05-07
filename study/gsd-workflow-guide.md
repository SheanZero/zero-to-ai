# GSD 工作流指导建议

> 配套文档：[`gsd-research.md`](./gsd-research.md)（客观调研报告）
> 本文是**主观、可操作**的使用建议，基于调研结论 + 全局指令（`~/.claude/CLAUDE.md`）的项目类型识别策略。
> 编写日期：2026-05-06

---

## TL;DR

1. **先识项目类型**，再决定要不要用 GSD。代码项目 + 多周以上 + 跨 session = GSD；单文件 / vault / 一次性脚本 = 不用 GSD。
2. **梯度入场**：trivial 用 `/gsd-fast`，ad-hoc 用 `/gsd-quick`，正式工作走完整 phase 流水线，无人值守用 `/gsd-autonomous`。
3. **不要把 GSD 和 superpowers 叠用**。9 项核心工作流完全重叠，叠用 = 重复执行 brainstorming/TDD/verification/plans。
4. **每个 phase 都走 `discuss → plan → execute → verify → ship`**，不要跳步，跳步会回头补。
5. **状态恢复优先用 `/gsd-resume-work` 或 `/gsd-progress`**，不要每次新对话都 `/gsd-new-project`。

---

## 1. 决策矩阵：要不要用 GSD？

| 信号 | 推荐 | 理由 |
|---|---|---|
| `pwd` 下有 `.planning/` 目录 | **沿用 GSD** | 已经在 GSD 项目里，用 `/gsd-progress` 接续 |
| 代码项目 + 预计跨 ≥3 个 session | **新建 GSD 项目** | 上下文持久化与 milestone 概念才有 ROI |
| 代码项目 + 一次性脚本 / 单文件改动 | **不用 GSD** | 用 superpowers 或裸写；GSD 开销远大于收益 |
| Vault / 知识库 / 文档库 | **绝对不用 GSD** | 全局指令明确禁止；vault 用 `ingest`/`query`/`lint` |
| 已经在用 superpowers 体系 | **二选一** | 同一项目不要混用，详见 §4 |
| brownfield 接手陌生代码 | **GSD + 先 map** | `/gsd-map-codebase` 建索引，再 `/gsd-new-milestone` |
| 探索性研究 / 不确定要不要做 | **先 `/gsd-explore`** | Socratic 路由，再决定升级到哪个流程 |

---

## 2. 梯度入场：选对开销

GSD 自带 4 档梯度，**永远从最轻的开始**，不够再升级。

```
任务规模 →

trivial          ad-hoc 中等                 正式工作                    全自动
≤3 文件          多文件单一改动              多 phase 多 plan            无人值守
≤1 分钟          ≤1 小时                    ≥1 天                       milestone 级

/gsd-fast   →   /gsd-quick   →   /gsd-quick --full   →   完整 phase 流水线   →   /gsd-autonomous
```

### 2.1 何时升档

- `/gsd-fast` 触发 scope check 失败 → 升 `/gsd-quick`
- `/gsd-quick` 发现需要 cross-AI review / TDD / verification → 加 `--full`
- `/gsd-quick --full` 已经超过单一改动范围 → 升 `/gsd-phase` 加进 ROADMAP
- 整个 milestone 已 plan 完毕，user 不想逐 phase 守候 → `/gsd-autonomous`

### 2.2 不要做

- ❌ 用 `/gsd-fast` 改 5+ 文件 —— scope check 会拒绝，硬上会出锅
- ❌ 用完整 phase 流水线改一行 typo —— PLAN/SUMMARY/VERIFICATION 全套噪声
- ❌ 跳过 `/gsd-quick`，trivial 任务直接 `/gsd-plan-phase`

---

## 3. 推荐工作流模板

### 3.1 Greenfield 新项目（从零到 v1.0）

```
Day 0:  /gsd-new-project          # 一次性问答 + roadmap
Day N:  /clear
        /gsd-discuss-phase 1      # 锁决策
        /gsd-plan-phase 1         # 多 wave 计划
        /gsd-execute-phase 1      # wave 并行执行
        /gsd-verify-work 1        # UAT
        /gsd-ship 1               # PR
Day N+1: /clear → 重复 phase 2/3/...
最后:  /gsd-complete-milestone 1.0.0
```

**关键纪律**：
- 每个 phase 之间 `/clear`，避免上下文累积
- `/gsd-ship` 之前确认 verifier 状态是 `passed`，不要 `gaps_found` 还硬 ship
- 多 phase 等待人工时用 `/gsd-pause-work` 留 handoff，下次 `/gsd-resume-work`

### 3.2 Brownfield 接手项目

```
1. /gsd-map-codebase             # 4 mapper 并行扫描，产 7 份分析
2. /gsd-new-milestone "v2.0 ..." # 不是 new-project，因为代码已存在
3. （后续同 3.1 phase 流水线）
```

**为什么不直接 `/gsd-new-project`**：会试图重写 PROJECT.md / REQUIREMENTS，覆盖既有约定。`new-milestone` 模式会把现有代码当事实。

### 3.3 中途换会话恢复

```
1. /gsd-resume-work              # 读 STATE.md + .continue-here
2. /gsd-progress                 # 查看 6 维健康
3. /gsd-progress --next          # 自动判断该走哪一步
```

不要做：从头读 PROJECT.md / ROADMAP.md / 所有 phase 目录 —— STATE.md 已经是浓缩活记忆。

### 3.4 Phase 中发现需要紧急插队

```
/gsd-phase --insert <N>          # 在 phase N 后插入 N.1
                                 # 不破坏后续编号
```

或者捕获到 backlog：

```
/gsd-capture --backlog "需求描述" # 进 999.x 占位
                                 # 下个 milestone /gsd-review-backlog 提升
```

### 3.5 Verify 失败循环

```
/gsd-verify-work N        → status: gaps_found
/gsd-plan-phase N --gaps  → 基于 UAT.md 重新规划
/gsd-execute-phase N      → 只执行新 plan
/gsd-verify-work N        → 重新验证（UAT.md 续接）
```

**不要**直接手动改代码绕过 verifier —— UAT.md 会失同步，下次 ship 时 PR body 会乱。

### 3.6 跨 AI 评审强化计划质量

```
/gsd-plan-phase N
/gsd-review N --reviewers gemini,codex   # 调外部 CLI 独立评审
/gsd-plan-review-convergence N           # 自动 replan ↔ review 直到 0 HIGH
```

成本高，留给关键 phase（auth / 核心数据模型 / 第三方集成）。

---

## 4. GSD 与 superpowers 的并存策略

### 4.1 结论

**GSD 项目内部禁止叠用 superpowers**。理由（来自 `~/.claude/CLAUDE.md`）：9 项工作流完全重叠，重复执行 = 浪费时间 + 上下文翻倍。

### 4.2 重叠对照（详见调研报告 §1.3）

| superpowers skill | 在 GSD 里的等价物 |
|---|---|
| `brainstorming` | `gsd-discuss-phase` / `gsd-explore` / `gsd-spec-phase` |
| `test-driven-development` | `plan-phase --tdd` + `gsd-add-tests` |
| `verification-before-completion` | `gsd-verify-work` + verifier 子 agent |
| `dispatching-parallel-agents` | `execute-phase` 的 wave 并行 |
| `writing-plans` | `gsd-plan-phase` |
| `executing-plans` / `subagent-driven-development` | `gsd-execute-phase` |
| `using-git-worktrees` | `execute-phase` 的 `USE_WORKTREES` |
| `finishing-a-development-branch` | `gsd-ship` + `gsd-pr-branch` |
| `requesting-code-review` / `receiving-code-review` | `gsd-code-review` / `gsd-review` |

### 4.3 superpowers 仍然有价值的场景

| superpowers skill | 在 GSD 里**没有对应** | 仍然适用 |
|---|---|---|
| `writing-skills` | ✅ | 创建新 skill 时直接用 |
| `humanizer` | ✅ | 写文档 / 对外内容时过一遍 |
| `episodic-memory` | ✅ | 跨项目检索过往对话 |

### 4.4 非 GSD 项目仍然推荐 superpowers

如果不在 `.planning/` 项目里（比如修个小工具脚本、调个配置），用 superpowers 即可，不要为了"统一"硬上 GSD。

---

## 5. 配置建议

### 5.1 Model profile（`/gsd-config --profile`）

| 场景 | 推荐 profile |
|---|---|
| 商业关键 / 不能出错 / 一次写就 | `quality`（处处 Opus） |
| 日常开发 | `balanced`（Opus 规划 + Sonnet 执行）— **默认即可** |
| 个人项目 / 探索 / 预算紧 | `budget`（Sonnet 写 + Haiku 研究/验证） |
| 跑在 OpenCode 等多模型 CLI | `inherit` |

### 5.2 Workflow toggles（`/gsd-config`）

| Toggle | 推荐值 | 理由 |
|---|---|---|
| `mode` | `interactive`（默认） | 关键决策点暂停问人 |
| `mode` | `yolo` | 仅在 `/gsd-autonomous` 长跑时短暂切换 |
| `use_worktrees` | `true`（默认） | 真并行 + 隔离故障；除非 git submodule 复杂场景 |
| `worktree_skip_hooks` | `false`（默认） | pre-commit hook 是质量保险，别跳 |
| `text_mode` | 仅非 Claude CLI 时 `true` | AskUserQuestion 降级为编号列表 |

### 5.3 git 身份配置

调研报告显示当前提交身份是 `xinz@zhangxindeMacBook-Pro.local`（自动推断）。GSD 每个 task 一个 commit，commit 数量会快速积累，**先把全局身份配好**：

```bash
git config --global user.email "zxsheanjp@gmail.com"
git config --global user.name "Xin Zhang"
```

否则 GitHub 不会把这些 commit 计入贡献图。

---

## 6. 反模式速查

按"后悔率"从高到低排序。识别到立即停下。

| # | 反模式 | 立即该做 |
|---|---|---|
| 1 | Vault 项目里跑 GSD | 立刻 `rm -rf .planning/`，回到 vault 自己的工作流 |
| 2 | 同一项目叠用 GSD + superpowers | 选一个，删另一个的痕迹 |
| 3 | 单文件改动跑完整 phase 流水线 | 用 `/gsd-fast` 或 `/gsd-quick` |
| 4 | 跳过 `/gsd-discuss-phase` 直接 `plan-phase` | 回到 discuss，CONTEXT.md 是 planner 的灵魂 |
| 5 | 每次新对话 `/gsd-new-project` | 用 `/gsd-resume-work` 或 `/gsd-progress` |
| 6 | verifier 报 `gaps_found` 直接手动改代码 | 走 `/gsd-plan-phase N --gaps` 闭环 |
| 7 | `/gsd-autonomous` 不看就睡觉 | 第一次跑只跑 1 个 phase 验证作者契约后再放手 |
| 8 | `.planning/` commits 进了 PR | `/gsd-pr-branch` 重做干净分支 |
| 9 | 多 phase 之间不 `/clear` | 上下文累积导致后期 phase 质量崩塌 |
| 10 | 用 `/gsd-fast` 修隐含跨文件影响的"小 bug" | 升 `/gsd-quick`，让 planner 评估 blast radius |

---

## 7. 学习路径建议

如果你是第一次用 GSD，按这个顺序熟悉：

1. **必读 1 篇**：`/gsd-help` 输出（来自 `workflows/help.md`）
2. **试跑 1 次**：用一个真实小项目跑完 `/gsd-new-project → 1 phase → /gsd-ship`
3. **理解 5 个产物**：`PROJECT.md` / `ROADMAP.md` / `STATE.md` / `PLAN.md` / `VERIFICATION.md` —— 知道每个文件回答什么问题
4. **掌握 6 个命令**：`new-project / discuss-phase / plan-phase / execute-phase / verify-work / ship`
5. **熟悉 3 个出口**：`fast` / `quick` / `progress --do`
6. **配置 1 套偏好**：profile + workflow toggles + git 身份
7. **解锁高级**：`autonomous` / `review` (cross-AI) / `workstreams` / `manager` 多 phase 并管

不要一上来就读 65 个 SKILL，会被淹没。

---

## 8. 何时不要用任何工作流框架

- **学新技术 / 看官方教程**：直接跑代码，框架是干扰
- **5 分钟内能完成的事**：光读 SKILL 时间就花完了
- **debugging 一个具体错误**：用 `systematic-debugging` 或 `gsd-debug`，但不要为它建 phase
- **写一次性数据分析脚本**：跑完即弃，没有持久化价值

---

## 附：常用命令速记

| 想做什么 | 用什么 |
|---|---|
| 新代码项目，准备好搞它 | `/gsd-new-project` |
| 接手别人的 repo | `/gsd-map-codebase` → `/gsd-new-milestone` |
| 不知道接下来该做啥 | `/gsd-progress --next` |
| 用自然语言描述意图 | `/gsd-progress --do "..."` |
| 改个 typo | `/gsd-fast "fix typo in README"` |
| 加个功能（中等） | `/gsd-quick "add X"` 或 `/gsd-quick --full` |
| 正式 phase | `/gsd-discuss-phase N` → `/gsd-plan-phase N` → `/gsd-execute-phase N` → `/gsd-verify-work N` → `/gsd-ship N` |
| 暂停 / 续接 | `/gsd-pause-work` / `/gsd-resume-work` |
| 失败工作流 post-mortem | `/gsd-forensics` |
| 看进度 | `/gsd-progress` 或 `/gsd-stats` |
| 全自动跑完 milestone | `/gsd-autonomous` |
| 升级 GSD | `/gsd-update` |
| 查命令 | `/gsd-help` |
