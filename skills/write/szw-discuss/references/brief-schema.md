# 01-brief.md Schema

> `/szw-discuss commit` 通过 stdin 接收的 JSON 字段契约，以及最终渲染到 `articles/<slug>/01-brief.md` 的结构。
> 修改本文档须同步更新 `scripts/finalize-discuss.py` 的 `REQUIRED_BRIEF_FIELDS` 和 `render_brief_md()`。

---

## stdin JSON 字段（commit 子命令）

| 字段 | 类型 | 必需 | 说明 |
|---|---|---|---|
| `thesis` | str | ✅ | 一句话核心命题；同步回填 `ARTICLE.md` 的 Thesis 段 |
| `reader_payoff` | str | ✅ | 读者读完得到什么具体收益（不是"了解"，是"能做"） |
| `supporting_claims` | list[str] | ✅ | 3-5 条支撑论点；空列表会渲染为 `_（无）_` |
| `counterargument` | str | ✅ | 强读者会怎么反驳；至少写 1 条 |
| `evidence_needed` | list[str] | ✅ | research 阶段要找的证据清单 |
| `out_of_scope` | list[str] | ✅ | 明确不写的子话题（防止 scope creep） |
| `target_platforms` | list[str] | ⛔ | 可选；如给则覆盖 ARTICLE.md frontmatter；合法 item: blog/wechat/x/xhs |
| `grill_qa` | list[QA] | ✅ | 拷问 9 问问答记录；非空数组 |
| `alignment_check` | dict | ✅ | 与 ADR / EDITORIAL_CONTEXT 比对结果 |

### `QA` 项 schema

```json
{
  "q": "What popular misunderstanding does this challenge?",
  "user_answer": "...",
  "ai_recommendation": "...",
  "final": "..."
}
```

四个字段都建议给（缺则渲染时跳过该行）；`q` 必给。

### `alignment_check` 字段

```json
{
  "adrs_consulted": ["0001", "0002"],
  "principles_consulted": ["P1", "P3"],
  "conflicts": [],
  "notes": "..."
}
```

| 子字段 | 类型 | 说明 |
|---|---|---|
| `adrs_consulted` | list[str] | ID 字串（如 "0001"）；用于附录 B |
| `principles_consulted` | list[str] | 原则编号（参考 EDITORIAL_CONTEXT §3） |
| `conflicts` | list[str] | **关键 gate**：非空 → commit 拒绝（exit 5），让 AI 改用 abort 或修 brief |
| `notes` | str | 比对说明文字 |

---

## 渲染输出（01-brief.md）

```
# 01-brief — <slug>

> 由 /szw-discuss 在 <date> 产出。
> Article type: <type>

## Thesis
## Reader Payoff
## Supporting Claims              ← bullet list
## Counterargument
## Evidence Needed                ← bullet list
## Out of Scope                   ← bullet list
## Target Platforms

---

## 附录 A：Topic Grill Q&A
### Q1. <question>
- **User**: ...
- **AI 建议**: ...
- **采纳**: ...
... (Q2 到 Q9)

---

## 附录 B：宪法对齐检查
- **ADR 比对**: 0001, 0002
- **Principles 比对**: P1, P3

**冲突结论**: 无冲突 / 列冲突 bullet
**说明**: ...
```

---

## 同步更新清单

- [ ] `scripts/finalize-discuss.py` —— `REQUIRED_BRIEF_FIELDS` + `render_brief_md()`
- [ ] `references/brief-schema.md` —— 本文档
- [ ] `study/fan.md` §3.3 —— Phase 2 字段列表
- [ ] 下游 `/szw-research` `/szw-outline` `/szw-write`：读 `01-brief.md` 时按本 schema 解析
