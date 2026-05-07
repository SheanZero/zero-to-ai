---
name: szw-progress
description: Show progress of all active articles with per-article next-step recommendations. Default route command for multi-article workflows. Recommends the highest-priority next action when invoked without args; supports natural-language routing via --do "<text>". Use when unsure what to do next, when juggling multiple articles in parallel, or when starting a fresh session and want a quick situational overview.
---

# szw-progress

多 article 进度路由。读 `.zero/STATE.md` 的 Active Articles 表，按优先级排序、推荐下一步。

## 何时使用

- 用户问"接下来该做啥"/"现在到哪了"
- 多 article 并行时想看全局视图
- 新会话不确定 resume 哪篇时（先 progress，再 resume）
- 用户用自然语言描述意图（"我想继续昨天那篇"），用 `--do` 路由

## 何时不用

- `.zero/` 不存在 → 先 `/szw-init`
- 想看命令清单 → `/szw-help`
- 想恢复某篇上下文（已经知道 slug）→ 直接 `/szw-resume <slug>`
- 想改配置 → `/szw-config`

---

## 调用语法

| 形式 | 行为 |
|---|---|
| `/szw-progress` | 默认：所有 active articles 进度表 + 全局推荐 |
| `/szw-progress <slug>` | 单 article 详情：status、阶段产物清单、下一步推荐 |
| `/szw-progress --next` | 仅输出全局推荐命令（一行） |
| `/szw-progress --do "<text>"` | 自然语言路由：根据用户描述匹配 slug + 命令 |
| `/szw-progress --completed` | 列 Recently Completed 表（最近 N 篇已完成） |

底层调用 [`scripts/parse-state.py`](./scripts/parse-state.py)，自动从 cwd 向上找 `.zero/STATE.md`。

---

## 执行流程

### 默认（`/szw-progress` 无参数）

1. 跑 `parse-state.py active` 拿到结构化 JSON
2. 检查 `active_count`：
   - 0 → "无 active article。建议 `/szw-new-article` 起新文章。"
   - 1 → 直接展开该 article 的下一步推荐（无需多选）
   - ≥ 2 → 渲染表格 + 全局推荐
3. 渲染输出（见 [输出示例](#输出示例)）

### `<slug>` 模式

1. 跑 `parse-state.py article <slug>`
2. 输出该 article 的：
   - 元数据：slug / status / last_touched / days_since_touched
   - 阶段产物清单：按 PHASE_FILES 顺序，标注 ✅ exists / ⛔ missing / ⭐ status_required
   - 下一步推荐：command + reason
3. 退出码 2（slug 不在 active）→ 提示是否在 Recently Completed 或建议 `/szw-help` 查命令

### `--next` 模式

1. 跑 `parse-state.py active`
2. 只输出 `global_recommendation.command` 一行（让用户能 pipe / copy）
3. 若 active_count=0，输出 `/szw-new-article`

### `--do "<text>"` 模式（NL 路由）

1. 跑 `parse-state.py active` 拿全部 active articles
2. **AI 侧**做匹配（脚本不做 NLP）：
   - 用户文字提到的关键词 vs. 各 slug
   - 用户文字描述的动作 vs. 各 status 对应的 next_command
   - 找不到匹配 → 输出 active 表 + 让用户选
3. 输出：匹配到的 article + 推荐命令 + 简短理由（"匹配 slug 'XXX'，因为 your text mentions YYY"）

### `--completed` 模式

1. 跑 `parse-state.py completed`
2. 渲染 Recently Completed 表（4 列：Slug / Completed at / Disposition / Platforms）
3. 提示："要看专栏全量统计 → `/szw-stats`（v3.0）"

---

## 优先级排序（多 article）

`parse-state.py` 已经按 `priority_rank` 元组升序排好。规则：

| 优先级 | 触发 | 理由 |
|---|---|---|
| **1** | `status = review_failed` | HIGH issue 待修，流水线被 gate 卡住 |
| **2** | `status = paused` | 已留 handoff，恢复成本低 |
| **3** | 同优先级内按 `last_touched` 升序（最久未触碰排前） | 避免被忘记 |

JSON 输出的 `global_recommendation.priority_bucket` 取值：
- `review_failed` —— 第一优先级命中
- `paused` —— 第二优先级命中
- `stale` —— 最久未触碰已 ≥ 7 天
- `most_recent` —— 兜底

---

## 错误处理

| 退出码 | 含义 | 应对 |
|---|---|---|
| `0` | 成功 | — |
| `1` | STATE.md 不存在 | 提示 `/szw-init` 初始化 |
| `2` | 指定 slug 不存在 | 提示是否在 Recently Completed；建议 `/szw-progress` 看 active 表 |
| `3` | STATE.md 解析失败 / 表结构损坏 | 跑 `parse-state.py validate` 看具体 issue；从 git 回滚或手动修 |

---

## Gates

- **Pre-flight**：`<cwd>/.zero/STATE.md` 必须存在，否则 exit 1
- **降级**：Active Articles 表为空时仍正常输出（提示起新文章），不视为错误
- **不破坏**：纯只读，不修改任何文件

---

## 完成 marker

无写操作。输出全部为 stdout 报告。

---

## 设计原则

1. **JSON 中间表示**：脚本输出 JSON，AI 渲染 Markdown 表 / 报告。脚本可独立测试，渲染逻辑可演化
2. **优先级单点维护**：排序逻辑在 `parse-state.py priority_rank()`；改规则只改一处
3. **status → next 映射对齐 szw-help**：保持与 [`../szw-help/SKILL.md`](../szw-help/SKILL.md) "下一步推荐规则"一致；改动同步两处
4. **NL 路由 AI 侧**：脚本不做 NLP；AI 拿 active 列表 + 用户文字做语义匹配
5. **降级友好**：缺 STATE.md / 表损坏 / 空表 都给可操作的下一步
6. **不写文件**：纯只读；写 STATE.md 由 `/szw-complete` `/szw-pause` `/szw-new-article` 各自负责

---

## 与其他命令的关系

- `/szw-init` —— 创建 STATE.md 骨架
- `/szw-new-article` —— 给 STATE.md Active 表追加一行
- `/szw-progress` —— 读 STATE.md 渲染（本命令）
- `/szw-resume <slug>` —— 选定一篇深入恢复上下文
- `/szw-complete <slug>` —— 把 article 从 Active 移到 Recently Completed
- 各流水线命令（`/szw-discuss` / `/szw-write` / ...）—— 跑完后更新各自 article 的 ARTICLE.md status 和 STATE.md 行的 last_touched

---

## 输出示例

### 示例 1：3 个 active articles（review_failed 占位）

```
📍 当前位置：3 个 active articles（按优先级排序）

| Slug | Status | Last touched | Next |
|---|---|---|---|
| 2026-05-skills-vs-gsd | ⚠️ review_failed | 0 天前 | /szw-write 2026-05-skills-vs-gsd [section] --mode polish |
| 2026-05-claude-vs-codex | created | 16 天前 ⏰ | /szw-discuss 2026-05-claude-vs-codex |
| 2026-05-agentic-coding | brief_done | 2 天前 | /szw-research 2026-05-agentic-coding |

🎯 全局推荐：先修 review_failed
   → /szw-write 2026-05-skills-vs-gsd [section] --mode polish
   理由：修复 review HIGH issue（最优先级）

提示：/szw-progress <slug> 看单篇详情；/szw-resume <slug> 切上下文
```

### 示例 2：单 article 详情（`/szw-progress 2026-05-skills-vs-gsd`）

```
📍 2026-05-skills-vs-gsd | status=review_failed | last_touched=2026-05-06 (0 天前)

阶段产物：
  ✅ ARTICLE.md           (元数据)
  ✅ 01-brief.md          (历史产物)
  ✅ 04-draft.md          (历史产物)
  ⭐ 05-review.md         (status_required；review 报告)

注：02-research.md / 03-outline.md 缺失 → v1.0 流水线（跳过研究/大纲，直接起稿）

🎯 推荐下一步：/szw-write 2026-05-skills-vs-gsd [section] --mode polish
   理由：修复 review HIGH issue（最优先级）
```

### 示例 3：`--next` 一行输出

```
/szw-write 2026-05-skills-vs-gsd [section] --mode polish
```

### 示例 4：自然语言路由（`--do "继续昨天那篇 agentic"`）

```
🔀 路由匹配：

  你说："继续昨天那篇 agentic"
  匹配 article：2026-05-agentic-coding（slug 含 'agentic'，2 天前触碰）
  当前 status：brief_done

🎯 推荐：/szw-research 2026-05-agentic-coding
   理由：证据采集 + 判断诊断（v2.0）

不对？看完整 active 表：/szw-progress
```

### 示例 5：空 active 表

```
📍 当前位置：无 active article

🎯 推荐：/szw-new-article
   起新文章；或 /szw-progress --completed 看最近发布的。
```

### 示例 6：`--completed` 输出

```
📜 Recently Completed（最近 2 篇）：

| Slug | Completed at | Disposition | Platforms |
|---|---|---|---|
| 2026-04-codex-deep-dive | 2026-04-30 | published | blog, wechat |
| 2026-03-old-draft | 2026-03-15 | archived | - |

提示：/szw-stats 看专栏全量统计（v3.0）
```

---

## 关于自然语言路由（`--do`）的实现要点

AI 侧匹配时按这个优先顺序：

1. **slug 字串包含**：用户文字含 slug 的关键 token（如 "agentic" 命中 `2026-05-agentic-coding`）
2. **status 关键词**：用户提到 "review" / "审稿" → 匹配 `review_failed` 或 `draft_done` 的 article
3. **时间词**：用户说 "上次/昨天" → 取 `last_touched` 最大的
4. **动作词**：用户说 "起稿" → 匹配 `outline_done` 或 `brief_done`（可走 write）

匹配失败的兜底：直接渲染默认表格 + 让用户选。**不要**强行猜，避免把用户路到错的 article。

---

## 不实现的事

- **不修改 STATE.md**：本命令纯只读；写操作由 `/szw-complete` `/szw-pause` 各自负责
- **不读 ARTICLE.md 的 thesis 等内容**：那是 `/szw-resume <slug>` 的职责（context restore）
- **不调用子 agent**：本命令是确定性脚本 + 简单渲染，无需 LLM 加工
- **不缓存**：每次调用都重新解析 STATE.md，避免陈旧
