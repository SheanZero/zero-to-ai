# Evidence Bank Schema

> `.zero/evidence/<topic>.md` —— 跨文章复用的证据沉淀。
> 由 `/szw-research commit` 的 `evidence_bank_writes` 字段触发；其他 skill 只读不写。

---

## 文件位置

`<column_root>/.zero/evidence/<topic>.md`

- `topic` 必须是 slug 格式：`^[a-z0-9][a-z0-9-]*$`
- 推荐按主题取名（如 `claude-code-skills` / `agentic-coding-2026` / `gsd-architecture`）
- 退役的证据移到 `.zero/evidence/retired/<topic>.md`，prepare-research.py 自动跳过 retired

---

## 文件结构

```markdown
# Evidence: <topic>

> Auto-collected by `/szw-research`. Last updated: <YYYY-MM-DD>

## Sources

### <Source title> (<date>)
- **URL**: <url>
- **Quote**: > <inline quote>
- **Confidence**: high | medium | low
- **Used in**: `<slug>` (claim <Cn>, added <YYYY-MM-DD>)

### <Another source> (<date>)
- ...
```

---

## 写入行为（finalize-research.py）

| 情况 | 行为 |
|---|---|
| 文件不存在 | 创建：写 H1 + meta blockquote + `## Sources` + 第一批 source(s) |
| 文件已存在 | 1) 更新 meta blockquote 的 `Last updated` 字段；2) 在文件末追加新 source(s)（不去重，不排序） |

不去重的理由：
- 同 URL 不同 quote 是合理的（不同段落引用同一来源）
- 同 URL 同 quote 但来自不同 article 也保留（看哪些文章都用了它，便于 audit）
- 真要清理 → 由作者手动或后续 `/szw-evidence-bank`（v3.0）处理

---

## 字段说明

| 字段 | 来源 | 备注 |
|---|---|---|
| `Source title` | BankWrite.sources[].title | H3 标题；后接 `(date)` |
| `URL` | BankWrite.sources[].url | 来源链接 |
| `Quote` | BankWrite.sources[].quote | 关键引文（一句即可） |
| `Confidence` | BankWrite.sources[].confidence | high/medium/low |
| `Used in` | 自动注入 | `\`<slug>\` (claim <Cn>, added <date>)` |
| `from_claim` | BankWrite.sources[].from_claim | 不直接渲染，融合到 "Used in" 行 |

---

## 用法（其他 skill 如何复用）

### `/szw-research` Phase 1（自身）

prepare-research.py 输出 `existing_evidence_topics`：每个 topic 的 path / modified / size。AI 在 Phase 1 收集证据时：
1. 看主题相关的 evidence file
2. 视相关性 Read 该文件
3. 复用已有 source（在 `evidence_cards[].sources` 里直接引用）
4. 新发现的源继续走 `evidence_bank_writes` 沉淀

### `/szw-write`（v1.0/v2.0）

write 阶段如需引用证据，可读 02-research.md（首选）或 .zero/evidence/<topic>.md（次选，跨文章背景）。

### `/szw-audit`（v3.0）

审计专栏一致性时，可对比所有文章的引用源是否互相矛盾、URL 是否失效、quote 是否准确等。

---

## 与 ARTICLE.md / STATE.md 的关系

evidence bank 是 **column-scoped** 资产（不属于任何单个 article）：
- 创建 / 修改不更新 ARTICLE.md
- 不在 STATE.md 表里出现
- 跟随 column 容器目录走（git 跟踪）

article 通过 `Used in` 行的 backlink 反向定位"哪些 article 引用过这条 source"。

---

## 同步更新清单

- [ ] `scripts/finalize-research.py` 的 `append_to_evidence_bank()` —— 写入逻辑
- [ ] `scripts/prepare-research.py` 的 `list_evidence_bank()` —— 列出逻辑
- [ ] `references/evidence-bank.md` —— 本文档
- [ ] `study/fan.md` §9 目录布局中的 `.zero/evidence/`
