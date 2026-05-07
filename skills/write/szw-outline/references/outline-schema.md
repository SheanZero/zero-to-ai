# 03-outline.md Schema

> `/szw-outline commit` 通过 stdin 接收的 JSON 字段契约 + 渲染到 `articles/<slug>/03-outline.md` 的结构。
> 修改本文档须同步更新 `scripts/finalize-outline.py` 的 `REQUIRED_*_FIELDS` 和 `render_outline_md()`。

---

## stdin JSON top fields

| 字段 | 类型 | 必需 | 说明 |
|---|---|---|---|
| `thesis_map` | dict | ✅ | Phase 1 产物（论证地图） |
| `section_slices` | list[Slice] | ✅ | Phase 2 产物（章节拆片）；非空 |
| `decision_log` | list[Decision] | ✅ | 内部循环间的决策记录；可空数组 |
| `loop_rounds` | int | ✅ | Phase 1↔Phase 2 内部循环次数（0/1/2） |
| `verdict` | enum | ✅ | `passed` / `weak_section_unresolved` |
| `weak_section_notes` | str | ⛔ | verdict != passed 时建议给说明 |

### `thesis_map` 字段

| 子字段 | 类型 | 必需 | 说明 |
|---|---|---|---|
| `main_thesis` | str | ✅ | 一句话核心命题（继承自 brief.thesis；Phase 1 可微调措辞，但不变核心立场） |
| `supporting` | list[Supporting] | ✅ | 3-5 条；非空 |
| `counter` | list[Counter] | ✅ | 1-2 条；可空数组（不推荐） |
| `argument_chain_ok` | bool | ✅ | Phase 1 自检：3 条 supporting 是否合力推出 thesis |
| `argument_chain_notes` | str | ⛔ | 自检说明 |

#### `Supporting` 项

```json
{
  "claim_id": "C1",          // 必须与 prepare-outline.py 分配的 claim ID 对应
  "claim_text": "...",
  "evidence_ref": "02-research.md §1 / 01-brief.md.evidence_needed (待验证)",
  "argument_link": "如何用此 claim 推到 thesis"
}
```

#### `Counter` 项

```json
{
  "text": "强读者反方观点",
  "response": "如何回应"
}
```

### `Slice` 项（section_slices 元素）

| 字段 | 类型 | 必需 | 说明 |
|---|---|---|---|
| `n` | int | ✅ | 节序号（1, 2, 3, ...） |
| `title` | str | ✅ | 章节标题 |
| `core_claim` | str | ✅ | 引用 claim ID（"C1" 或 "C1 + C2"） |
| `evidence_needed` | str | ✅ | 此节需要的证据（链回 02-research.md） |
| `reader_payoff` | str | ✅ | 读完此节读者获得什么 |
| `programmer_implication` | str | ✅ | 程序员可执行行动 |
| `counterargument` | str | ✅ | 反方观点 + 回应（节内自含，与 thesis_map.counter 不同层级） |
| `acceptance_criteria` | list[str] | ✅ | 写完此节的完成标准（非空数组；2-4 条） |

### `Decision` 项（decision_log 元素）

```json
{
  "round": 1,
  "phase": "thesis_map" | "section_slices",
  "decision": "做了什么调整",
  "reason": "为什么"
}
```

---

## verdict gate

| verdict | 行为 |
|---|---|
| `passed` | commit 通过，渲染 03-outline.md，推进 status=outline_done |
| `weak_section_unresolved` | commit 拒绝（exit 5）；AI 应提示用户回 `/szw-research` 补证据或 `/szw-discuss` 改命题 |

`loop_rounds` 已经满 2 仍 weak → AI 必须 escalate；不能强行 commit。

---

## section count 软约束

- 推荐：4-6 节强 section
- 接受：3-8 节
- 警告：< 3 或 > 8 → stderr WARN（不阻断 commit）

---

## 渲染输出（03-outline.md）

```
# 03-outline — <slug>

> 由 /szw-outline 在 <date> 产出。
> 模式：基于 01-brief.md + 02-research.md（v2.0 完整路径）
>   或：⚠️ 基于 01-brief.md only（02-research.md 缺失；evidence 未独立验证）
> 内部循环：<n> 轮 · 结论：<verdict>

## §1 Thesis Map
### Main Thesis
### Supporting
#### S1 · C1
- Claim / Evidence ref / Argument link
... (S2, S3, ...)
### Counter
#### Counter 1
- 声音 / 回应
### Argument Chain
- 结论 + 说明

---

## §2 Section Slices
### §1. <title>
- Core claim / Evidence needed / Reader payoff / Programmer implication / Counterargument
- Acceptance criteria (bullet list)
... (§2, §3, ...)

---

## §3 Decision Log
- Round N (phase): decision — reason
... 或 _（无内部循环；首轮即通过）_
```

---

## mode 自动检测

`finalize-outline.py commit` 启动时检查 `articles/<slug>/02-research.md` 是否存在：

| 文件 | mode | 影响 |
|---|---|---|
| 存在 | `brief_plus_research` | 渲染头部"v2.0 完整路径" |
| 缺失 | `brief_only` | 渲染头部"⚠️ evidence 未独立验证" + 提示 v2.0 跑 /szw-research |

mode 不在 stdin JSON 里 —— 由脚本根据文件存在与否判定，避免 AI 撒谎。

---

## claim ID 稳定性约定

prepare-outline.py 按 brief.supporting_claims 顺序分配 `C1..Cn`。AI 在 `thesis_map.supporting[].claim_id` 必须使用此 ID。
- 增加 supporting：必须在 brief 阶段做（重跑 `/szw-discuss`），不在 outline 阶段擅自加
- 删除 supporting：outline 可以选择不引用某个 claim_id，但 brief 里仍保留（不重跑 discuss 不删）
- 拆分 / 合并 supporting：见上一条；要在 brief 阶段做

这与 `prepare-research.py` / `finalize-research.py`（待建）的 claim ID 规则一致。

---

## 同步更新清单

- [ ] `scripts/finalize-outline.py` —— `REQUIRED_*_FIELDS` + `render_outline_md()`
- [ ] `references/outline-schema.md` —— 本文档
- [ ] `study/fan.md` §4.3 —— Phase 1/2 字段
- [ ] 下游 `/szw-write`：读 03-outline.md 时按本 schema 解析 section slices
- [ ] 上游 `/szw-research`（待建）：commit 时若有 thesis 微调，需考虑 outline 是否要重跑
