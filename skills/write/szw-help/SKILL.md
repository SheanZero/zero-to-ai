---
name: szw-help
description: Show available szw column commands organized by category, and recommend the next action based on current STATE.md. Use when starting fresh, when unsure what command to run, or to see all commands grouped by version (v1.0 / v2.0 / v3.0).
---

# szw-help

提供 szw 命令清单与下一步推荐。

## 何时使用

- 用户问"有哪些命令"/"怎么用 szw"
- 跑完 `/szw-init` 后想查命令
- 不确定当前阶段该用什么命令
- 显式调用 `/szw-help`

## 调用语法

| 形式 | 行为 |
|---|---|
| `/szw-help` | 默认：完整命令清单 + 下一步推荐 |
| `/szw-help <command>` | 单条命令详解（链接到对应 skill 目录的 SKILL.md） |
| `/szw-help --next` | 仅基于 STATE.md 推荐下一步（不列全量命令） |
| `/szw-help --by-version v1\|v2\|v3` | 按版本筛选 |
| `/szw-help --catalog` | 仅列分类清单（无下一步推荐） |

---

## 默认输出（`/szw-help` 无参数）

执行流程：

1. **检测专栏状态**：
   - 当前 cwd 下是否有 `.zero/`？
   - 如有：读 `.zero/STATE.md` 看 Active Articles 表 + 各 status
   - 如无：进入"未初始化"分支

2. **输出三段**：
   - **当前位置**：active articles 数 + 简报（单个时直接列；多个时按 last_touched 表显示；或"未初始化"）
   - **下一步推荐**：根据状态匹配下一推荐命令（见下表）
   - **完整命令清单**：摘要版，按 8 类列出（详见 [`references/commands-catalog.md`](./references/commands-catalog.md)）

控制输出 < 40 行。完整 catalog 通过链接展开。

---

## 下一步推荐规则（多 article 场景）

读 `<cwd>/.zero/STATE.md` 的 `## Active Articles` 表（每行：slug / status / last_touched / next action）：

### 全局推荐（无 active article 或单 active article 时）

| 整体状态 | 推荐下一步 | 理由 |
|---|---|---|
| 无 `.zero/`（未初始化） | `/szw-init` | 先建专栏才能用其他命令 |
| 已初始化，Active Articles 为空 | `/szw-new-article` | 起第一篇 |
| 仅一个 active article | 直接给该 article 的下一步（见下表） | 无需多选 |

### 单 article 状态 → 推荐命令

| article status | 推荐下一步 | 理由 |
|---|---|---|
| `created` | `/szw-discuss <slug>` | 拷问选题 |
| `brief_done` | `/szw-research <slug>`（v2.0+）/ `/szw-write <slug>`（v1.0） | 进入证据 / 起稿 |
| `research_done` | `/szw-outline <slug>` | 论证设计 |
| `outline_done` | `/szw-write <slug>` | 起稿 |
| `draft_done` | `/szw-review <slug>` | 反审 |
| `review_failed` | `/szw-write <slug> [section] --mode polish` | 修复 review HIGH issue |
| `review_passed` | `/szw-publish <slug>` | 打包发布 |
| `published` | `/szw-complete <slug>` | 终结流水线 |
| `paused` | `/szw-resume <slug>` | 恢复上下文 |
| `completed` / `archived` | （已不在 Active 表） | — |

### 多 article 优先级（≥ 2 个 active）

按下列优先级挑出"全局最该做"的：

1. **`review_failed`** —— HIGH issue 待修，最优先（流水线被 gate 卡住）
2. **`paused`** —— 已留 handoff，恢复成本低
3. **`last_touched` 最久** —— 避免某篇被忘记
4. 其他按 `last_touched` 降序

输出格式：默认列所有 active articles + 标注全局推荐；用 `--next` 仅输出全局推荐命令。

### 降级处理

- STATE.md 不存在 → "建议先 `/szw-init`"
- STATE.md 存在但 Active Articles 表损坏 → "建议 `/szw-resume --list` 手动浏览或重建 STATE.md"

---

## 单命令详解（`/szw-help <command>`）

例如 `/szw-help discuss` 或 `/szw-help /szw-discuss`：

1. 在 `references/commands-catalog.md` 查找该命令
2. 输出该命令的：
   - 用途
   - 触发条件
   - 调用语法
   - 衔接（前置 / 后续命令）
   - Skill 目录路径（如 `skills/write/szw-discuss/SKILL.md`）
3. 提示用户："要看完整流程定义，打开 `<skill_path>/SKILL.md`"

---

## 按版本筛选（`/szw-help --by-version v1`）

只列出指定版本的命令：

- `v1.0`：MVP 闭环（init / new-article / discuss / write / publish / context / adr / progress / resume / help / config = 11 个）
- `v2.0`：增强（research / outline / review / capture / quick / new-series = 6 个）
- `v3.0`：完整（retro / audit / glossary / evidence-bank / series / pause / stats / summary = 8 个）

---

## 完成 marker

不需要——纯展示命令，无 phase 间转移。

---

## 设计原则

1. **默认输出 < 40 行**：避免淹没用户视野；完整 catalog 通过链接展开
2. **下一步推荐基于 STATE.md**：不需要用户告知当前阶段
3. **命令清单单独维护**：在 [`references/commands-catalog.md`](./references/commands-catalog.md)，新增命令只改一处
4. **降级友好**：STATE.md 缺失 / 损坏时仍能输出基础帮助
5. **无副作用**：纯读取，不写任何文件

---

## 输出示例

### 示例 1：未初始化目录

```
📍 当前位置：未初始化（cwd 无 .zero/）

🎯 推荐下一步：/szw-init

📚 命令分类速览（26 个）：
1. 专栏生命周期 (3)：/szw-init /szw-stats /szw-summary
2. 创建入口 (2)：/szw-new-article /szw-new-series
3. 主流水线 (7)：/szw-discuss /szw-research /szw-outline /szw-write /szw-review /szw-publish /szw-complete
4. 轻量出口 (2)：/szw-capture /szw-quick
5. 长期资产 (4)：/szw-context /szw-adr /szw-glossary /szw-evidence-bank
6. 进度路由 (3)：/szw-progress /szw-resume /szw-pause
7. 复盘 (2)：/szw-retro /szw-audit
8. 系列管理 (1)：/szw-series
9. 配置 (2)：/szw-help /szw-config

完整 catalog：skills/write/szw-help/references/commands-catalog.md
单命令详解：/szw-help <command>
```

### 示例 2：当前在写文章 draft 阶段（单 active）

```
📍 当前位置：1 个 active article
   - 2026-05-skills-vs-gsd | status=draft_done | last_touched=2026-05-06

🎯 推荐下一步：/szw-review 2026-05-skills-vs-gsd
   → Codex 反审 + Phase 2 学风格

📚 完整命令分类：见 references/commands-catalog.md
```

### 示例 2b：多 article 并行场景

```
📍 当前位置：3 个 active articles

| Slug | Status | Last touched | Next |
|---|---|---|---|
| 2026-05-skills-vs-gsd | review_failed | 2026-05-06 | /szw-write S2 --mode polish |
| 2026-05-agentic-coding | brief_done | 2026-05-04 | /szw-research |
| 2026-05-claude-vs-codex | created | 2026-05-02 | /szw-discuss |

🎯 全局推荐：先修 review_failed
   → /szw-write 2026-05-skills-vs-gsd S2 --mode polish

提示：/szw-progress 看完整表 + 进度；/szw-resume <slug> 切换上下文
```

### 示例 3：单命令详解 `/szw-help discuss`

```
🔍 /szw-discuss —— 选题讨论拷问 + 文章 brief（合并）

用途：写前一对一拷问选题，逼出核心命题；产出 01-brief.md（含 grill 拷问附录）

触发：articles/<slug>/ARTICLE.md 已存在
衔接：前置 /szw-new-article；后续 /szw-research（v2.0）/ /szw-write（v1.0）
参与度：★★★★★ HIGH

完整定义：skills/write/szw-discuss/SKILL.md
```
