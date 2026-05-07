# szw-wiki-init Templates

wiki 层 schema 文件与 INDEX 模板，由 [`SKILL.md`](../SKILL.md) Phase 3 渲染到 Column 内。

## 文件清单

### Schema 文件（始终渲染，含标记块，走聚合）

| 模板 | 写入位置 | 用途 |
|---|---|---|
| `wiki/CONVENTIONS.md` | `<target>/wiki/CONVENTIONS.md` | 命名 / frontmatter / 链接 / 附件路径约定 |
| `wiki/WORKFLOWS.md` | `<target>/wiki/WORKFLOWS.md` | ingest / query / lint / 迁移流程 |

### 入口与日志（bootstrap != skip 时渲染）

| 模板 | 写入位置 | 用途 |
|---|---|---|
| `wiki/INDEX.md` | `<target>/wiki/INDEX.md` | wiki 顶层入口（仿 Karpathy index.md） |
| `wiki/log.md` | `<target>/wiki/log.md` | 操作日志（grep-friendly） |

### 7 类目录索引（bootstrap != skip 时渲染）

| 模板 | 写入位置 |
|---|---|
| `wiki/concepts/INDEX.md` | `<target>/wiki/concepts/INDEX.md` |
| `wiki/people/INDEX.md` | `<target>/wiki/people/INDEX.md` |
| `wiki/topics/INDEX.md` | `<target>/wiki/topics/INDEX.md` |
| `wiki/frameworks/INDEX.md` | `<target>/wiki/frameworks/INDEX.md` |
| `wiki/tools/INDEX.md` | `<target>/wiki/tools/INDEX.md` |
| `wiki/connections/INDEX.md` | `<target>/wiki/connections/INDEX.md` |
| `wiki/hubs/INDEX.md` | `<target>/wiki/hubs/INDEX.md` |

### 原始素材库索引（bootstrap != skip 时渲染）

| 模板 | 写入位置 |
|---|---|
| `resources/INDEX.md` | `<target>/resources/INDEX.md` |

## 渲染规则

### Schema 文件聚合

CONVENTIONS.md / WORKFLOWS.md 含 `<!-- szw-init:auto-* -->` 标记块。已存在时：

- 标记块**外**内容（用户自定义区）→ 原位保留（红线）
- 标记块**内**内容 → 按 version 比对决定 apply / skip
- 详见 SKILL.md Phase 4

### INDEX.md 不覆盖

INDEX.md 是 ingest 增量维护的产物（每次 ingest 后追加新页）。本 skill **不覆盖**已存在的 INDEX.md，仅创建空 stub。

如需 reset INDEX：手动删除后重跑本 skill。

### 占位符

| 占位符 | 含义 | 来源 |
|---|---|---|
| `<YYYY-MM-DD>` | 渲染日期 | 系统时间 |
| `<INIT_TIMESTAMP>` | `YYYY-MM-DD HH:MM` | 系统时间 |
| `<schema_version>` | schema 版本号 | 模板硬编码 `1.2` |

## 标记块版本

CONVENTIONS.md / WORKFLOWS.md 的标记块章节：

| 文件 | section slugs |
|---|---|
| `CONVENTIONS.md` | `naming` / `frontmatter` / `links` / `tags` / `markdown-style` / `dates` / `special-files` |
| `WORKFLOWS.md` | `ingest` / `query` / `lint` / `special-cases` / `self-check` / `hub-maintenance` / `inbox-migration` |

每个标记块带 `version: <semver>`。schema 演进时升 minor，下次 init 会 diff 出待更新章节。

> v1 当前 CONVENTIONS / WORKFLOWS 模板**还未加标记块包裹**（迁移自 szw-init 的 v2.1 内容）。后续迭代时分章节包裹。

## 迭代方式

- 改章节内容 → 直接编辑模板
- 加新约定 / 工作流 → 加新标记块 + 升 version
- 不需要改 SKILL.md，下次 `/szw-wiki-init [--refresh]` 用新模板
