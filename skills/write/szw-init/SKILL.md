---
name: szw-init
description: Initialize a new technical writing column from scratch. Auto-detects two modes — empty directory (full construction with deep questioning) or existing directory (review-then-construct). Generates COLUMN.md, EDITORIAL_CONTEXT.md, ADRs, base directory skeleton, STATE.md, and szw-config.json automatically. Orchestrates two sub-skills — /szw-claude-init for CLAUDE.md + AGENTS.md, and /szw-wiki-init for the optional wiki layer. Use once when starting a new column.
---

# szw-init

初始化一个技术写作专栏。本 skill 是 **orchestrator**——它生成基础资产（COLUMN / EDITORIAL_CONTEXT / ADR / STATE / szw-config / 目录骨架），然后调用两个 sub-skill：

- `/szw-claude-init` —— 生成 / 更新 CLAUDE.md + AGENTS.md
- `/szw-wiki-init` —— 启用 wiki 时建 wiki 层（resources / assets / wiki/{7 类}）

两种模式：

- **Mode A**（空目录）：深度问答构造 → 全新生成所有长期资产
- **Mode B**（已有文件）：扫描现有内容 → 反推定位 → 用户确认后生成；schema 文件走聚合（由 sub-skill 处理）

## 何时使用

- 用户表达"我要开个技术专栏"/"建立写作系统"/"把这些散稿整合成专栏"
- 当前路径下没有 `.zero/` 目录
- 已有 Column 想做 schema 升级（走 Mode B + sub-skill 聚合）

## 何时不用

- `.zero/` 已存在且不需要 schema 升级 → `/szw-progress` 或 `/szw-resume`
- 只想刷新 CLAUDE.md / AGENTS.md → `/szw-claude-init`（直接调，跳过 base 资产）
- 只想加 wiki 层 → `/szw-wiki-init`（直接调）
- 目标是 vault / 知识库 / 非写作项目

---

## Step 0 — 检测模式

扫描当前工作目录（cwd 即 Column 根；v1.0 不支持多 Column）：

| 检测信号 | 模式 |
|---|---|
| 空目录或仅含 `.git` / `.DS_Store` | **Mode A**（空目录构造） |
| 含 `*.md` / `*.txt` 等文件，但无 `.zero/` | **Mode B**（已有文件） |
| 已有 `.zero/szw-config.json` | **Mode B-reinit**（schema 升级） |

---

## Mode A — 空目录全新构造

### A.1 深度问答（一次问一个）

按顺序提问，每个问题给一个候选答案让用户接受 / 修改：

1. **专栏定位**：你的专栏要解决什么问题？谁会读？
2. **目标读者**：实操程序员 / 技术 lead / 工程经理 / 独立开发者，主次怎么排？
3. **文章类型偏好**：industry-analysis / programmer-advice / product-analysis / tech-blog 各占多少？
4. **写作语言**：纯中文 / 纯英文 / 中英混排（推荐：技术术语保留英文）
5. **已有术语**：是否有反复用的概念词需要锁定（如 Agentic Coding / AI Agent）？

### A.2 询问：是否启用 wiki 层？

```
是否为本专栏启用 wiki 层？

  [推荐] 写技术专栏用 wiki 层做素材积累，让证据银行复利、防止术语漂移
  [跳过] 短文 / 灵感型博客可不要

  [Y/n]:
```

记下答案 `wiki_enabled = true | false`。具体 bootstrap 方式（seed / empty / skip）由 sub-skill `/szw-wiki-init` 自己问，本 skill 不深入。

### A.3 起草 `COLUMN.md` / `EDITORIAL_CONTEXT.md` / `ROADMAP.md`

按 [`templates/COLUMN.md`](./templates/COLUMN.md) / [`templates/EDITORIAL_CONTEXT.md`](./templates/EDITORIAL_CONTEXT.md) / [`templates/ROADMAP.md`](./templates/ROADMAP.md) 渲染。

### A.4 询问是否建 3 条核心 ADR

默认建议（用户可改 / 跳）：
- `0001-no-benchmark-dumping.md`
- `0002-tool-review-needs-action.md`
- `0003-no-anxiety-farming.md`

模板见 [`templates/adrs/`](./templates/adrs/)。

### A.5 创建基础目录骨架

```bash
bash scripts/create-skeleton.sh [target_dir]
```

只建 fan.md §9 基础 13 个目录（`published/` / `articles/` / `editorial-adr/` / `glossary/` / `inbox/{pending,done}/` / `series/` / `summaries/` / `.zero/{evidence,audits,writing-history}/`）。

不建 wiki 层目录——那是 `/szw-wiki-init` 的事。

### A.6 写 `.zero/STATE.md` 与 `.zero/szw-config.json` 与 `.gitignore`

按模板渲染：
- [`templates/STATE.md`](./templates/STATE.md) → `<cwd>/.zero/STATE.md`
- [`templates/szw-config.json`](./templates/szw-config.json) → `<cwd>/.zero/szw-config.json`
- [`templates/.gitignore`](./templates/.gitignore) → `<cwd>/.gitignore`
- [`templates/szw-config.local.json.example`](./templates/szw-config.local.json.example) → 仅作 example 保留（不直接写入 `.zero/`）

`szw-config.json` 中 `wiki.enabled` 按 A.2 答案设；其他字段用模板默认。

### A.7 调用 `/szw-claude-init`

base 资产就绪后，调用 sub-skill 生成 CLAUDE.md + AGENTS.md：

```
调用 /szw-claude-init

参数（隐式从当前 cwd 读取）：
  - target: <cwd>
  - 自动从 .zero/szw-config.json 读 wiki.enabled / vault.path
  - 渲染条件块（IF wiki.enabled / IF vault.path）

预期产出：
  - <cwd>/CLAUDE.md
  - <cwd>/AGENTS.md
```

`/szw-claude-init` 在子 session 跑完后输出 `## CLAUDE INIT COMPLETE`，主 session 继续。

### A.8 启用 wiki 时调用 `/szw-wiki-init`

如 A.2 用户选 yes：

```
调用 /szw-wiki-init

参数：
  - target: <cwd>
  - 让 sub-skill 自己询问 bootstrap 方式（seed-from-vault / empty-skeleton / skip）

预期产出：
  - <cwd>/wiki/{7 类}/
  - <cwd>/resources/ + assets/ + inbox/sources/
  - <cwd>/.zero/wiki-cache/
  - <cwd>/wiki/{CONVENTIONS, WORKFLOWS, INDEX, log}.md
  - <cwd>/wiki/<type>/INDEX.md (×7)
  - <cwd>/resources/INDEX.md
  - 修改 .zero/szw-config.json: wiki.enabled = true（确认）
  - [若选 seed] .zero/szw-config.local.json: vault.path
```

`/szw-wiki-init` 跑完后输出 `## WIKI INIT COMPLETE`。

### A.9 报告

```
## COLUMN INIT COMPLETE
- Path: <abs path>
- Mode: A
- Base assets: 7 files (COLUMN / EDITORIAL_CONTEXT / ROADMAP / 3 ADRs / STATE / szw-config + .gitignore)
- Wiki enabled: <true | false>
  [若 true] Wiki bootstrap: <empty | seed | skip>
- Sub-skills called: szw-claude-init [, szw-wiki-init]
- Next: /szw-new-article
  [若 wiki + seed] 或 /szw-wiki-import --full
  [若 wiki + empty] 或 /szw-wiki-ingest --from-inbox（待 inbox 有素材后）
```

---

## Mode B — 已有文件 review-then-construct

### B.1 扫描现有内容

- 列出所有 `*.md` / `*.txt`（跳过 `.git` / `node_modules` / `*.DS_Store`）
- 按主题聚类（关键词 / 反复出现的概念）
- 区分：已发布文章 / 草稿 / 散落笔记
- 提取信号：反复主题 / 已用术语 / 受众线索 / 反复观点 / 写作风格

### B.2 检测现有 schema 文件

| 检测项 | 行为 |
|---|---|
| `CLAUDE.md` / `AGENTS.md` 已存在 | 标记给 `/szw-claude-init` 走聚合 |
| `wiki/CONVENTIONS.md` / `wiki/WORKFLOWS.md` 已存在 | 标记给 `/szw-wiki-init --refresh` 走聚合 |
| `.zero/szw-config.json` 已存在 | 校验 + 询问是否补缺字段；不强制覆盖 |
| `wiki/` 已存在 | 询问是否调 `/szw-wiki-init --schema-only` 刷新 |

### B.3 起草 + 用户确认

逐节展示建议，每节询问 ✅ 接受 / ✏️ 修改 / ⏭️ 跳过。可多轮迭代。

### B.4 整合已有文件

询问用户：
- **整合到 `articles/archived/<slug>/`**（推荐）
- **保持原位**

### B.5 调用 sub-skill 处理 schema 文件

聚合机制由 sub-skill 自身实现（详见 `/szw-claude-init` Phase 3 / `/szw-wiki-init` Phase 4），本 skill 只决定何时调用：

- 调 `/szw-claude-init`
  - 已存在 CLAUDE.md / AGENTS.md → sub-skill 解析标记块 → 用户决策
  - 不存在 → sub-skill 直接渲染
- （如 wiki 启用）调 `/szw-wiki-init [--refresh]`
  - 已存在 wiki/ → sub-skill 走 `--schema-only` 聚合
  - 不存在 → sub-skill 走完整流程

### B.6 创建目录骨架（同 A.5，仅缺失部分）

`scripts/create-skeleton.sh` 检测到 `.zero/` 已存在会报 exit 2；Mode B-reinit 跳过这步或手动 `mkdir -p` 缺失的子目录。

### B.7 写 STATE.md / szw-config.json（同 A.6，但若已存在则补缺字段）

---

## 目录骨架

**用脚本一次性创建**：

```bash
bash skills/write/szw-init/scripts/create-skeleton.sh [target_dir]
```

详见 [`scripts/create-skeleton.sh`](./scripts/create-skeleton.sh)。

退出码：

| 码 | 含义 |
|---|---|
| 0 | 成功 |
| 1 | 参数错（目标不存在） |
| 2 | 目标已存在 `.zero/`（拒绝覆盖） |
| 3 | 目标不可写 |

**wiki 层目录**由 [`/szw-wiki-init`](../szw-wiki-init/) 通过其内部脚本 `init-wiki-layer.sh` 创建。

---

## Gates

| 类型 | 触发 | 处理 |
|---|---|---|
| **Pre-flight** | `.zero/` 已存在且 `szw-config.json` 完整 | 进 Mode B-reinit；不删除现有内容 |
| **Sub-skill 失败** | `/szw-claude-init` 或 `/szw-wiki-init` 报错 | 显示子 skill 错误信息，建议修复后重跑 |
| **Abort** | 经 3 轮问答仍无法明确专栏意图 | 中止；建议先做选题探索 |

---

## 输出（向用户报告）

完成后向用户输出：

- 初始化路径：`<cwd>`
- COLUMN.md 一句话定位摘要
- 创建的 ADR 数量与编号
- wiki 启用与否 + bootstrap 方式
- 调用过哪些 sub-skill
- 下一步建议

---

## 完成 marker

```
## COLUMN INIT COMPLETE
- Path: <abs path>
- Mode: A | B | B-reinit
- Wiki enabled: true | false
- Sub-skills invoked:
  - /szw-claude-init: <CLAUDE INIT COMPLETE | DEFERRED | BLOCKED>
  - /szw-wiki-init: <WIKI INIT COMPLETE | not invoked>
- Files created (base): <count>
- ADRs: <编号列表>
- Next: <推荐命令>
```

失败时：

```
## COLUMN INIT BLOCKED
- Reason: <原因>
- Suggestion: <下一步>
```

---

## Templates

模板单独维护在 [`templates/`](./templates/)。本 skill 仅维护**基础资产**模板；CLAUDE / AGENTS / wiki schema 模板在两个 sub-skill 各自的 `templates/`。

| 模板 | 写入目标 | 用途 |
|---|---|---|
| [`templates/COLUMN.md`](./templates/COLUMN.md) | `<cwd>/COLUMN.md` | 专栏定位 |
| [`templates/EDITORIAL_CONTEXT.md`](./templates/EDITORIAL_CONTEXT.md) | `<cwd>/EDITORIAL_CONTEXT.md` | 写作宪法 |
| [`templates/ROADMAP.md`](./templates/ROADMAP.md) | `<cwd>/ROADMAP.md` | 选题列表（空 stub） |
| [`templates/.gitignore`](./templates/.gitignore) | `<cwd>/.gitignore` | git 忽略 local config / pause / 增量历史 |
| [`templates/STATE.md`](./templates/STATE.md) | `<cwd>/.zero/STATE.md` | 活记忆 |
| [`templates/szw-config.json`](./templates/szw-config.json) | `<cwd>/.zero/szw-config.json` | 工作流配置 |
| [`templates/szw-config.local.json.example`](./templates/szw-config.local.json.example) | （example 文件） | 本机特定 config 示例 |
| [`templates/ADR.md`](./templates/ADR.md) | （脚手架） | 通用 ADR 骨架 |
| [`templates/adrs/0001-*.md`](./templates/adrs/) | `<cwd>/editorial-adr/0001-*.md` | 默认 ADR：不做 benchmark 搬运 |
| [`templates/adrs/0002-*.md`](./templates/adrs/) | `<cwd>/editorial-adr/0002-*.md` | 默认 ADR：工具评测要落到行动 |
| [`templates/adrs/0003-*.md`](./templates/adrs/) | `<cwd>/editorial-adr/0003-*.md` | 默认 ADR：不制造职业焦虑 |

由 sub-skill 维护的模板（不在本目录）：

| 模板 | 维护者 |
|---|---|
| `CLAUDE.md` / `AGENTS.md` | [`/szw-claude-init/templates/`](../szw-claude-init/templates/) |
| `wiki/CONVENTIONS.md` / `WORKFLOWS.md` / `INDEX.md` / `log.md` | [`/szw-wiki-init/templates/wiki/`](../szw-wiki-init/templates/wiki/) |
| `wiki/{7 类}/INDEX.md` | 同上 |
| `resources/INDEX.md` | [`/szw-wiki-init/templates/resources/`](../szw-wiki-init/templates/resources/) |

---

## 设计原则

1. **Orchestrator + sub-skills 分层**：本 skill 负责"高层决策 + base 资产"，schema 文件细节交 sub-skills
2. **不假设环境**：可在任意空 / 非空目录跑；自动检测模式
3. **可恢复**：每一步问答后立即写文件
4. **不破坏已有内容**：Mode B 永远先扫描 + 提议；schema 文件聚合走 sub-skill
5. **薄 wrapper 风格**：详细工作流在 sub-skill SKILL.md，本 skill 只做协调
6. **wiki 可选**：A.2 选 No 时整个 wiki 流程跳过；CLAUDE.md / AGENTS.md 仍生成（不含 wiki 章节）

---

## 子 agent 调用

| 子 agent | Mode | 用途 | Completion marker |
|---|---|---|---|
| `column-positioner` | A | 起草 COLUMN.md / EDITORIAL_CONTEXT 初版 | `## POSITIONING DRAFTED` |
| `column-reviewer` | B | 扫描已有文件 → 反推定位 / 风格 / 术语 | `## REVIEW COMPLETE` |

聚合不在本 skill 处理（移到 sub-skills）。

---

## Sub-skill 调用关系

```
/szw-init
  ├─→ A.7  /szw-claude-init  (始终调)
  └─→ A.8  /szw-wiki-init    (仅 wiki.enabled=true 时调)

调用方式：通过 SKILL 系统直接 invoke，子 session 跑完后主 session 继续。
返回值：通过 ## *_COMPLETE marker 通信。
```

也可以**绕过 init 单独使用 sub-skills**：

- 已有 Column 想刷 CLAUDE.md：直接 `/szw-claude-init`
- 已有 Column 想加 wiki 层：直接 `/szw-wiki-init`
- 普通项目想加 Claude 指令：直接 `/szw-claude-init`（会用 generic 或 szw-flavor 视用户决定）

---

## 失败处理

| 退出码 | 含义 | 应对 |
|---|---|---|
| `0` | 成功 | — |
| `1` | 不在合法目录 / 参数错 | 检查 cwd 与参数 |
| `2` | 目标已存在 `.zero/` 且不是 re-init | 用 `/szw-progress` 看现状 |
| `3` | 目录不可写 | 检查权限 |
| `4` | 用户中止（3 轮问答仍未明确） | 建议先做选题探索 |
| `5` | sub-skill 失败 | 看 sub-skill 错误信息修复 |

---

## 与其他命令的关系

- **下游**：
  - `/szw-claude-init`（始终调用）
  - `/szw-wiki-init`（启用 wiki 时调用）
  - `/szw-new-article`（init 完成后第一篇文章）
- **后续维护**：`/szw-context` / `/szw-adr` / `/szw-config` / `/szw-glossary`
- **wiki 维护**（启用 wiki 时）：`/szw-wiki-import` / `/szw-wiki-ingest` / `/szw-wiki-query` / `/szw-wiki-lint`
- **永远不调用**：vault 自身的 ingest/lint（避免双 owner）

---

## 不实现的事

- **不直接编辑用户已有正文文件**（除整合到 articles/archived/）
- **不渲染 CLAUDE.md / AGENTS.md**（交 `/szw-claude-init`）
- **不建 wiki 层目录或 schema 文件**（交 `/szw-wiki-init`）
- **不在 Mode B-reinit 自动跑 wiki-import**（提示用户后由用户决定）
- **不修改 vault 任何文件**
- **不创建多 Column 容器**（v1.0 假设 cwd 即 Column）
- **不 git commit**
