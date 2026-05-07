---
name: szw-outline
description: Two-phase outlining for an article — (1) build thesis map from brief and research, (2) slice into 4-6 vertical section outlines with acceptance criteria. Internal loop returns from Phase 2 to Phase 1 if a supporting claim can't carry an independent section. Use after /szw-research (v2.0 path) or directly after /szw-discuss (v1.0 path; works without research, with weaker evidence anchoring).
---

# szw-outline

把"论证地图"和"章节拆片"合并。AI 主导论证设计；脚本管 IO + 状态推进。**承上启下**：消费 01-brief.md（必需）+ 02-research.md（可选），产出 03-outline.md 给 `/szw-write` 起稿。

## 何时使用

- 跑完 `/szw-research`，准备从证据 → 论证结构（v2.0 路径）
- 跑完 `/szw-discuss`，想直接拆论证（v1.0 路径，跳过 research）
- 起稿前发现论证不清，回 outline 重整

## 何时不用

- 01-brief.md 不存在 → 先 `/szw-discuss`
- ARTICLE.md 不存在 → 先 `/szw-new-article`
- 想看流程现状 → `/szw-progress`

---

## 调用语法

| 形式 | 行为 |
|---|---|
| `/szw-outline` | 默认：取 STATE.md last_touched 最大且 status ∈ {research_done, brief_done} 的 slug（research_done 优先） |
| `/szw-outline <slug>` | 指定 article |

底层脚本：

```bash
scripts/prepare-outline.py [--slug <slug>]              # Phase 0：上下文
scripts/finalize-outline.py commit --slug <slug> < <json>  # Phase 3：落盘 + 推进
```

---

## 执行流程（4 phase）

### Phase 0：上下文收集（脚本）

```
prepare-outline.py [--slug <slug>]
```

输出 JSON 关键字段：
- `slug` / `current_status` / `type` / `target_platforms`
- `brief` —— 解析后的 01-brief.md（thesis / supporting_claims / counterargument / evidence_needed / out_of_scope）
- `claims_with_ids` —— `[{"id": "C1", "text": "..."}]`，按 brief 顺序分配；**outline 阶段必须按此 ID 引用**
- `research_md` —— 02-research.md 元数据（path / size / mtime）；不存在为 null
- `mode` —— `brief_plus_research`（02-research.md 存在）/ `brief_only`（缺失）
- `warnings` —— 例如"02-research.md missing → brief_only"

收到 JSON 后：
- 视 `mode` 决定是否 Read 02-research.md（brief_plus_research 必读）
- 必读 01-brief.md（核对 prepare 解析与原文一致）
- 视论证需要按需 Read 02-research.md 的 §2 Claim Diagnosis 章节

### Phase 1：thesis_map（论证地图）

AI 主导（参考 [`references/section-slice-pattern.md`](./references/section-slice-pattern.md) "拆片质检自查"）。具体：

1. **main_thesis 一句话锁定**
   - 继承 brief.thesis 的核心立场；可微调措辞，不变立场
   - 如果想换 thesis 立场 → escalate：建议回 `/szw-discuss` 改 brief
2. **3-5 supporting** —— 每条按 claim_id 引用 brief
   - `evidence_ref` 字段链回 02-research.md（v2.0）或 brief.evidence_needed（v1.0，标"待验证"）
   - `argument_link` 字段写"如何用此 claim 推到 thesis"
3. **1-2 counter** —— 来自 brief.counterargument，可以新加；每条配 response
4. **argument_chain_ok 自检** —— 三 supporting 是否合力推 thesis；不通过 → 找弱链回上游

### Phase 2：section_slices（章节拆片）

参考 [`references/section-slice-pattern.md`](./references/section-slice-pattern.md) 的 4 条规则 + 7 字段：

每节产出：`title / core_claim / evidence_needed / reader_payoff / programmer_implication / counterargument / acceptance_criteria`

**强约束**：
- 4-6 节最佳；接受 3-8（脚本 WARN 不阻断）
- 每节 acceptance_criteria 必须是非空 list；建议 2-4 条可验证
- core_claim 必须引用 prepare 给的 claim_id（C1 / C1+C2）；禁止凭空造 claim

### 内部循环（Phase 2 → Phase 1）

弱 section 触发循环：
- **Round 1**：Phase 2 发现某节撑不起（reader payoff 弱 / claim 不够锐 / 不可独立成立）→ 自动回 Phase 1 调整 supporting（合并 / 降级 / 加新）
- **Round 2**：第二轮仍弱 → 不再循环；`verdict = "weak_section_unresolved"` + `weak_section_notes` 写明
- 把每次循环的决策写到 `decision_log` 数组

### Phase 3：commit（脚本）

```bash
cat <<'EOF' | scripts/finalize-outline.py commit --slug <slug>
{ ... outline json ... }
EOF
```

脚本动作：
- 校验 JSON：top fields / thesis_map.* / section_slices[*].* 完整
- **verdict gate**：`verdict != "passed"` → exit 5（拒绝 commit；AI 必须 escalate）
- mode 自动判定：检 02-research.md 是否存在
- 渲染 03-outline.md（§1 Thesis Map / §2 Section Slices / §3 Decision Log）
- 改 ARTICLE.md：frontmatter `status → outline_done`，Status Log 追加 `outline_done via /szw-outline`
- 改 STATE.md Active 行：status / last_touched / next = `/szw-write`

---

## 失败处理

| 退出码 | 含义 | 应对 |
|---|---|---|
| `0` | 成功 | — |
| `1` | 不在专栏目录 | cd 到容器根 |
| `2` | slug / ARTICLE.md / 01-brief.md 不存在 | 先 `/szw-discuss` 完成 brief |
| `3` | STATE.md 缺失 / 解析失败 | `/szw-init` 修；或检查 STATE.md `## Active Articles` 标题 |
| `4` | stdin JSON 缺字段 / 解析失败 | 看错误信息，参考 outline-schema.md 补字段 |
| `5` | verdict != 'passed'（弱 section 第二轮仍未通过） | 二选一：(a) 回 `/szw-research` 补证据；(b) 回 `/szw-discuss` 改命题 |

---

## Gates

- **Pre-flight**：01-brief.md 必须存在；02-research.md 可选
- **claim ID 一致性**：thesis_map.supporting[].claim_id 必须来自 prepare-outline.py 给的列表
- **section count 软约束**：< 3 或 > 8 → stderr WARN（不阻断）
- **acceptance_criteria 必填**：每节非空 list
- **verdict gate**：weak_section_unresolved → exit 5
- **status 无强约束**：status != brief_done / research_done 也允许（warning）；重跑 outline_done 会覆盖

---

## 与上下游的紧密集成

### ↑ 与 /szw-discuss 的集成

| 集成点 | 实现 |
|---|---|
| Status precondition | brief_done（最低）或 research_done（推荐） |
| 输入文件 | 01-brief.md（必需） |
| **claim ID 稳定** | prepare-outline.py 按 brief.supporting_claims 顺序分配 C1..Cn；与 prepare-research.py 完全一致 |
| thesis 继承 | thesis_map.main_thesis 应继承 brief.thesis；改立场 → escalate 回 discuss |
| target_platforms 继承 | 不重问；用 brief 的值 |
| alignment_check 不重审 | 假定 brief 已通过 ADR 比对 |
| escape | verdict 失败 → 提示回 `/szw-discuss` 改命题 |

### ↑ 与 /szw-research 的集成（v2.0）

| 集成点 | 实现 |
|---|---|
| 02-research.md 检测 | prepare 输出 `mode='brief_plus_research'` 或 `'brief_only'`；finalize 同步 |
| evidence_ref 链回 | thesis_map.supporting[].evidence_ref 应引用 02-research.md §1 / §2 的具体 claim ID |
| HIGH-risk claim 处理 | 若 02-research.md 有 HIGH-risk 未消，outline 不应基于该 claim 拆 section；触发循环或 escalate |
| escape | verdict 失败 → 提示回 `/szw-research` 补证据 |

### ↓ 与 /szw-write 的集成

| 集成点 | 实现 |
|---|---|
| Status promotion | outline_done → write 的 prereq |
| 03-outline.md 消费 | szw-write 按 §2 section_slices 顺序起稿；每节核对 acceptance_criteria |
| target_platforms 继承 | szw-write 不重问 |

---

## 完成 marker

```
✅ Committed outline for <slug>
   wrote: articles/<slug>/03-outline.md
   updated: articles/<slug>/ARTICLE.md (status → outline_done)
   updated: STATE.md (Active row → outline_done)
   mode: brief_plus_research | brief_only · slices: <n> · loops: <0|1|2>

👉 Next: /szw-write <slug>
```

---

## 设计原则

1. **AI 论证 / 脚本落盘**：thesis 设计 + section 切分由 AI 判断；JSON 校验 + markdown 渲染 + 状态推进交脚本
2. **claim ID 是稳定接口**：prepare-{discuss,research,outline} 共享同一规则，让上下游产物可链回
3. **mode 双路径**：brief_plus_research（v2.0 完整）/ brief_only（v1.0 兜底）；header 标注让读者知道证据强度
4. **verdict 是硬 gate**：弱 section 不允许糊弄过关，强制 escalate
5. **decision_log 留痕**：内部循环的调整全部入 §3，便于 retro / audit
6. **target_platforms 单一真相**：在 brief 阶段定，outline 不重问；如要改请改 brief 然后重跑

---

## 与其他命令的关系

- `/szw-discuss` —— 上游：brief 必备
- `/szw-research`（v2.0） —— 上游可选：有它则 mode=brief_plus_research，evidence 锚点完整
- `/szw-outline`（本命令）—— 论证地图 + 章节拆片
- `/szw-write` —— 下游：按 03-outline.md §2 section_slices 起稿
- `/szw-review` —— 下游间接：reviewer 会对照 acceptance_criteria self-test 节是否过关

---

## 输出示例

### 示例 1：v2.0 完整路径（research 已完成）

```
[内部] prepare-outline.py → mode=brief_plus_research, claims=C1/C2/C3, research_md exists

📍 准备拆 outline：2026-05-skills-vs-gsd（industry-analysis）
   读 01-brief.md（thesis + 3 claims）+ 02-research.md（diagnosis: 1 HIGH→ accepted, 2 medium）

[Phase 1] 论证地图：
  Thesis: skills 比 GSD 更吃 ROI（继承 brief，措辞微调）
  Supporting: C1（HIGH-risk: accepted with safer rewrite）/ C2 / C3
  Counter: 1 条 + 回应
  Argument chain: ✅ 通过

[Phase 2] 拆片：4 节
  §1 流水线越完整反而越拖累 → C3
  §2 Skills 复利模型 → C1
  §3 GSD 真正定位 → C2
  §4 5 个决策标准 → C1+C2+C3

每节自查 acceptance_criteria 可验证 ✅
verdict=passed, loops=0

[落盘]
✅ Committed outline for 2026-05-skills-vs-gsd
   wrote: articles/2026-05-skills-vs-gsd/03-outline.md
   updated: ARTICLE.md (status → outline_done)
   updated: STATE.md
   mode: brief_plus_research · slices: 4 · loops: 0

👉 Next: /szw-write 2026-05-skills-vs-gsd
```

### 示例 2：v1.0 兜底路径（research 未做，brief_only）

```
[内部] prepare-outline.py → mode=brief_only, warning: 02-research.md missing

⚠️ 02-research.md 缺失。本次 outline 基于 brief.evidence_needed（计划而非已验证）。
   想要 v2.0 严谨度先跑 /szw-research。
   是否继续？

> 继续

[Phase 1/2 略，与示例 1 类似]

✅ Committed outline for ...
   mode: brief_only · slices: 4 · loops: 0
   ⚠️ 03-outline.md 头部标注"evidence 未独立验证"
```

### 示例 3：内部循环 + escalate

```
[Phase 1 第一轮] 给 thesis_map
[Phase 2 第一轮] 拆 5 节 → §3 撑不起独立一节（reader_payoff 弱）
[Phase 1 第二轮] 把 §3 的 C2 合并到 C1（降级 supporting）
[Phase 2 第二轮] 重拆 4 节 → §2 仍承载过重 + 论证链不通

⚠️ 内部循环已 2 轮仍未通过。
   弱点：C2 不足以独立支撑论证；建议二选一：
   1. /szw-research → 找更强证据让 C2 立得住
   2. /szw-discuss → 重审 brief，删 C2 或换 supporting

> 1

[finalize-outline.py commit 带 verdict=weak_section_unresolved]
ERROR: verdict='weak_section_unresolved' (not 'passed'). Outline rejected.
  notes: §2 承载过重；C2 在 brief_only 模式下证据不足
  Action: AI should ask user to escalate — back to /szw-research or /szw-discuss.
```

---

## 不实现的事

- **不修改 brief / research**：发现上游需要改 → escalate，不擅自动手
- **不调用子 agent**：thesis-mapper / section-planner 是 sub-agent 概念名（fan.md §7）；当前主对话直接担责
- **不写 04-draft.md**：起稿是 `/szw-write` 的事
- **不重审 ADR alignment**：discuss 阶段已做；outline 不重复
- **不 git commit**：用户决定
- **不自动跑 /szw-write**：commit 后只提示，让用户控制起稿时机
