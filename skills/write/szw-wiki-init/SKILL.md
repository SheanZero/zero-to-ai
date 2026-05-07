---
name: szw-wiki-init
description: Initialize the LLM wiki layer in a szw Column — build wiki/{7 category}/ + resources/ + assets/ + inbox/sources/ + .zero/wiki-cache/ directory subtree, render schema files (CONVENTIONS.md / WORKFLOWS.md / INDEX.md / log.md / 7 category INDEX.md / resources/INDEX.md), and set wiki.enabled=true in szw-config.json. Supports three bootstrap modes (seed-from-vault / empty-skeleton / skip-schema-only). Standalone-usable to add wiki layer to existing Column, or invoked by /szw-init when user enables wiki at setup. Aggregates existing schema files via marker blocks.
---

# szw-wiki-init

为已有 szw Column 初始化 LLM wiki 层（仿 [Karpathy LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) 模式）。

## 何时使用

- **作为 sub-skill 被 `/szw-init` 调用**（用户在 init 时选启用 wiki）
- **独立使用**：
  - 已有 szw Column 想新加 wiki 层
  - 已有 wiki schema 文件想 refresh / 升版（如 schema_version 1.1 → 1.2）
  - 想从 vault re-seed wiki

## 何时不用

- Column 还未初始化 → 先 `/szw-init`
- 只想做 import → `/szw-wiki-import`
- 只想 ingest 单素材 → `/szw-wiki-ingest`
- 只想生成 CLAUDE.md / AGENTS.md → `/szw-claude-init`

---

## 调用语法

| 形式 | 行为 |
|---|---|
| `/szw-wiki-init` | 默认：交互式询问 bootstrap 方式 |
| `/szw-wiki-init --bootstrap empty-skeleton` | 显式选空骨架（推荐默认） |
| `/szw-wiki-init --bootstrap seed-from-vault --vault-path <path>` | 从 vault 全量 seed |
| `/szw-wiki-init --bootstrap skip` | 仅 schema 文件，不建 7 类 INDEX |
| `/szw-wiki-init --analyze-only` | 检测现状，不写盘 |
| `/szw-wiki-init --target <dir>` | 指定目录 |
| `/szw-wiki-init --refresh` | 已有 schema 文件时强制走聚合（默认会询问） |

---

## 执行流程（6 phase）

### Phase 0：Prerequisite 检查

- `<target>/.zero/szw-config.json` 必须存在（否则 exit 4，提示先 `/szw-init`）
- 解析当前 `wiki.enabled` 与 `wiki.schema_version`

复用 [`../szw-claude-init/scripts/analyze-context.py`](../szw-claude-init/scripts/analyze-context.py) 拿到完整上下文。

### Phase 1：AI 询问 bootstrap 方式

仅当未通过 `--bootstrap` 显式指定时询问：

```
wiki 怎么 bootstrap？

  (a) seed from vault    从已有 LLM wiki vault 导入种子
  (b) empty skeleton     建空骨架（7 类目录 + INDEX.md 占位）
  (c) skip schema only   仅 schema 文件（CONVENTIONS / WORKFLOWS），不建 INDEX

  [a/b/c, default: b]:
```

选 (a) 时进 Phase 1.1：

```
请提供 vault 路径（含 1-wiki/ 与 4-resources/ 的目录）：
> _
```

校验：路径存在 + 含 `1-wiki/` 与 `4-resources/`。否则 exit 2。

vault.path 写到 `.zero/szw-config.local.json`（不入 git）。

### Phase 2：建目录

```bash
bash scripts/init-wiki-layer.sh --target <target>
```

幂等创建（已存在的目录保持不动，仅补 `.gitkeep` 到空目录）：

- `inbox/sources/`
- `resources/` + `assets/`
- `wiki/{concepts,people,topics,frameworks,tools,connections,hubs}/`
- `.zero/wiki-cache/`

### Phase 3：渲染 schema 文件

#### 3.1 始终渲染（无论 bootstrap）

| 模板 | 写入目标 |
|---|---|
| [`templates/wiki/CONVENTIONS.md`](./templates/wiki/CONVENTIONS.md) | `<target>/wiki/CONVENTIONS.md` |
| [`templates/wiki/WORKFLOWS.md`](./templates/wiki/WORKFLOWS.md) | `<target>/wiki/WORKFLOWS.md` |

均含 `<!-- szw-init:auto-* -->` 标记块；已存在时走 Phase 4 聚合。

#### 3.2 bootstrap = empty-skeleton 或 seed-from-vault 时额外渲染

| 模板 | 写入目标 |
|---|---|
| [`templates/wiki/INDEX.md`](./templates/wiki/INDEX.md) | `<target>/wiki/INDEX.md` |
| [`templates/wiki/log.md`](./templates/wiki/log.md) | `<target>/wiki/log.md` |
| [`templates/wiki/concepts/INDEX.md`](./templates/wiki/concepts/INDEX.md) | `<target>/wiki/concepts/INDEX.md` |
| [`templates/wiki/people/INDEX.md`](./templates/wiki/people/INDEX.md) | `<target>/wiki/people/INDEX.md` |
| [`templates/wiki/topics/INDEX.md`](./templates/wiki/topics/INDEX.md) | `<target>/wiki/topics/INDEX.md` |
| [`templates/wiki/frameworks/INDEX.md`](./templates/wiki/frameworks/INDEX.md) | `<target>/wiki/frameworks/INDEX.md` |
| [`templates/wiki/tools/INDEX.md`](./templates/wiki/tools/INDEX.md) | `<target>/wiki/tools/INDEX.md` |
| [`templates/wiki/connections/INDEX.md`](./templates/wiki/connections/INDEX.md) | `<target>/wiki/connections/INDEX.md` |
| [`templates/wiki/hubs/INDEX.md`](./templates/wiki/hubs/INDEX.md) | `<target>/wiki/hubs/INDEX.md` |
| [`templates/resources/INDEX.md`](./templates/resources/INDEX.md) | `<target>/resources/INDEX.md` |

INDEX.md 文件**已存在时不动**（不像 schema 文件走聚合；INDEX 是 ingest 增量维护，不应被 init 覆盖）。

#### 3.3 占位符替换

| 占位符 | 值 |
|---|---|
| `<YYYY-MM-DD>` | 今天 |
| `<INIT_TIMESTAMP>` | `YYYY-MM-DD HH:MM` |
| `<schema_version>` | `1.2` |

### Phase 4：聚合现有 schema 文件

仅 `wiki/CONVENTIONS.md` 与 `wiki/WORKFLOWS.md` 走聚合（INDEX 文件按 §3.2 规则不动）。

机制与 `/szw-claude-init` Phase 3 一致——标记块 diff + 用户决策（apply / skip / show diff）。

### Phase 5：更新 szw-config.json

修改 `<target>/.zero/szw-config.json`：

```json
{
  "wiki": {
    "enabled": true,
    "schema_version": "1.2",
    ...其他字段保持不变...
  }
}
```

如选 (a) seed → 同时写 `<target>/.zero/szw-config.local.json`：

```json
{
  "vault": {
    "path": "<USER_PROVIDED_VAULT_PATH>"
  }
}
```

### Phase 6：报告 + 提示下一步

```
✅ Wiki layer initialized at: <target>

Bootstrap: empty-skeleton | seed-from-vault | skip
Schema files written:
  - wiki/CONVENTIONS.md (created | updated | aggregated)
  - wiki/WORKFLOWS.md (created | updated | aggregated)

Index files (bootstrap != skip):
  - wiki/INDEX.md, log.md
  - wiki/{concepts,people,topics,frameworks,tools,connections,hubs}/INDEX.md
  - resources/INDEX.md

Config updated:
  - .zero/szw-config.json: wiki.enabled = true

Vault seed (only if seed-from-vault):
  - .zero/szw-config.local.json: vault.path = <path>

👉 Next:
  [if seed]    /szw-wiki-import --full   (执行实际 import)
  [if empty]   把素材放到 inbox/sources/ → review 后跑 /szw-wiki-ingest --from-inbox
  [always]     /szw-claude-init           (刷新 CLAUDE.md / AGENTS.md 加 wiki 章节)
```

---

## 退出码

| 码 | 含义 | 应对 |
|---|---|---|
| 0 | 成功（含 `--analyze-only`） | — |
| 1 | 不在 szw Column / 参数错 | 先 `/szw-init` |
| 2 | vault 路径不可达（seed 模式） | 改路径或选 (b) 空骨架 |
| 3 | wiki 已完整初始化（不重复建） | `--refresh` 强制走聚合 |
| 4 | 用户中止聚合 | 不视为错误；schema 文件不动 |
| 5 | 模板缺失 | 重装 skill |
| 6 | szw-config.json 写入失败 | 检查文件权限 + JSON 完整性 |

---

## Gates

| 类型 | 触发 | 处理 |
|---|---|---|
| **Pre-flight** | `<target>/.zero/szw-config.json` 必须存在 | 否则 exit 1 |
| **Vault 可达** | `--bootstrap seed-from-vault` 时 vault.path 必须含 `1-wiki/` 与 `4-resources/` | 否则 exit 2 |
| **不重复 init** | 默认 `wiki.enabled=true` 且 schema 完整 | exit 3，提示 `--refresh` |
| **聚合保护** | schema 文件已存在 → 标记块外用户内容永不动 | 与 claude-init 红线一致 |

---

## 设计原则

1. **职责单一**：仅负责 wiki 层结构与 schema；不动 CLAUDE/AGENTS/COLUMN/EDITORIAL_CONTEXT 等非 wiki 资产
2. **幂等**：可重复跑；已存在的目录与 INDEX 文件保持不动
3. **schema 与 INDEX 区分**：CONVENTIONS / WORKFLOWS 走聚合（机器维护），INDEX 是 ingest 增量产物（不重置）
4. **bootstrap 三选**：seed / empty / skip 让用户控制初始内容
5. **vault 仅作为 seed**：本 skill 完成后由 `/szw-wiki-import` 执行实际 import；本 skill 只配 vault.path
6. **不修改 vault**（红线）

---

## 子 agent 调用

| Agent | 角色 | Marker | 跑在 |
|---|---|---|---|
| `wiki-schema-aggregator` | CONVENTIONS / WORKFLOWS 标记块 diff + 用户决策 | `## WIKI SCHEMA AGGREGATED` | Claude |

v1 主对话承担即可。

---

## 与其他命令的集成

### 上游：`/szw-init`

`/szw-init` 在用户选启用 wiki 时调用本 skill：

```
/szw-init Mode A
  ↓ A.1-A.7 完成基础（COLUMN / EDITORIAL_CONTEXT / ADR / 目录骨架 / STATE / szw-config）
  ↓ 询问 1: 启用 wiki？ → Yes
  ↓ 询问 2: bootstrap 方式
  ↓ 调 /szw-claude-init   → 渲染 CLAUDE.md / AGENTS.md（含 wiki 章节）
  ↓ 调 /szw-wiki-init     → 本 skill：建目录 + 渲染 schema + 写 config
[init COMPLETE]
```

### 下游：`/szw-wiki-import`

如果选了 `seed-from-vault`，本 skill 完成后**提示**用户跑 `/szw-wiki-import --full`（不自动跑，避免长时间阻塞）。

### 关联：`/szw-claude-init`

本 skill 修改了 `wiki.enabled=true` 后，建议用户跑 `/szw-claude-init` 让 CLAUDE.md / AGENTS.md 也加上 wiki 章节（条件块求值会变）。

---

## 模板

详见 [`templates/`](./templates/) 与 [`templates/README.md`](./templates/README.md)：

- `wiki/CONVENTIONS.md` —— 命名 / frontmatter / 链接 / 附件路径约定（含标记块）
- `wiki/WORKFLOWS.md` —— ingest / query / lint / 迁移流程（含标记块）
- `wiki/INDEX.md` / `log.md` —— wiki 层入口与日志
- `wiki/{7 类}/INDEX.md` —— 各分类索引（空 stub）
- `resources/INDEX.md` —— 原始素材库索引

---

## 不实现的事

- **不修改非 wiki 资产**（CLAUDE / AGENTS / COLUMN / EDITORIAL_CONTEXT / ADR / STATE）
- **不执行 vault import**（仅配 vault.path）
- **不创建 wiki 内容页**（那是 `/szw-wiki-ingest` 与 `/szw-wiki-create-page` 的事）
- **不修改 INDEX.md 文件**（已存在时不覆盖；ingest 增量维护）
- **不 git commit**

---

## 完成 marker

```
## WIKI INIT COMPLETE
- Target: <abs path>
- Bootstrap: empty-skeleton | seed-from-vault | skip
- Schema files: 2 (created | updated | aggregated)
- Index files: <count> (created or skipped if exists)
- Config updated: wiki.enabled = true
- Vault path configured: true | false
```

失败时：

```
## WIKI INIT BLOCKED
- Reason: <原因>
- Suggestion: <下一步>
```

中止聚合时：

```
## WIKI INIT DEFERRED
- Schema files preserved per user decision
- Directories created: <count>
- Config updated (wiki.enabled = true): <yes | no>
```
