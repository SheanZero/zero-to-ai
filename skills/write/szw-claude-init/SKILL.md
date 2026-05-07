---
name: szw-claude-init
description: Generate or update CLAUDE.md and AGENTS.md project instructions for the current directory. Auto-detects project type (szw Column / vault / generic / empty), analyzes existing content for project-specific conventions, and renders or aggregates the instruction files using maintained marker blocks. Standalone-usable for any project that needs Claude / Codex project-level guidance, or invoked by /szw-init during column setup. Supports --analyze-only / --force / --no-agents / --target.
---

# szw-claude-init

为当前目录生成或更新 `CLAUDE.md` 和 `AGENTS.md` 项目级指令。

## 何时使用

- **作为 sub-skill 被 `/szw-init` 调用**（首次创建 Column 时）
- **独立使用**（重要场景）：
  - 已有 szw Column 想刷新 CLAUDE.md / AGENTS.md（schema 升级 / 用户改 wiki.enabled）
  - 普通项目想加 Claude Code 项目指令
  - 已有 vault 想加 CLAUDE.md（vault 自身有，但本 skill 可生成 szw 风格的项目指令）
  - 现有 CLAUDE.md / AGENTS.md 想做版本聚合升级

## 何时不用

- 想初始化整个 Column → `/szw-init`（它会调用本 skill）
- 只想配置 vault.path / wiki.enabled → `/szw-config`
- 想初始化 wiki 层 → `/szw-wiki-init`

---

## 调用语法

| 形式 | 行为 |
|---|---|
| `/szw-claude-init` | 默认：扫描 cwd，分析后生成 / 更新 |
| `/szw-claude-init --analyze-only` | 只扫描分析，输出 JSON，不写盘 |
| `/szw-claude-init --force` | 强制覆盖（跳过聚合询问；危险） |
| `/szw-claude-init --target <dir>` | 指定目录（不依赖 cwd） |
| `/szw-claude-init --no-agents` | 只生成 CLAUDE.md，跳过 AGENTS.md |
| `/szw-claude-init --skip-existing` | 已存在的目标文件保持不动 |

---

## 执行流程（4 phase）

### Phase 0：上下文检测（脚本）

```bash
python3 scripts/analyze-context.py [--target <dir>] [--include-existing-content]
```

输出 JSON 关键字段：

- `project_type`: `szw-column` / `vault` / `generic` / `docs-only` / `empty` / `unknown`
- `has_zero_config` / `config_summary.{wiki_enabled, schema_version, writing_lang, vault_path_configured}`
- `vault_path`（仅 szw-column 且配置了 local config）
- `existing_files.{claude_md, agents_md, wiki_dir, resources_dir, ...}`
- `existing_markers.{claude_md, agents_md}` —— 标记块清单（含 section + version）
- `directory_layout` —— 顶层目录列表
- `warnings`

收到 JSON 后，AI 在主对话做 Phase 1。

### Phase 1：AI 分析（决定渲染策略）

读 JSON 决定：

#### 1.1 选 flavor

| project_type | flavor | 模板取舍 |
|---|---|---|
| `szw-column` | `szw-flavor`（默认） | 含全部章节（按 wiki/vault 条件） |
| `vault` | `szw-flavor` + 用户提示 | "目标看起来是 vault；用 szw 模板可能不准确，要继续吗？" |
| `generic` | `szw-flavor` + 警告 | 大多数 szw 章节不适用；建议先 `/szw-init` 把目录初始化为 Column |
| `docs-only` | `szw-flavor` + 警告 | 同上 |
| `empty` | 阻断 | 提示先 `/szw-init` |
| `unknown` | 询问 | 让用户选 flavor |

v1 仅支持 `szw-flavor`。`generic-flavor` 留 v2。

#### 1.2 决定章节包含（条件块求值）

模板里的条件块（`<!-- IF wiki.enabled -->...<!-- ENDIF -->` / `<!-- IF vault.path -->...<!-- ENDIF -->`）按这两个值决定是否渲染：

| 条件 | 求值依据 |
|---|---|
| `wiki.enabled` | `config_summary.wiki_enabled` 为 `true` |
| `vault.path` | `vault_path` 非空 |

#### 1.3 提取已有内容（如果 `existing_files.claude_md` 或 `existing_files.agents_md`）

跑 Phase 0 时加 `--include-existing-content` 拿：
- 标记块外的 `preserved_user_content.{claude_md, agents_md}` —— 用户自定义区，原位保留
- 标记块内的 `existing_section_content.{claude_md, agents_md}` —— 现有 section 内容

为 Phase 3 聚合做准备。

#### 1.4 决定占位符值

| 占位符 | 值来源 |
|---|---|
| `<column_name>` | `column_name`（cwd basename） |
| `<YYYY-MM-DD>` | 今天日期 |
| `<VAULT_PATH>` | `vault_path` |
| `<schema_version>` | 默认 `1.2`（与本 skill 同版本） |

### Phase 2：AI 渲染（生成候选）

读模板：

- [`templates/CLAUDE.md`](./templates/CLAUDE.md)
- [`templates/AGENTS.md`](./templates/AGENTS.md)（除非 `--no-agents`）

按 Phase 1 决策：
- 处理条件块（`<!-- IF X -->...<!-- ENDIF -->` 保留 / 删除）
- 替换占位符
- 升级 `schema_version` 到当前

输出**候选**文本，未写盘。

### Phase 3：聚合（仅当 existing 文件存在）

对 CLAUDE.md / AGENTS.md 各自跑：

```
1. 收集 existing_markers 的 (section, version)
2. 对每个 section：
   - 旧版无该 section（schema 升级带来新章节）→ ADD（默认应用，可单独跳过）
   - 新版无该 section（章节已废弃）→ REMOVE（询问用户）
   - version 相同：
     - existing content == 新候选内容 → SKIP
     - existing != 新候选 → CHANGED-USER-EDITED；询问用户：
        [a] 保留我的版本（init 跳过此 section）
        [b] 应用 init 新版（覆盖修改）
        [c] 显示 diff 后再选
   - version 旧（schema 升级）→ UPGRADE（默认应用，可单独跳过）
3. 用户决策汇总后构造最终内容
4. 标记块外内容（preserved_user_content）原位插回
```

`--force` 跳过 Phase 3 询问，所有 section 直接覆盖（仍保留标记块外内容）。

### Phase 4：写盘

对每个目标文件：
- 写 `<target>/CLAUDE.md` / `<target>/AGENTS.md`
- 报告写了哪些 section / 哪些被跳过 / 哪些用户区被保留

---

## 输出格式

```
✅ szw-claude-init done at: <target>

CLAUDE.md:
  - Status: created | updated | unchanged
  - Sections: 9 written, 0 skipped (user-edited), 0 added, 0 removed
  - User content preserved: <chars>

AGENTS.md:
  - Status: created
  - Sections: 9 written

Project type: szw-column
Wiki enabled: true
Vault configured: true (local)

👉 Next:
  - Run /szw-help to see available commands
  - Edit user-customization area at end of CLAUDE.md / AGENTS.md for project-specific rules
```

如有用户决策跳过的 section：

```
⚠️ 1 section was kept (user-edited):
  - red-lines (CLAUDE.md): user version retained, init upgrade skipped
    To apply init version later, run: /szw-claude-init --force
```

---

## 退出码

| 码 | 含义 | 应对 |
|---|---|---|
| 0 | 成功（含 `--analyze-only`） | — |
| 1 | 目标目录不存在 / 无权限 | 检查 `--target` |
| 2 | 目标是空目录 + 不是 szw Column | 提示先 `/szw-init` |
| 3 | 用户中止聚合（保留现状） | 不视为错误；不写盘 |
| 4 | 目标 frontmatter / 标记块解析失败 | 修目标文件后重跑 |
| 5 | 模板缺失 | 重装 skill |

---

## Gates

| 类型 | 触发 | 处理 |
|---|---|---|
| **Pre-flight** | 目标目录可读写 | 否则 exit 1 |
| **Empty + non-column** | `project_type=empty` | 提示先 `/szw-init` |
| **schema downgrade** | existing version > 当前版本 | 警告 + 询问"是否 downgrade（不推荐）/ 跳过" |
| **Force overwrite** | `--force` 时 | 仍保留标记块外用户内容（红线） |

---

## 设计原则

1. **AI 分析 / 脚本扫描**：脚本只做静态扫描（文件存在性、frontmatter、标记块），AI 在主对话做语义判断
2. **Phase 0 输出 JSON**：决定 flavor / 章节 / 占位符的所有依据集中在一份 JSON
3. **聚合永远保留用户区**：标记块外内容是红线
4. **支持独立使用**：不依赖 `.zero/szw-config.json`；无 config 时降级处理（不渲染需要 wiki/vault 配置的章节）
5. **schema_version 显式记账**：每个 section 带 version，schema 演进可平滑
6. **不修改 vault**：本 skill 只读 `vault_path`，不写

---

## 子 agent 调用

当聚合需要 `merge by AI`（用户选 [c] 显示 diff + 智能合并）时，可调子 agent：

| Agent | 角色 | Marker | 跑在 |
|---|---|---|---|
| `instructions-aggregator` | 解析标记块 + 渲染候选 + 用户决策 | `## AGGREGATION READY` | Claude |
| `instructions-merger` | 用户选 [c] 时智能合并新旧 section | `## MERGE PROPOSAL READY` | Claude（或 Codex，看 config 路由） |

v1 主对话承担即可，子 agent 是 v2 的拆分点。

---

## 与 /szw-init 的集成

`/szw-init` 在 Mode A 完成基础生成（COLUMN.md / EDITORIAL_CONTEXT.md / ADR / 目录骨架）后，**调用本 skill**：

```
[szw-init Mode A]
  ↓ 完成 COLUMN.md / EDITORIAL_CONTEXT / ADR / 目录骨架 / STATE.md / szw-config.json
  ↓ 询问 1（启用 wiki？）+ 询问 2（bootstrap）
  ↓ 调用 /szw-claude-init（自动跑，不再询问）
  ↓ [可选] 调用 /szw-wiki-init（如果启用 wiki）
[szw-init COMPLETE]
```

`/szw-init` 调用时通过环境变量 / CLI 参数传入：
- `--target <cwd>`
- 不需要传 wiki / vault 配置（本 skill 自己读 szw-config.json）

---

## 模板

详见 [`templates/`](./templates/)：

- `CLAUDE.md` —— Claude Code 项目指令模板（9 标记块 + 条件块）
- `AGENTS.md` —— Codex 项目指令模板（含 §5.4 Codex 子 agent 角色段）
- `README.md` —— 模板使用说明

---

## 不实现的事

- **不修改用户自定义区内容**（红线）
- **不创建任何目录 / 子文件**（仅写两个 .md）
- **不修改 szw-config.json**（那是 `/szw-config` 的事）
- **不调用其他 sub-skill**（被 `/szw-init` / `/szw-wiki-init` 调用，不反向依赖）
- **不访问 vault**（仅读 vault.path 字符串作为模板占位符）
- **不 git commit**

---

## 完成 marker

```
## CLAUDE INIT COMPLETE
- Target: <abs path>
- Project type: <type>
- Files written: CLAUDE.md, AGENTS.md
- Sections written: <count>
- Sections preserved (user-edited): <count>
- User content preserved: <chars>
```

失败时：

```
## CLAUDE INIT BLOCKED
- Reason: <原因>
- Suggestion: <下一步>
```

中止聚合时：

```
## CLAUDE INIT DEFERRED
- All existing sections preserved per user request
- Target unchanged
- To re-attempt: /szw-claude-init [--force]
```
