# 02-research.md Schema

> `/szw-research commit` 通过 stdin 接收的 JSON 字段契约 + 渲染到 `articles/<slug>/02-research.md` 的结构。
> 修改本文档须同步更新 `scripts/finalize-research.py` 的 `REQUIRED_*_FIELDS` / `VALID_*` 集合 + `render_research_md()`。

---

## stdin JSON top fields

| 字段 | 类型 | 必需 | 说明 |
|---|---|---|---|
| `evidence_cards` | list[Card] | ✅ | Phase 1 产物（每个 claim 一张证据卡）；可空数组（diagnosis-only 报告） |
| `claim_diagnosis` | list[Diag] | ✅ | Phase 2 产物（每个 claim 一份诊断）；非空 |
| `overall_credibility` | enum | ✅ | `high` / `medium` / `low` |
| `high_risk_claims` | list[str] | ✅ | claim_id 列表；**必须等于** diagnosis 中 risk='H' 的 claim_id 集合 |
| `loop_rounds` | int | ✅ | Phase1↔Phase2 内部循环次数（0/1/2；非负整数） |
| `verdict` | enum | ✅ | `passed` / `passed_with_high_risk` / `needs_rework` |
| `user_decision` | enum/null | ⛔ | 仅 verdict='passed_with_high_risk' 时必填：`accept` / `downgrade` |
| `recommended_actions` | list[str] | ⛔ | 给下游 write 的提示项 |
| `notes` | str | ⛔ | 整体说明 |
| `evidence_bank_writes` | list[BankWrite] | ⛔ | 同步到 `.zero/evidence/<topic>.md` 的源；可省略 |

### `Card` 项（evidence_cards 元素）

| 字段 | 类型 | 必需 | 说明 |
|---|---|---|---|
| `claim_id` | str | ✅ | C1..Cn（来自 prepare-research.py） |
| `claim_text` | str | ✅ | 原文（来自 brief） |
| `status` | enum | ✅ | `covered` / `source_needed` / `weak` |
| `sources` | list[Source] | ✅ | 可空（如 status=source_needed） |

### `Source` 项

| 字段 | 类型 | 必需 | 说明 |
|---|---|---|---|
| `type` | str | ✅ | 自由字串：`official-doc` / `paper` / `blog` / `community` / `interview` / 等 |
| `title` | str | ✅ | 来源标题 |
| `date` | str | ⛔ | YYYY-MM-DD；缺失渲染为 `_unknown_` |
| `url` | str | ✅ | 链接 |
| `quote` | str | ✅ | 关键引文 |
| `confidence` | enum | ✅ | `high` / `medium` / `low` |

### `Diag` 项（claim_diagnosis 元素）

| 字段 | 类型 | 必需 | 说明 |
|---|---|---|---|
| `claim_id` | str | ✅ | 与 evidence_cards 同 ID 体系 |
| `claim_text` | str | ✅ | 原文 |
| `type` | enum | ✅ | `fact` / `interpretation` / `opinion` / `prediction` / `advice` |
| `evidence_required` | str | ✅ | 若要让此 claim 站住，需要什么证据 |
| `evidence_available` | str | ✅ | 实际有什么证据 |
| `counter_evidence` | str | ⛔ | 反向证据；可空字串 |
| `confidence` | enum | ✅ | `high` / `medium` / `low` |
| `risk` | enum | ✅ | `L` / `M` / `H` |
| `safer_rewrite` | str | ✅ | 降低风险的措辞建议 |

### `BankWrite` 项（evidence_bank_writes 元素）

```json
{
  "topic": "claude-code-skills",   // slug 格式：[a-z0-9][a-z0-9-]*
  "sources": [
    {"title": "...", "url": "...", "quote": "...",
     "confidence": "high", "from_claim": "C1", "date": "2026-04-20"}
  ]
}
```

`from_claim` 字段是 BankWrite source 独有（cards/sources 没有），用于在 evidence bank 文件里标"哪个 claim 引用了它"。

---

## verdict gate

| verdict | high_risk_claims | user_decision | 行为 |
|---|---|---|---|
| `passed` | 空 | (任意) | ✅ commit |
| `passed` | 非空 | (任意) | ❌ exit 5（自相矛盾） |
| `passed_with_high_risk` | 空 | (任意) | ❌ exit 5（应改用 passed） |
| `passed_with_high_risk` | 非空 | `accept` | ✅ commit + WARN 输出 HIGH-risk claim ID |
| `passed_with_high_risk` | 非空 | `downgrade` | ❌ exit 5 提示回 /szw-discuss 改 brief |
| `passed_with_high_risk` | 非空 | `null` 或缺失 | ❌ exit 5 让用户先决定 |
| `needs_rework` | (任意) | (任意) | ❌ exit 5（loop 已用尽，必须 escalate） |

---

## 渲染输出（02-research.md）

```
# 02-research — <slug>

> 由 /szw-research 在 <date> 产出。
> Brief reference: 01-brief.md
> 内部循环：<n> 轮 · 结论：<verdict>

## §1 Evidence Cards
### C1 — <claim text>
**Status**: ✅ covered | 🔍 source_needed | ⚠️ weak

#### Source 1: <title>
- Type / Date / URL / Quote / Confidence
... (Source 2, ...)
... (C2, C3, ...)

---

## §2 Claim Diagnosis
### C1 — <claim text>
- Type / Evidence Required / Evidence Available / Counter-Evidence
- Confidence / Risk / Safer Rewrite (blockquote)
... (C2, C3, ...)

---

## §3 Recommended Action
- Overall Credibility: 🟢/🟡/🔴
- High-Risk Claims: ...
- Loop Rounds / Verdict / User Decision

### Action Items
### Notes
### Evidence Bank Sync
- `<topic>` — N source(s) appended
```

---

## claim ID 一致性

- `evidence_cards[].claim_id` 和 `claim_diagnosis[].claim_id` 必须用 prepare-research.py 给出的 `C1..Cn`
- 不强制覆盖（AI 可以选择不评估某些显然 claim），但建议每个 brief.supporting_claims 都有 diagnosis
- `high_risk_claims` 必须严格等于 `claim_diagnosis` 中 `risk='H'` 的 claim_id 集合（脚本强制校验，不一致 exit 4）

---

## 同步更新清单

- [ ] `scripts/finalize-research.py` —— `REQUIRED_*_FIELDS` / `VALID_*` / `render_research_md()` / `check_verdict_gate()`
- [ ] `references/research-schema.md` —— 本文档
- [ ] `references/evidence-bank.md` —— BankWrite 同步行为
- [ ] `study/fan.md` §4.2 —— 命令规约
- [ ] 下游 `/szw-outline`：读 02-research.md 时按本 schema 解析；mode 检测看 02-research.md 是否存在
- [ ] 下游 `/szw-write`：HIGH-risk claim 的 `safer_rewrite` 应在起稿时优先采用
