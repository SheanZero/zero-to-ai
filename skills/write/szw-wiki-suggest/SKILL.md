---
name: szw-wiki-suggest
description: Recommend relevant wiki pages and resources for an article (by slug → reads articles/<slug>/ARTICLE.md ## Thesis section) or for free-text input (--thesis "..."). Consumes .zero/wiki-cache/{pages,reverse,resources}.json (rebuilt by /szw-wiki-import or /szw-wiki-ingest). Scores by tag overlap × type priority (connections>topics>concepts>tools>people>frameworks>hubs) × status (mature>active>stub) + inlinks. Returns markdown grouped by type, or --json for downstream consumers (szw-discuss prepare v2).
---

# szw-wiki-suggest

给一个 article（或自由 thesis 文本）推荐相关 wiki 页 + resources，作为写作前的"先看 wiki 有没有"提示。

## 何时使用

- 进 `/szw-discuss` 前手动看哪些 wiki 资源可以引用：`/szw-wiki-suggest <slug>`
- 试探一个未立项的话题在已有 wiki 中的覆盖：`/szw-wiki-suggest --thesis "<keywords>"`
- 给 v2 的 `/szw-discuss` prepare 阶段自动调用（`auto_suggest_in_discuss=true`）

## 何时不用

- wiki 还没建 → 先 `/szw-wiki-init` + `/szw-wiki-ingest`
- 想读完整 wiki 页内容 → 直接 Read 该页
- 想生成一段综合答案 → `/szw-wiki-query`（v2）
- 想写新的 stub 页 → `/szw-wiki-create-page`（v2）

---

## 调用语法

| 形式 | 行为 |
|---|---|
| `/szw-wiki-suggest <slug>` | 从 `articles/<slug>/ARTICLE.md` 提取 `## Thesis` + frontmatter title 作为关键词源 |
| `/szw-wiki-suggest --thesis "<text>"` | 直接用自由文本 |
| `/szw-wiki-suggest <slug> --type concepts` | 只看某一类（`connections / topics / concepts / tools / people / frameworks / hubs`） |
| `/szw-wiki-suggest <slug> --limit 20` | 调最大返回数（默认 12） |
| `/szw-wiki-suggest <slug> --json` | 输出结构化 JSON（给 szw-discuss prepare v2 等下游） |
| `/szw-wiki-suggest --target <dir>` | 指定 Column 根 |

---

## 执行流程

本 skill 是**纯只读**的脚本式查询，无 phase / 无事务 / 不写盘。

### Phase 0：preflight

- `<target>/.zero/szw-config.json` 存在 + `wiki.enabled=true`
- `<target>/.zero/wiki-cache/{pages,reverse}.json` 存在（否则提示先跑 `rebuild-indexes.py` 或任一 ingest/import）

### Phase 1：关键词抽取

```bash
python3 scripts/suggest.py <slug>
python3 scripts/suggest.py --thesis "..."
```

- **slug 模式**：读 `articles/<slug>/ARTICLE.md`，提取 frontmatter `title` + `## Thesis` 段全文
- **thesis 模式**：直接用 `--thesis` 文本

文本切分：
- 英文 token：`[A-Za-z][A-Za-z0-9_-]{2,}`，lowercase，去停用词
- CJK 2-gram：连续 CJK run 上滑窗 2 字
- 关键词集：`en_keywords`（与 page tags 比对）+ `cjk_bigrams`（与 title/summary 子串比对）

### Phase 2：评分

对每个 wiki 页：

```
raw   = tag_overlap × 10 + title_hits × 5 + summary_hits × 2
score = raw × type_weight × status_weight + inlinks × 0.5
```

| 维度 | 取值 |
|---|---|
| `tag_overlap` | `set(page.tags) ∩ en_keywords` 大小 |
| `title_hits` | en_keywords + cjk_bigrams 在 title.lower() 子串命中数 |
| `summary_hits` | 同上，但在 summary_head（首段 200 字摘要） |
| `type_weight` | connections=5 > topics=4 > concepts=3 > tools=2.5 > people=2 > frameworks=1.5 > hubs=1 |
| `status_weight` | mature=3 > active=2 > stub=1 |
| `inlinks` | 其他 wiki 页 `related[]` 中引用本页的次数 |

`raw == 0` 的页直接丢弃；其余按 score 降序取前 `--limit`。

### Phase 3：分组输出

- markdown：按 type 分组，每条 `<slug> <status> (score=, tags=)` + summary 一行
- 末尾追加 top 页的 sources（去重）作为 `### related resources`
- `--json`：完整 breakdown 给下游

完成 marker：`## SUGGESTIONS READY`（参 fan-llm-wiki-extension §10 子 agent 表）

---

## 输出示例

### Markdown 默认

```
## SUGGESTIONS READY

For: 2026-05-llm-wiki-deep-dive
Source: articles/2026-05-llm-wiki-deep-dive/ARTICLE.md
Keywords: en=8 cjk=12

### concepts (3)

- **[llm-wiki-pattern](wiki/concepts/llm-wiki-pattern.md)** `active` (score=132.0, tags=ai,knowledge-management)
  Karpathy 提出的用 LLM 维护个人 wiki 的工作流。相比 RAG 的优势在于知识的结构化与可演化。
- **[agentic-coding-loop](wiki/concepts/agentic-coding-loop.md)** `stub` (score=15.0)
  ...

### people (1)

- **[andrej-karpathy](wiki/people/andrej-karpathy.md)** `stub` (score=20.0, tags=ai)
  ...

### related resources (3)

- resources/2026-05-07-foo-test.md `[ai,knowledge-management]` — Foo Test 文章
- ...
```

### JSON（`--json`）

```json
{
  "slug": "2026-05-llm-wiki-deep-dive",
  "source": "articles/.../ARTICLE.md",
  "keywords": {"english": [...], "cjk_bigrams": [...]},
  "suggestions_by_type": {
    "concepts": [
      {
        "path": "wiki/concepts/llm-wiki-pattern.md",
        "slug": "llm-wiki-pattern",
        "title": "LLM Wiki 模式",
        "status": "active",
        "score": 132.0,
        "breakdown": {
          "tag_overlap": ["ai", "knowledge-management"],
          "title_hits": 2,
          "summary_hits": 4,
          "type_weight": 3.0,
          "status_weight": 2.0,
          "inlinks": 1,
          "raw": 22.0
        }
      }
    ],
    "people": [...]
  },
  "related_resources": [...],
  "total_matched": 5,
  "returned": 5
}
```

---

## 退出码

| 码 | 含义 | 应对 |
|---|---|---|
| 0 | 成功 | — |
| 1 | 非 column / wiki 未启用 / wiki-cache 缺失 / 参数不合法 | 检查 cwd 或先跑 `rebuild-indexes.py` |
| 2 | slug 不存在（articles/<slug>/ARTICLE.md 缺失） | 检查 slug 是否拼对 |
| 3 | `--thesis` 与 slug 同时给（互斥） | 二选一 |
| 4 | 关键词抽取为空 | thesis 文本太短或全是停用词；改用更具体的 thesis |

---

## Gates

| 类型 | 触发 | 处理 |
|---|---|---|
| **Pre-flight** | `wiki.enabled=true` + cache 存在 | 否则 exit 1 |
| **互斥** | `--thesis` + 位置 slug 同时给 | exit 3 |
| **空匹配** | scored 列表为空 | 仍输出空 markdown（"For: <slug>" + 0 条），不是错误 |
| **不写盘** | 红线 | 脚本只读 |

---

## 设计原则

1. **只读 + 幂等**：不修改任何文件，可任意重复跑
2. **rebuild-indexes 是 source of truth**：所有匹配都基于 cache，避免每次重扫 wiki 目录
3. **评分透明**：`--json` 模式暴露完整 breakdown（tag_overlap / title_hits / weights / inlinks），便于调参与 debug
4. **type 权重偏 connection / topic**：这两类是"综合页"，对写作的引用价值高于 stub concept
5. **CJK 用 2-gram**：避免分词依赖；2-gram 已能命中"知识管理"/"agentic 编程"/"Wiki 模式"等常见短语
6. **不依赖嵌入 / LLM**：v1 完全确定性；v2 可加 wiki-suggester sub-agent 做语义召回

---

## 子 agent

v1 全脚本。v2 计划：

| Agent | 角色 | Marker | 跑在 |
|---|---|---|---|
| `wiki-suggester` | 语义召回（嵌入 / LLM rerank）；处理脚本评分为 0 但语义相关的边缘项 | `## SUGGESTIONS READY` | Claude |

---

## 与其他命令的关系

- **上游**（必须先跑过其一）：
  - `/szw-wiki-import`（vault seed → 触发 rebuild）
  - `/szw-wiki-ingest`（resources → wiki → 触发 rebuild）
  - 或手动跑 `scripts/rebuild-indexes.py`
- **下游**（v2）：
  - `/szw-discuss` prepare 调本 skill 的 `--json` 模式输出 `wiki_refs[]` 写入 brief context
  - `/szw-research` prepare 同上，evidence card 加 `wiki_ref / resource_ref`
- **平行**：
  - `/szw-wiki-query`（v2，综合回答）—— suggest 是"列举"，query 是"回答"
  - `/szw-wiki-lint`（v2，健康检查）—— 互不干扰

---

## 不实现的事（v1）

- **不写盘 / 不 git commit**
- **不调 LLM**：评分纯确定性
- **不读 brief / outline**：仅 ARTICLE.md `## Thesis` 段（够用且稳定）
- **不做语义召回**：靠 tag/title/summary 子串 + 加权
- **不做反向 trace**（"哪些 article 引用了这个 wiki 页"）→ 留给 `/szw-wiki-trace`（v2）
- **不补 missing 关键词**：thesis 太短 → exit 4，不擅自扩展

---

## 完成 marker

```
## SUGGESTIONS READY
- For: <slug or --thesis label>
- Source: <articles/<slug>/ARTICLE.md or --thesis>
- Total matched: <count>
- Returned: <limit>
```

无匹配：

```
## SUGGESTIONS READY (empty)
- Reason: 0 wiki pages match keywords
- Suggestion: 用 /szw-wiki-create-page 建 stub 或扩 thesis 关键词
```

错误：

```
## SUGGEST BLOCKED
- Reason: <e.g. cache missing | invalid slug | empty keywords>
- Suggestion: <next step>
```

---

## 反模式

1. **不要在 ingest 之前跑 suggest**——cache 缺失 → exit 1
2. **不要把短 thesis（< 5 词）直接喂进来**——关键词不够 → exit 4
3. **不要预期语义级别的相关性**——v1 是 tag/字串级；强语义相似项可能 score=0 被丢弃，这是已知 trade-off
4. **不要把 `--json` 输出贴回给用户**——给下游脚本用；面向人时用默认 markdown
