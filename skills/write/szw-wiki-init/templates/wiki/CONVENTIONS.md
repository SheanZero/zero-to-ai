# Wiki Conventions

> 本文件规定 wiki/ / resources/ / inbox/sources/ / assets/ 中文件的命名、frontmatter、链接、标签、附件路径约定。
>
> ingest / query / lint 流程详见 [`WORKFLOWS.md`](WORKFLOWS.md)。
>
> 本约定基于 [Karpathy LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) + [SheanZero vault conventions](file:///path/to/vault/conventions.md) 演化。

> Initialized: <YYYY-MM-DD>
> schema_version: 1.2

---

## 一、文件命名

### resources/

格式：`YYYY-MM-DD-<slug>.md`

- `YYYY-MM-DD`：捕获日期（不是原始发布日期）
- `slug`：英文小写连字符短语，简洁描述内容
- 示例：
  - `2026-04-04-karpathy-llm-wiki.md`
  - `2026-04-10-attention-is-all-you-need.md`
  - `2026-04-10-podcast-lex-fridman-altman.md`

### inbox/sources/

同 `resources/` 命名格式（review 通过、迁移到 `resources/` 时不需重命名）。

### wiki/

格式：`<slug>.md`（不带日期，因为是持续演进的）

- 全小写，连字符分隔
- 简洁但具描述性
- 示例：
  - `concepts/llm-wiki-pattern.md`
  - `people/andrej-karpathy.md`
  - `topics/agentic-coding.md`
  - `frameworks/grokking-deep-learning.md`
  - `tools/claude-code.md`
  - `connections/wiki-vs-rag.md`
  - `hubs/agent-systems.md`

### assets/

**子目录命名**：与关联的 markdown 文件名同名（去 `.md`）

- `resources/2026-05-06-foo.md` → `assets/2026-05-06-foo/`
- 例外：`assets/wiki-illustrations/`（wiki 自创图，未关联具体 resource）

**附件文件命名**：自由，建议语义化：

- `page_01.jpg` / `page_02.jpg`（截图序列）
- `architecture-diagram.png`
- `interview-transcript.pdf`

---

## 二、Frontmatter

### resources/<file>（必备）

```yaml
---
type: article | paper | book | book-chapter | video | podcast | conversation | tweet | repo | other
title: "原始标题"
source: "https://..."           # 原始链接，本地文件可省略
author: "作者姓名"               # 多人用数组
captured: 2026-04-10             # 捕获日期
lang: zh | en | ...
tags: [tag1, tag2]               # 用户随手打的标签
processed: false                 # ingest 后改 true
wiki_pages: []                   # ingest 后填入生成的 wiki 页路径
summary: ""                      # ingest 后填入一句话摘要
# --- 仅 type: repo 时使用 ---
stars: 0
last_commit: 2026-04-10
repo_status: active              # active | archived | stale
relevance: medium                # high | medium | low
use_case: ""                     # 一句话：为什么关注
---
```

### inbox/sources/<file>（resources 必备 + 加 read 字段）

```yaml
---
type: article
title: "..."
source: "..."
author: "..."
captured: 2026-05-06
lang: zh
tags: [...]
read: false                      # 用户 review 后改 true → 触发自动迁移到 resources/
read_notes: ""                   # 可选简评
---
```

### wiki/<type>/<slug>.md（必备）

```yaml
---
type: concept | person | topic | framework | tool | connection | hub
title: "页面标题"
created: 2026-04-10              # 首次创建日期
updated: 2026-04-10              # 最近更新日期
sources: []                      # 关联的 resource 路径数组（hub 可空）
related: []                      # 相关 wiki 页双向链接
status: stub | active | mature
tags: []
derived: false                   # true = 反向沉淀页（essay → wiki connection），降权使用
---
```

字段说明：
- `sources` 对内容页必须；`hub` 页允许为空（hub 只做导航）
- `status`：`stub` → `active`（多来源） → `mature`（结构稳定）
- `tool` 类型页若来源是 GitHub 仓库可追加 `stars` / `last_commit` / `repo_status`
- `derived: true` 标记综合产物（如 `/szw-wiki-feedback` 从 essay 提取的连接），lint 时降权评分

---

## 三、链接格式

### Wiki 内部链接（Obsidian wikilink）

```markdown
[[wiki/concepts/llm-wiki-pattern|LLM Wiki 模式]]
[[wiki/people/andrej-karpathy|Karpathy]]
```

### Wiki → Resource 溯源

在 wiki 页底部用 `## Sources` 章节列出：

```markdown
## Sources

- [[resources/2026-04-04-karpathy-llm-wiki|Karpathy: LLM Wiki]] (2026-04-04)
- [[resources/2026-04-10-some-paper|Some Paper Title]] (2026-04-10)
```

### Markdown → Asset 引用（路径表）

| 文件位置 | 引用路径 | 相对深度 |
|---|---|---|
| `inbox/sources/<file>.md` | `![[../../assets/<slug>/img.jpg]]` | 2 层 |
| `resources/<file>.md` | `![[../assets/<slug>/img.jpg]]` | 1 层 |
| `wiki/<type>/<file>.md` | `![[../../assets/<slug>/img.jpg]]` | 2 层 |

ingest 迁移时自动 rewrite 引用相对深度。

### 跨 Column → vault（如 vault.path 已配置）

- 用 `file:///<vault>/...` 绝对路径
- 仅用于 wiki/ 中 import 来的页（vault seed 来源）
- szw 自创的页**不要**外链 vault

### 外部链接

普通 markdown 链接 `[文本](https://...)`，不要混用 Obsidian 语法。

---

## 四、标签

### 命名

- 全小写，连字符分隔
- 不嵌套（避免 `#ai/llm/transformer`）
- 一个文件 3-7 个标签为佳

### 推荐顶层标签

- 领域：`#ai` `#dev-workflow` `#productivity` `#engineering` `#design`
- 类型：`#concept` `#tool` `#paper` `#tutorial` `#opinion`
- 状态：`#stub` `#evergreen` `#archived`

---

## 五、Markdown 风格

### 标题层级

- `# 一级标题`：仅文件标题（与 frontmatter title 一致）
- `## 二级`：主要章节
- `### 三级`：子章节
- 不超过四级

### 列表

- 无序列表用 `-`
- 有序列表用 `1.` `2.`
- 嵌套用 2 空格缩进

### 引用

- 引用原文用 `>`
- 标注来源：`> "..." — 作者，《来源》`

### 分隔

- 章节间空行
- 大段落分隔可用 `---`，不滥用

---

## 六、日期与时间

- 日期：`YYYY-MM-DD`
- 周：`YYYY-Www`（ISO 8601）
- 不用相对日期（"昨天" / "上周"）
- log.md 条目：`## [YYYY-MM-DD HH:MM] {operation} | {target}`

---

## 七、特殊文件

### INDEX.md（任何目录的）

- 第一行：`# {目录名}`
- 内容：该目录下文件的目录树 + 一句话描述
- ingest 后必须更新对应 INDEX.md

### log.md

- wiki 全局日志在 `wiki/log.md`
- 条目格式见上文"日期与时间"

### CLAUDE.md / AGENTS.md / CONVENTIONS.md / WORKFLOWS.md

- 由 `/szw-init` 生成
- 用 `<!-- szw-init:auto-* -->` 标记块包裹机器维护区
- 用户编辑应在标记块**外**进行
