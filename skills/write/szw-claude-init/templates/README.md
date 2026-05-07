# szw-claude-init Templates

`CLAUDE.md` 与 `AGENTS.md` 的项目指令模板，由 [`SKILL.md`](../SKILL.md) 在 Phase 2 渲染。

## 文件清单

| 模板 | 写入位置 | 用途 |
|---|---|---|
| `CLAUDE.md` | `<target>/CLAUDE.md` | Claude Code 项目级指令（9 章节 + 标记块 + 条件块） |
| `AGENTS.md` | `<target>/AGENTS.md` | Codex 项目级指令（含 §5.4 Codex 子 agent 角色段） |

## 标记块约定

模板用 HTML 注释包裹"机器维护区"：

```markdown
<!-- szw-init:auto-start [section: red-lines, version: 1.2] -->
## 4. 红线
...
<!-- szw-init:auto-end [section: red-lines] -->
```

- `section` slug：稳定标识，不要改名（改名等于"删旧 + 加新"）
- `version` semver：每次 schema 演进升 minor（如 `1.2` → `1.3`）
- 标记块**外**的内容是用户自定义区，由 `/szw-claude-init` Phase 3 聚合时**原位保留**

当前 9 个 section（CLAUDE.md / AGENTS.md 共用 slug，章节内容按 flavor 不同）：

1. `project-role`
2. `directory-layout`
3. `core-abstractions`
4. `red-lines`
5. `skill-routing`
6. `source-flow`（仅 wiki.enabled）
7. `vault-boundary`（仅 vault.path 已配置）
8. `style-prefs`
9. `startup-check`

AGENTS.md 额外有 `codex-roles` section（在 skill-routing 内 §5.4）。

## 条件块约定

```markdown
<!-- IF wiki.enabled -->
（仅 wiki.enabled=true 时渲染）
<!-- ENDIF -->

<!-- IF vault.path -->
（仅 vault.path 已配置时渲染）
<!-- ENDIF -->
```

`/szw-claude-init` Phase 1 决定每个条件的求值，Phase 2 渲染时按此保留 / 删除。

## 占位符约定

模板里 `<...>` 是待填字段：

| 占位符 | 含义 | 来源 |
|---|---|---|
| `<column_name>` | 专栏名（cwd basename） | `analyze-context.py` 的 `column_name` |
| `<YYYY-MM-DD>` | 渲染日期 | 系统时间 |
| `<VAULT_PATH>` | vault 绝对路径 | `analyze-context.py` 的 `vault_path` |
| `<schema_version>` | schema 版本号 | 模板硬编码（与本 skill 同版本） |

未填的占位符**不要**留 angle bracket，要换成实际值或合理空白（如"未配置"）。

## 迭代方式

- 改章节内容 → 直接编辑模板
- schema 演进 → 升 `version`（让聚合机制识别为"待更新"）
- 加新章节 → 加新标记块 + 升 `schema_version`
- 删章节 → 标记块整段删（聚合会把现有此 section 标 REMOVE，询问用户确认）

不需要改 SKILL.md，下次 `/szw-claude-init` 自动用新模板。

## flavor 扩展（v2）

当前仅支持 `szw-flavor`。未来可加 `templates/generic-flavor/` 给非 szw 项目用：

```
templates/
├── szw-flavor/        ← v1 默认（即当前 templates/CLAUDE.md / AGENTS.md）
│   ├── CLAUDE.md
│   └── AGENTS.md
└── generic-flavor/    ← v2 通用项目（无 wiki / 无 article 流水线）
    ├── CLAUDE.md
    └── AGENTS.md
```

v1 时 `templates/CLAUDE.md` 与 `templates/AGENTS.md` 直接当 szw-flavor 用。
