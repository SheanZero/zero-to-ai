# ARTICLE.md Schema

> `articles/<slug>/ARTICLE.md` 的字段契约 —— 文章元数据 + 项目状态 + 流水线锚点。
> 修改本文档须同步更新 `templates/ARTICLE.md`、`scripts/new-article.py`、各下游 skill 的解析器。

---

## 文件位置

`<column_root>/articles/<slug>/ARTICLE.md`

每个 article 有且仅有一份。终态后不删（completed 留原位；archived 移到 `articles/archived/<slug>/`）。

---

## 整体结构

```
---
<YAML frontmatter>
---

# <Working Title>

## Thesis
## Source Material
## Status Log
```

---

## YAML Frontmatter 字段

| 字段 | 类型 | 必需 | 由谁写 | 取值 |
|---|---|---|---|---|
| `slug` | str | ✅ | `/szw-new-article` | 全局唯一；regex `^[a-z0-9][a-z0-9-]*$`；通常 `YYYY-MM-<topic>` |
| `title` | str | ✅ | `/szw-new-article`（默认从 slug 推） | working title；最终标题在 publish 阶段定 |
| `type` | enum | ✅ | `/szw-new-article` | `industry-analysis` / `programmer-advice` / `product-analysis` / `tech-blog` |
| `target_platforms` | list[str] | ✅ | `/szw-new-article`（默认从 config 取） | 子集 of `[blog, wechat, x, xhs]` |
| `status` | enum | ✅ | 各流水线命令推进 | 见下表 |
| `created_at` | date | ✅ | `/szw-new-article` | `YYYY-MM-DD` |
| `linked_series` | str / null | ⛔ | `/szw-new-article --series` | 系列名；对应 `series/<name>/INDEX.md` |
| `linked_inbox` | str / null | ⛔ | `/szw-new-article --from-inbox` | 原 inbox slug；对应 `inbox/done/<slug>.md` |

### status 枚举（11 种，与 STATE.md schema 对齐）

| Status | 由谁推进 | 是否 active |
|---|---|---|
| `created` | `/szw-new-article` | ✅ |
| `brief_done` | `/szw-discuss` | ✅ |
| `research_done` | `/szw-research`（v2.0） | ✅ |
| `outline_done` | `/szw-outline`（v2.0） | ✅ |
| `draft_done` | `/szw-write` | ✅ |
| `review_failed` | `/szw-review` | ✅ |
| `review_passed` | `/szw-review` | ✅ |
| `published` | `/szw-publish` | ✅ |
| `paused` | `/szw-pause`（v3.0） | ✅ |
| `completed` | `/szw-complete --published` | ❌（终态） |
| `archived` | `/szw-complete --archived` | ❌（终态） |

详见 `study/fan.md` §3.0 状态机定义。

---

## H2 段落

### `## Thesis`

`/szw-new-article` 留空（带提示文本）；`/szw-discuss` Phase 2 写入。

格式：1-2 段陈述 + bullet 形式的 supporting claims。详见 `01-brief.md` 的 thesis 节。

> **设计决定**：thesis 在 ARTICLE.md 是冗余字段（也在 01-brief.md 里），但放这里方便 `/szw-resume` 不读 brief 就能看到。

### `## Source Material`

可选输入材料：
- `--from-inbox` 时，自动嵌入 inbox/done/<slug>.md 内容（带 HTML 注释标注来源）
- 否则仅占位提示，由用户手填

### `## Status Log`

按时间顺序的状态变更记录，每行一个条目：

```
- 2026-05-06: created via /szw-new-article
- 2026-05-06: brief_done via /szw-discuss
- 2026-05-06: review_failed (3 HIGH issues, see 05-review.md)
```

各流水线命令推进 status 时**追加一行**，不覆盖。便于 `/szw-retro` 复盘时间线。

---

## 字段不变性（重要）

| 字段 | 创建后可变？ |
|---|---|
| `slug` | ❌ 永不变 —— 改名等于新文章；目录名也是 slug |
| `title` | ✅ 可变（最终由 `/szw-publish` 定） |
| `type` | ⚠️ 可变但慎重（影响 review / publish 模板） |
| `target_platforms` | ✅ 可变（publish 前可调整） |
| `status` | ✅ 由命令推进 |
| `created_at` | ❌ 永不变 |
| `linked_series` | ⚠️ 应只在 `/szw-new-article` 时设定；事后修改需手动同步 series INDEX |
| `linked_inbox` | ❌ 永不变 |

---

## 下游消费者

| 字段 | 谁读 | 用途 |
|---|---|---|
| `slug` | 所有命令 | 定位 articles/<slug>/ |
| `title` | `/szw-write` `/szw-publish` | 起稿 / 打包 |
| `type` | `/szw-discuss` `/szw-write` `/szw-review` | 选模板 / 风格预设 |
| `target_platforms` | `/szw-publish` | 决定打包多少份 |
| `status` | 所有命令 | gate 检查（如 publish 要求 review_passed） |
| `created_at` | `/szw-stats` `/szw-summary` | 统计 / 报告 |
| `linked_series` | `/szw-series` `/szw-publish` | 系列引用 / cross-link |
| `linked_inbox` | `/szw-retro` | 复盘灵感来源 |

---

## 同步更新清单（变更字段时）

- [ ] `templates/ARTICLE.md` —— 模板要反映新字段
- [ ] `scripts/new-article.py` —— `render_article_md()` 的 substitutions
- [ ] `references/article-md-schema.md` —— 本文档
- [ ] `study/fan.md` §3.2 —— 命令规约
- [ ] 所有读 ARTICLE.md 的下游 skill（`szw-resume` `szw-discuss` `szw-write` 等）
