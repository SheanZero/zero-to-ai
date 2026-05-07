---
name: szw-research
description: Combined evidence collection + claim diagnosis in a Codex-driven workflow. Two-phase (1) gather evidence cards for each supporting claim from the brief, (2) diagnose factual support / safer wording for each claim. Internal HIGH-risk loop returns to Phase 1 for more evidence (max 2 rounds), then escalates. Sediments cross-article evidence to .zero/evidence/<topic>.md. Use after /szw-discuss to harden a brief before /szw-outline.
---

# szw-research

把"证据采集"和"判断诊断"合并到一条 Codex 驱动的命令。AI 主导（强建议路由 Codex）做研究 + 诊断；脚本管 IO + verdict gate + evidence bank 同步。**v2.0 完整路径的关键节点**：把 brief 的 supporting claims 从"主张"硬化成"有证据的、措辞安全的论证基础"。

## 何时使用

- 跑完 `/szw-discuss`，brief 已 commit，准备硬化论证
- 写到一半发现某 claim 不可靠 → 退回这里补证据
- v2.0 完整流水线：discuss → **research** → outline → write → review → publish → complete

## 何时不用

- 01-brief.md 不存在 → 先 `/szw-discuss`
- 文章是 quick post / 个人感悟 → `/szw-quick`（v2.0），跳过 research
- v1.0 简化流程：直接 brief → write 也行（牺牲 evidence 严谨度）
- 想看进度 → `/szw-progress`

---

## 调用语法

| 形式 | 行为 |
|---|---|
| `/szw-research` | 默认：取 STATE.md last_touched 最大且 status=brief_done 的 slug |
| `/szw-research <slug>` | 指定 article |

底层脚本：

```bash
scripts/prepare-research.py [--slug <slug>]                 # Phase 0：上下文 + claim ID
scripts/finalize-research.py commit --slug <slug> < <json>  # Phase 3：落盘 + verdict gate + bank 同步
```

---

## 执行流程（4 phase）

### Phase 0：上下文收集（脚本）

```
prepare-research.py [--slug <slug>]
```

输出 JSON 关键字段：
- `slug` / `current_status` / `type` / `target_platforms`
- `brief` —— 解析后的 01-brief.md（thesis / supporting_claims / counterargument / evidence_needed）
- `claims_with_ids` —— `[{"id": "C1", "text": "..."}]`，按 brief 顺序分配；**Phase 1/2 必须按此 ID 引用**
- `existing_evidence_topics` —— 已有 .zero/evidence/<topic>.md 列表（topic / path / modified / size），供 AI 视相关性 Read 复用
- `editorial_context_path` —— 若 EDITORIAL_CONTEXT.md 有 §10 Evidence Standards 节，AI 可读
- `warnings`

收到 JSON 后：
- Read 01-brief.md 核对解析结果
- Read 相关的 evidence bank 文件（按 topic 名相关性挑选）

### Phase 1：证据采集（AI / Codex）

**强建议路由 Codex**（fan.md §7 概念名 `evidence-researcher`）：Codex 的 web 搜索 + 长上下文检索更适合证据搜集。当前可：
- 主对话直接用 WebSearch / WebFetch
- 或 dispatch `Agent codex:rescue` 让 Codex 跑研究子任务

每条 claim（C1..Cn）产出 `evidence_card`：
- `status`: `covered` / `source_needed` / `weak`
- `sources[]`: `type / title / date / url / quote / confidence`

**复用 evidence bank**：从 `existing_evidence_topics` 选相关 topic，把 source 直接拷到 cards。

**沉淀到 evidence bank**：跨文章可复用的 source 加到 `evidence_bank_writes` 字段（按 topic 分组）。

### Phase 2：判断诊断（AI / Codex）

每条 claim 产出 `claim_diagnosis`：
- `type`: `fact` / `interpretation` / `opinion` / `prediction` / `advice`（决定证据要求强度）
- `evidence_required` vs `evidence_available` —— 是否对得上
- `counter_evidence` —— 反向证据
- `confidence`: `high` / `medium` / `low`
- `risk`: `L` / `M` / `H`
- `safer_rewrite` —— 降低风险的措辞建议

按 type → risk 经验法则：
- `fact` 要求 `confidence=high`，否则 risk≥M
- `prediction` / `advice` 必带 counter_evidence；否则 risk≥M
- `opinion` risk 通常 L（已知是观点）但措辞要标"我认为/在我观察到"

### 内部 HIGH-risk 循环（Phase 2 → Phase 1）

Phase 2 完成后看 `risk='H'` 的 claim：

| 状况 | 行为 |
|---|---|
| 0 个 HIGH-risk | `verdict='passed'` → 直接 commit |
| ≥1 HIGH-risk + `loop_rounds < 2` | 自动回 Phase 1 补该 claim 证据，重跑 Phase 2，`loop_rounds++` |
| ≥1 HIGH-risk + `loop_rounds == 2` | 不再循环；问用户：(a) **accept** HIGH-risk → `verdict='passed_with_high_risk'` + `user_decision='accept'`；(b) **downgrade** thesis → `user_decision='downgrade'` 退回 /szw-discuss；(c) 极端情况 `verdict='needs_rework'` 让 AI escalate |

### Phase 3：commit（脚本）

```bash
cat <<'EOF' | scripts/finalize-research.py commit --slug <slug>
{ ... research json ... }
EOF
```

脚本动作：
- 校验 JSON：top fields / cards / diagnosis / source 字段；`high_risk_claims` 必须等于 diagnosis 中 risk='H' 的集合
- **verdict gate**（见 [`references/research-schema.md`](./references/research-schema.md) "verdict gate" 表）
- 渲染 02-research.md（§1 Evidence Cards / §2 Claim Diagnosis / §3 Recommended Action）
- 改 ARTICLE.md：`status → research_done`，Status Log 加 `research_done via /szw-research`
- 改 STATE.md Active 行：status / last_touched / next = `/szw-outline`
- 同步 evidence bank：每个 `evidence_bank_writes` topic → 创建或追加 `.zero/evidence/<topic>.md`

---

## 失败处理

| 退出码 | 含义 | 应对 |
|---|---|---|
| `0` | 成功 | — |
| `1` | 不在专栏目录 | cd 到容器根 |
| `2` | slug / ARTICLE.md / 01-brief.md 不存在 | 先 `/szw-discuss` 完成 brief |
| `3` | STATE.md 缺失 / 解析失败 | 检查 STATE.md `## Active Articles` 标题 |
| `4` | stdin JSON 缺字段 / 字段值非法 / `high_risk_claims` 与 diagnosis 不一致 | 看错误信息修 JSON |
| `5` | verdict gate 拒绝（详见下表） | 视具体原因 escalate 或回上游 |

### exit 5 verdict gate 详分类

| 错误 | 含义 | 应对 |
|---|---|---|
| `verdict='needs_rework'` | 内部循环用尽仍 HIGH-risk | escalate 用户：(a) 回 `/szw-discuss` 改命题；(b) 手动多跑一轮研究 |
| `verdict='passed' but high_risk 非空` | 自相矛盾 | 让 AI 改 verdict 为 passed_with_high_risk，问用户决定 |
| `verdict='passed_with_high_risk' but high_risk 空` | 自相矛盾 | 改 verdict 为 passed |
| `passed_with_high_risk` + `user_decision=null` | 没问用户 | 把 HIGH-risk claim 列出来问用户 accept / downgrade |
| `passed_with_high_risk` + `user_decision='downgrade'` | 用户选择降级 | 提示用户跑 `/szw-discuss <slug>` 改 brief |

---

## Gates

- **Pre-flight**：01-brief.md 必须存在；status 不强制 brief_done（warning）
- **claim ID 一致性**：cards / diagnosis 的 claim_id 应来自 prepare 给的 C1..Cn 列表（脚本不强制覆盖率，但 high_risk_claims 与 diagnosis 必须严格一致）
- **verdict gate**：见上表
- **状态推进对称**：与 discuss / outline 一致；写 Status Log + STATE.md

---

## 与上下游的紧密集成

### ↑ 与 /szw-discuss 的集成

| 集成点 | 实现 |
|---|---|
| Status precondition | brief_done（最低）；status != brief_done → warning，不阻断 |
| 输入文件 | 01-brief.md（必需） |
| **claim ID 稳定** | prepare-research.py 按 brief.supporting_claims 顺序分配 C1..Cn；与 prepare-outline.py 完全一致 |
| brief 字段消费 | thesis / supporting_claims / evidence_needed / counterargument 全部读入；不修改 brief |
| **HIGH-risk escape** | user_decision='downgrade' → exit 5 提示回 `/szw-discuss` 改 brief |
| target_platforms / alignment_check 不重审 | 假定 brief 已通过 ADR 比对 |

### ↓ 与 /szw-outline 的集成

| 集成点 | 实现 |
|---|---|
| Status promotion | research_done → outline 的优选 prereq（也接受 brief_done） |
| 02-research.md 检测 | szw-outline 自动检测 → mode='brief_plus_research'（v2.0 完整）vs 'brief_only'（v1.0 兜底） |
| evidence_ref 链回 | outline 的 thesis_map.supporting[].evidence_ref 应引用 02-research.md §1 / §2 的 claim ID |
| HIGH-risk 处理 | research 接受了 HIGH-risk + accept → outline 应在该 claim 的 section 用 safer_rewrite |

### ↔ 与 evidence bank 的集成

| 集成点 | 实现 |
|---|---|
| Phase 1 复用 | prepare 列已有 topics；AI 视相关性 Read 来源 |
| Phase 3 沉淀 | evidence_bank_writes 字段 → finalize 自动创建/追加 `.zero/evidence/<topic>.md` |
| backlink | 每条 source 的 "Used in" 行自动写 `<slug> (claim Cn, added date)` |

---

## 完成 marker

```
✅ Committed research for <slug>
   wrote: articles/<slug>/02-research.md
   updated: articles/<slug>/ARTICLE.md (status → research_done)
   updated: STATE.md (Active row → research_done)
   evidence bank: .zero/evidence/<topic>.md (created|appended, N source(s))
   ⚠️  HIGH-risk accepted: C3 (consider safer_rewrite at /szw-write)   # 仅 passed_with_high_risk

👉 Next: /szw-outline <slug>
```

---

## 设计原则

1. **AI 研究 / 脚本落盘**：Codex 跑 evidence + diagnosis 的判断；JSON 校验 + render + state + bank 同步交脚本
2. **claim ID 是稳定接口**：与 prepare-discuss / prepare-outline 共享同一规则
3. **verdict 是硬 gate + 三态**：passed / passed_with_high_risk(+accept) / 其他都拒绝；让用户决策不能被脚本跳过
4. **HIGH-risk 不能糊弄**：自动循环 ≤ 2 轮；2 轮仍 HIGH 必须显式 user_decision，不允许默认通过
5. **evidence bank 自动沉淀**：写一次受益所有后续文章；跨文章复用是复利结构
6. **不修改 brief**：发现问题 escalate 回 discuss，不擅自动手
7. **safer_rewrite 不是装饰**：write 阶段 HIGH-risk claim 应优先用，是 research 留给 write 的 hand-off

---

## 与其他命令的关系

- `/szw-discuss` —— 必备上游：brief 是 input
- `/szw-research`（本命令） —— 证据 + 诊断
- `/szw-outline` —— 直接下游：消费 02-research.md + 01-brief.md，做论证地图 + 拆片
- `/szw-write` —— 间接下游：HIGH-risk claim 用 safer_rewrite
- `/szw-evidence-bank`（v3.0） —— 管理 .zero/evidence/ 目录的清理 / dedup / retire
- Codex 集成：当前用 codex:rescue 或主对话承担；将来可定义 sub-agent

---

## 输出示例

### 示例 1：happy path（无 HIGH-risk）

```
[内部] prepare-research.py → slug=2026-05-foo, claims=C1/C2/C3, existing topics=[]

📍 准备研究 2026-05-foo（industry-analysis）
   读 01-brief.md（thesis + 3 claims + evidence_needed）
   读 EDITORIAL_CONTEXT.md §3 Principles

[Phase 1 - Codex] 证据采集：
  C1 → 2 sources (Anthropic 官方 high + mattpocock blog medium) → covered
  C2 → 1 source (GSD 官方 high) → covered
  C3 → 1 source (HN thread low) → weak

[Phase 2 - Codex] 诊断：
  C1: type=interpretation, risk=L, safer_rewrite=...
  C2: type=interpretation, risk=L, safer_rewrite=...
  C3: type=fact, risk=H ⚠️ (90% 数字无代表性证据)

high_risk=[C3], loop_rounds=0
[内部循环 1] 回 Phase 1 找 C3 更多证据... 找不到代表性数据
[内部循环 2] 仍 HIGH-risk

⚠️ C3 经过 2 轮内部循环仍 HIGH-risk。

  C3 原文："写作场景 90% 痛点是单人短反馈循环"
  风险：仅一个 HN 帖子（非代表性），90% 这个具体数字无法独立验证

  Safer rewrite: "在我观察到的写作场景中，多数痛点出现在单人短反馈循环；
                  90% 这个数字未经独立验证。"

请决定：
  1. accept HIGH-risk + 起稿用 safer_rewrite（thesis 不依赖精确数字时合理）
  2. downgrade → 回 /szw-discuss 改 brief（删 C3 或换措辞）

> 1

[finalize] commit with verdict=passed_with_high_risk, user_decision=accept
✅ Committed research for 2026-05-foo
   wrote: articles/2026-05-foo/02-research.md
   updated: ARTICLE.md (status → research_done)
   updated: STATE.md (Active → research_done, next: /szw-outline)
   evidence bank: .zero/evidence/claude-code-skills.md (created, 2 sources)
   ⚠️  HIGW-risk accepted: C3 (consider safer_rewrite at /szw-write)

👉 Next: /szw-outline 2026-05-foo
```

### 示例 2：选 downgrade → 回 discuss

```
[同上 Phase 1/2/loop]

请决定：accept / downgrade?

> 2

[finalize commit with verdict=passed_with_high_risk, user_decision=downgrade]
ERROR: verdict='passed_with_high_risk', user_decision='downgrade'.
HIGH-risk claims: ['C3']. Action: AI should advise user to run /szw-discuss <slug>
to revise brief (soften thesis or drop the high-risk claims).
exit=5

👉 Next: /szw-discuss 2026-05-foo（修 brief，删 C3 或换措辞）
```

### 示例 3：所有 claim covered + 无 HIGH-risk

```
[Phase 1 + 2 顺利]
all claims: covered/risk=L
verdict=passed, user_decision=null, evidence_bank_writes=[3 topics]

✅ Committed research for ...
   evidence bank: 3 files synced
👉 Next: /szw-outline ...
```

---

## 不实现的事

- **不修改 brief**：发现问题 escalate；不擅自改 01-brief.md
- **不写 outline / draft**：上下游各司其职
- **不调用 specific Codex sub-agent**：fan.md §7 的 evidence-researcher / claim-diagnoser 是概念名；当前用 codex:rescue 或主对话
- **不做 evidence bank 去重**：写多份是数据；清理交 `/szw-evidence-bank`（v3.0）
- **不重审 ADR alignment**：discuss 已做
- **不强制 source 数量**：可以 0 source（status=source_needed）；diagnosis 仍可基于 evidence_required vs available 给 risk
- **不 git commit**：用户决定何时入版本
