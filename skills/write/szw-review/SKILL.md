---
name: szw-review
description: Two-phase review (1) skeptical reviewer (Codex-driven) for fact / counterargument / boundary issues with H/M/L severity, (2) style capture by diffing 04-draft.md vs latest writing-history snapshot to learn author edits and accumulate to .zero/style-profile.md. Phase 1 has internal loop ≤ 2 rounds; HIGH issues → review_failed → polish loop. Phase 2 auto-skip when diff < threshold (config). Use after /szw-write to validate draft + extract style; downstream of style-profile becomes /szw-write Phase 1 input on next call.
---

# szw-review

合并"反方审稿"和"风格捕获"。AI（Phase 1 强建议路由 Codex 跨 AI 评审）+ 脚本管 IO + verdict gate + style-profile 累积。**v2.0 风格学习闭环的关键节点**：每次 review 都让 .zero/style-profile.md 更懂作者，下次 write 起稿就更像作者。

## 何时使用

- 跑完 `/szw-write` 出新 04-draft.md，准备评审
- 起完稿想做风格档案累积（哪怕 Phase 1 都过）
- review_failed 修复后回头再审
- v2.0 流水线：discuss → research → outline → write → **review** → publish → complete

## 何时不用

- 04-draft.md 不存在 → 先 `/szw-write`
- 想看进度 → `/szw-progress`
- 想发布 → `/szw-publish`

---

## 调用语法

| 形式 | 行为 |
|---|---|
| `/szw-review` | 默认：取 STATE.md 最新 draft_done / review_failed / review_passed slug |
| `/szw-review <slug>` | 指定 article |

底层脚本：

```bash
scripts/prepare-review.py [--slug <slug>]                    # Phase 0：上下文 + diff 计算
scripts/finalize-review.py commit --slug <slug> < <json>     # Phase 3：落盘 + verdict gate + style-profile append
```

---

## 执行流程（4 phase）

### Phase 0：上下文收集（脚本）

```
prepare-review.py [--slug <slug>]
```

输出 JSON 关键字段：
- `slug` / `current_status` / `type` / `target_platforms`
- `article_md_path` / `draft_md_path` / `brief_md_path` / `outline_md_path` / `research_md_path`
- `long_term_assets`：editorial_context / style_profile（可能 null）/ adrs / glossary
- `phase2_context`：
  - `config`：style_capture 配置（enabled / diff_threshold_pct / merge_after_n_reviews / min_pattern_frequency）
  - `latest_snapshot`：最近一份 writing-history 文件元信息
  - `diff_pct`：04-draft.md vs snapshot 的变更比例（百分比）
  - `should_skip`：Phase 2 是否建议跳过
  - `skip_reason`：skip 理由（diff < threshold / no snapshot / config disabled）
- `warnings`

收到 JSON 后：
- **必读** 04-draft.md / 01-brief.md
- **必读** EDITORIAL_CONTEXT.md（§3 Principles + §5 Topic Boundaries + §7 Style Guide）
- 02-research.md（如有）→ 边界审 / fact 审对照
- 03-outline.md（如有）→ acceptance_criteria 检查
- 相关 ADR
- style-profile.md（如已存在）→ 看作者偏好；Phase 1 也可参考避免重复学

### Phase 1：Skeptical Review（强建议 Codex）

**强建议**：dispatch `Agent codex:rescue` 让 Codex 做独立评审（跨 AI 反审更客观）；或主对话承担。

**3 类审 + H/M/L 分级**：
1. **技术审 (`fact` / `claim`)**：术语 / 数字 / 引用 / 论证可靠性
2. **反方审 (`counterargument`)**：最强反驳是什么；文章有没有回应
3. **边界审 (`boundary`)**：是否越过 EDITORIAL_CONTEXT.md §5 topic boundaries；是否违反 ADR
4. （可选 `style`）：明显的 banned patterns / 节奏问题

每个 issue 输出：`{id, severity, category, location, description, evidence, suggestion}`。

**内部循环（≤ 2 轮）**：第一轮列 issues 后，AI 按建议对照 brief / research，看是否有自己疏漏的反方/证据；第二轮再列；之后定稿。

### Phase 2：Style Capture

**先看 prepare 输出 `phase2_context.should_skip`**：
- `true` → 整个 Phase 2 跳过；输出 `phase2.skipped=true` + skip_reason
- `false` → 执行

**执行步骤**：
1. Read writing-history 最近 snapshot（path 在 prepare 给的 `latest_snapshot.filename`）
2. 用 difflib 或人工对比 snapshot vs 04-draft.md
3. 提取 5 类风格特征：
   - **vocabulary_substitutions**：AI 用 X，作者改 Y（带频次 + 示例）
   - **sentence_patterns**：作者偏好的句式（如"不是 X 而是 Y"）
   - **rhythm_paragraph**：节奏 / 段落特征
   - **punctuation_mixing**：标点 / 中英混用偏好
   - **anti_patterns**：作者反复删除的词（最高优先级，下次 write 必避）
4. 不必每次都填满 5 类；空数组允许（脚本仅追加非空部分）

### Phase 3：commit（脚本）

```bash
cat <<'EOF' | scripts/finalize-review.py commit --slug <slug>
{
  "phase1": {
    "loop_rounds": 1,
    "issues": [...],
    "summary": "..."
  },
  "phase2": {
    "skipped": false,
    "diff_pct": 12.5,
    "snapshot_compared": "...",
    "features": {...}
  },
  "verdict": "review_passed",
  "notes": "..."
}
EOF
```

脚本动作：
- JSON 校验 + verdict gate（HIGH 存在 + verdict=passed → exit 5）
- 渲染 05-review.md（§1 Phase 1 issues by severity / §2 Phase 2 features 或 skip 标记 / §3 Notes）
- 改 ARTICLE.md：status → review_passed | review_failed；Status Log 追加
- 改 STATE.md Active 行：
  - review_passed → next: `/szw-publish <slug>`
  - review_failed → next: `/szw-write <slug> S<n> --mode polish`（自动从 first HIGH issue 的 location 提取 S\<n\>）
- style-profile.md 累积（仅 Phase 2 not skipped 且 features 非全空）：
  - 不存在 → 创建（带 H1 + meta + 4 段框架）
  - 存在 → meta blockquote 更新（Last updated + sample size 累加）+ Recent Edits 表末尾追加新行

---

## 失败处理

| 退出码 | 含义 | 应对 |
|---|---|---|
| `0` | 成功 | — |
| `1` | 不在专栏目录 | cd 到容器根 |
| `2` | slug / ARTICLE.md / 04-draft.md 不存在 | 先 `/szw-write` 出 draft |
| `3` | STATE.md 缺失 / row 找不到 | 检查 STATE.md 表结构 |
| `4` | stdin JSON 缺字段 / 字段值非法 | 看错误信息修；参考 [`references/review-schema.md`](./references/review-schema.md) |
| `5` | verdict gate：HIGH 存在但 verdict=review_passed | 二选一：(a) verdict 改 review_failed；(b) 把 HIGH issues 降级到 MEDIUM/LOW 并说明理由 |

---

## Gates

- **Pre-flight**：04-draft.md 必须存在；status 不强制（warning）
- **verdict gate**：HIGH 与 review_passed 不能共存
- **review_failed 允许无 HIGH**：用户可基于 MEDIUM 决定 fail（用判断，脚本不强制）
- **Phase 2 skip 智能**：基于 diff_pct vs config threshold；可被 AI override（提交 `skipped: false` 即可）

---

## 与上下游的紧密集成

### ↑ 与 /szw-write 的集成

| 集成点 | 实现 |
|---|---|
| Status precondition | draft_done（最优）/ review_failed（loop）/ review_passed（重审） |
| 输入文件 | 04-draft.md（必需） |
| **风格闭环关键** | Phase 2 用 `.zero/writing-history/<slug>/` 最近 snapshot 与 04-draft.md 做 diff，反推作者改了什么 |
| diff threshold | `style_capture.diff_threshold_pct`（默认 5%）；diff 不显著直接跳 Phase 2 |
| section 定位 | issue.location 含 S\<n\> → review_failed 时 next_action 自动指向 `/szw-write <slug> S<n> --mode polish` |

### ↑ 与 /szw-research 的集成

| 集成点 | 实现 |
|---|---|
| HIGH-risk safer_rewrite 检查 | Phase 1 fact 审参照 02-research.md §3：起稿是否用了 safer_rewrite |
| evidence 对照 | issue 的 evidence 字段可引用 02-research.md §1 evidence cards |

### ↑ 与 /szw-discuss / /szw-outline 的集成

| 集成点 | 实现 |
|---|---|
| thesis 对照 | Phase 1 看 04-draft.md 是否兑现 brief.thesis |
| acceptance_criteria 检查 | 03-outline.md §2 每节的 ACx；Phase 1 逐 section 自检 |
| boundary 审 | EDITORIAL_CONTEXT §5 topic_boundaries + ADR 列表（discuss 时已对齐；review 重审防止起稿越界） |

### ↓ 与 /szw-write 的集成（review_failed 循环）

| 集成点 | 实现 |
|---|---|
| review_failed → polish | next_action 自动定位 `S<n>`（提取自第一 HIGH issue location）|
| style-profile.md 反向喂 | 累积到 .zero/style-profile.md → 下次 /szw-write Phase 0 prepare 输出 long_term_assets.style_profile → AI 必读 |

### ↓ 与 /szw-publish 的集成

| 集成点 | 实现 |
|---|---|
| review_passed → publish | next_action = `/szw-publish <slug>` |
| 04-draft.md 是 publish 输入 | publish 按节标记切平台版本 |

### ↔ 与 .zero/style-profile.md 的集成

| 集成点 | 实现 |
|---|---|
| 写入 | finalize append（Recent Edits 表）+ meta 累计（articles + edit instances） |
| 读取 | /szw-write Phase 1 必读；review 自身的 Phase 1 也可参考（避免重复学） |
| 自动合并（v3.0） | `style_capture.merge_after_n_reviews` 阈值后把 Recent → Stable；当前不实现 |

---

## 完成 marker

```
✅ Committed review for <slug>
   verdict: review_passed | review_failed
   wrote: articles/<slug>/05-review.md
   issues: HIGH=N, MEDIUM=N, LOW=N
   updated: articles/<slug>/ARTICLE.md (status → <verdict>)
   updated: STATE.md (next: <next_action>)
   .zero/style-profile.md (created|appended, N edit row(s))     # 仅 Phase 2 非跳过且 features 非空
   Phase 2 skipped: <reason>                                       # 仅 Phase 2 跳过

👉 Next: /szw-publish <slug>           # 或 /szw-write <slug> S<n> --mode polish
```

---

## 设计原则

1. **AI 评审 / 脚本落盘 + 累积**：Phase 1 判断由 AI（Codex）；JSON 校验 + render + state + style-profile append 交脚本
2. **verdict gate 反虚假 passed**：HIGH 与 passed 不能共存；保持质量门
3. **Phase 2 自动跳过避免噪声**：diff < threshold 不学；用户微改不算"风格"
4. **风格闭环是复利**：每次 review 都让 style-profile.md 更厚；下次 write 更像作者
5. **next_action 智能**：location 含 S\<n\> 自动定位 polish 目标，让 review_failed 循环零摩擦
6. **不自动跑 polish**：commit 后只提示，让用户决定何时 polish
7. **不调用 sub-agent**：fan.md §7 的 skeptical-reviewer / style-extractor 是概念名；当前主对话 + codex:rescue 承担

---

## 与其他命令的关系

- `/szw-write` —— 上游：04-draft.md 是 input；writing-history snapshot 是 Phase 2 baseline
- `/szw-research`（v2.0） —— 上游可选：HIGH-risk safer_rewrite 是 Phase 1 fact 审参照
- `/szw-outline`（v2.0） —— 上游可选：acceptance_criteria 是 Phase 1 检查清单
- `/szw-discuss` —— 上游：brief 的 thesis / out_of_scope / counterargument 是 Phase 1 边界基线
- `/szw-review`（本命令） —— skeptical review + style capture
- `/szw-write`（review_failed 循环） —— 下游：polish 后回头再 review
- `/szw-publish` —— 下游（review_passed 路径）：04-draft.md 打包成多平台
- `.zero/style-profile.md` —— 横向资产：被本命令写、被 /szw-write 读

---

## 输出示例

### 示例 1：Phase 1 全过 + Phase 2 学到风格

```
[内部] prepare-review.py → diff_pct=22%, should_skip=false (>3%)

📍 准备评审 2026-05-foo（industry-analysis）
   读 04-draft.md / 01-brief.md / 02-research.md / 03-outline.md
   读 EDITORIAL_CONTEXT §3/§5/§7
   ⚠️ style-profile.md 不存在（首次 review，本次 Phase 2 将创建）

[Phase 1 - Codex] 反方审：
  - 技术审：所有数字 + 引用 ✓
  - 反方审：counter 已回应 ✓
  - 边界审：未越界 ✓
  HIGH=0, MEDIUM=1（claim 措辞模糊）, LOW=1（开头略突兀）

[Phase 2] Style capture：
  diff vs snapshot 01-both-full-..md = 22%
  vocab: 或许→deleted x1, 工程师→程序员 x2, 随着→deleted x1
  sentence: 短句直接陈述
  anti_patterns: 在某种程度上

[finalize commit]
✅ Committed review for 2026-05-foo
   verdict: review_passed
   wrote: articles/2026-05-foo/05-review.md
   issues: HIGH=0, MEDIUM=1, LOW=1
   updated: ARTICLE.md (status → review_passed)
   updated: STATE.md (next: /szw-publish 2026-05-foo)
   .zero/style-profile.md (created, 6 edit row(s))

👉 Next: /szw-publish 2026-05-foo
```

### 示例 2：HIGH issue → review_failed → 自动定位 polish

```
[Phase 1] HIGH=1 (S2 §3 fact 错误：90% 数字无证据)
[Phase 2] skip (diff < 3%)

[finalize commit verdict=review_failed]
✅ Committed review for 2026-05-foo
   verdict: review_failed
   wrote: articles/2026-05-foo/05-review.md
   issues: HIGH=1, MEDIUM=0, LOW=0
   updated: ARTICLE.md (status → review_failed)
   updated: STATE.md (next: /szw-write 2026-05-foo S2 --mode polish)
   Phase 2 skipped: diff_pct=2.1% < threshold=3% (no significant author edits since last AI snapshot)

👉 Next: /szw-write 2026-05-foo S2 --mode polish
```

### 示例 3：HIGH 存在但 AI 说 passed → 拒绝

```
[Phase 1] HIGH=1
[finalize commit verdict=review_passed]   ← AI 错了

ERROR: verdict='review_passed' but 1 HIGH issue(s) present: ['H1']. Self-contradictory.
Set verdict='review_failed' (and address via /szw-write polish), or downgrade those issues
to MEDIUM/LOW with justification.
exit=5
```

### 示例 4：第二次 review，append style-profile

```
[内部] prepare → style_profile_path 已存在
[Phase 1] no issues
[Phase 2] 学到 1 个新 vocab + 1 个 anti-pattern

[finalize] ✅ verdict=review_passed
   .zero/style-profile.md (appended, 2 edit row(s))
   meta updated: 2 articles, 8 edit instances
```

---

## 不实现的事

- **不自动跑 polish**：commit 后只提示，用户决定
- **不修改 brief / research / outline**：只读上游产物；发现需要改回 escalate
- **不调用 sub-agent**：fan.md §7 的概念名；当前主对话 + codex:rescue 承担
- **不自动合并 Recent Edits → Stable Patterns**：v3.0 deferred；当前仅 append
- **不去重 article 贡献数**：同 slug 多次 review 累计算多次贡献（便于估稳定度）；audit 时手工去重
- **不强制 Phase 2 features 非空**：可以只学 anti_patterns 一类；空全跳（不污染 style-profile）
- **不 git commit**：用户决定何时入版本
