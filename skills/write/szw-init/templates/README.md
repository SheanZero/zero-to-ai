# szw-init Templates

szw-init 在执行 Mode A / Mode B 流程时填充并写入 cwd 的**基础资产**模板。

> 本 skill 只维护基础资产；CLAUDE.md / AGENTS.md / wiki schema 文件由两个 sub-skill 各自维护：
> - [`../szw-claude-init/templates/`](../../szw-claude-init/templates/) —— CLAUDE.md / AGENTS.md
> - [`../szw-wiki-init/templates/`](../../szw-wiki-init/templates/) —— wiki / resources schema

## 文件清单

### 始终渲染

| 模板 | 写入位置 | 用途 |
|---|---|---|
| `COLUMN.md` | `<cwd>/COLUMN.md` | 专栏定位（一次写就基本不动） |
| `EDITORIAL_CONTEXT.md` | `<cwd>/EDITORIAL_CONTEXT.md` | 写作宪法（长期演进） |
| `ROADMAP.md` | `<cwd>/ROADMAP.md` | 选题列表（空 stub，由 /szw-capture 填） |
| `.gitignore` | `<cwd>/.gitignore` | git 忽略 local config / pause / 增量历史 |
| `STATE.md` | `<cwd>/.zero/STATE.md` | 活记忆 |
| `szw-config.json` | `<cwd>/.zero/szw-config.json` | 工作流配置 |

### 仅 example（不直接写入）

| 模板 | 用途 |
|---|---|
| `szw-config.local.json.example` | 机器特定 config 示例（用户复制后改名为 `szw-config.local.json`） |

### ADR 模板

| 模板 | 写入位置 | 用途 |
|---|---|---|
| `ADR.md` | （脚手架） | 通用 ADR 骨架 |
| `adrs/0001-no-benchmark-dumping.md` | `<cwd>/editorial-adr/0001-no-benchmark-dumping.md` | 默认 ADR：不做 benchmark 搬运 |
| `adrs/0002-tool-review-needs-action.md` | `<cwd>/editorial-adr/0002-tool-review-needs-action.md` | 默认 ADR：工具评测要落到行动 |
| `adrs/0003-no-anxiety-farming.md` | `<cwd>/editorial-adr/0003-no-anxiety-farming.md` | 默认 ADR：不制造职业焦虑 |

## 已迁走的模板（不在本目录）

| 模板 | 当前位置 | 维护者 |
|---|---|---|
| `CLAUDE.md` | `../../szw-claude-init/templates/CLAUDE.md` | `/szw-claude-init` |
| `AGENTS.md` | `../../szw-claude-init/templates/AGENTS.md` | `/szw-claude-init` |
| `wiki/CONVENTIONS.md` | `../../szw-wiki-init/templates/wiki/CONVENTIONS.md` | `/szw-wiki-init` |
| `wiki/WORKFLOWS.md` | `../../szw-wiki-init/templates/wiki/WORKFLOWS.md` | `/szw-wiki-init` |
| `wiki/INDEX.md` | `../../szw-wiki-init/templates/wiki/INDEX.md` | `/szw-wiki-init` |
| `wiki/log.md` | `../../szw-wiki-init/templates/wiki/log.md` | `/szw-wiki-init` |
| `wiki/{concepts,people,topics,frameworks,tools,connections,hubs}/INDEX.md` | `../../szw-wiki-init/templates/wiki/...` | `/szw-wiki-init` |
| `resources/INDEX.md` | `../../szw-wiki-init/templates/resources/INDEX.md` | `/szw-wiki-init` |

## 占位符约定

模板里的 `<...>` 是占位符，由 SKILL 在执行时替换：

| 占位符 | 含义 | 示例值 |
|---|---|---|
| `<column_name>` | 专栏名（cwd 的 basename） | `Zero` |
| `<YYYY-MM-DD>` | 当前日期 | `2026-05-06` |
| `<vision_one_line>` | 一句话愿景（用户回答） | "解释 AI 编程工具如何重塑程序员工作流" |
| `<positioning_paragraph>` | 一段定位说明 | （根据问答合成） |
| `<primary_audience>` | 主要读者 | "实操程序员、独立开发者" |
| `<NNNN>` | ADR 编号（从 0004 起） | `0004` |
| `<Decision title>` | ADR 标题 | "AI 工具对比优先比 workflow fit" |

替换原则：
- AI 起草内容时，根据用户问答（Mode A）/ 已有内容分析（Mode B）填占位符
- 用户最终确认后再写入磁盘
- 已有 `<...>` 表示"待填"，未填的不要保留 angle bracket

## 与 sub-skill 的协作

```
/szw-init Mode A：
  ↓ 渲染本目录的基础资产模板
  ↓ 调用 /szw-claude-init   → 渲染 CLAUDE.md / AGENTS.md（用其自身 templates/）
  ↓ 启用 wiki 时调 /szw-wiki-init  → 渲染 wiki schema（用其自身 templates/）
```

每个 sub-skill 的模板独立迭代，与本目录解耦。

## 迭代建议

- 改本目录模板（COLUMN / EDITORIAL_CONTEXT / ROADMAP / STATE / szw-config / ADR）→ 直接编辑
- 改 CLAUDE.md / AGENTS.md → 编辑 `../../szw-claude-init/templates/`
- 改 wiki schema → 编辑 `../../szw-wiki-init/templates/wiki/`
- 不需要改 SKILL.md，下次 init / sub-skill 自动用新模板

## ADR 模板与默认 ADR 内容分离

- `ADR.md` —— 通用骨架，未来新建 ADR 时套用
- `adrs/000N-*.md` —— 写好的默认条目，可直接 cp 到 `editorial-adr/`，由 SKILL 替换日期占位符
