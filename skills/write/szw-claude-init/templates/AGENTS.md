# <column_name> — Codex 项目指令

> Last updated by /szw-init: <YYYY-MM-DD>
> szw_init_version: 1.2

本文件是 szw Column 给 Codex 的项目级约束。每次 session 自动加载。

> **维护规则**：本文件章节用 `<!-- szw-init:auto-* -->` 标记块包裹。
> - 标记块**内**由 `/szw-init` 维护，re-init 时询问是否更新
> - 标记块**外**（包括文末"用户自定义区"）init 永不动
> - 想加项目特定约束 → 写到文末用户自定义区

<!-- szw-init:auto-start [section: project-role, version: 1.2] -->

## 1. 项目角色

这是一个**技术专栏 Column**，由 [szw 工作流](https://github.com/sheanzero/zero-to-ai) 管理。

<!-- IF wiki.enabled -->
本 Column 同时是 [Karpathy LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) 模式的本地实例：

| Karpathy 三层 | 本 Column 体现 |
|---|---|
| Raw sources | `resources/` + `assets/` |
| Wiki | `wiki/`（含 7 类：concepts / people / topics / frameworks / tools / connections / hubs） |
| Schema | 本文件 + CLAUDE.md + wiki/CONVENTIONS.md + wiki/WORKFLOWS.md |
<!-- ENDIF -->

<!-- szw-init:auto-end [section: project-role] -->

<!-- szw-init:auto-start [section: directory-layout, version: 1.2] -->

## 2. 目录布局速查

```
<column_name>/
├── COLUMN.md                  专栏定位
├── EDITORIAL_CONTEXT.md       写作宪法（走 /szw-context）
├── ROADMAP.md                 选题路线图
├── CLAUDE.md / AGENTS.md      项目指令（本文件）
├── published/                 已发布成品（只走 /szw-publish 写）
├── articles/<slug>/           单篇文章过程
├── editorial-adr/             决策记录（走 /szw-adr）
├── glossary/                  术语长定义（走 /szw-glossary）
├── inbox/
│   ├── pending/               写作灵感
│   ├── done/                  灵感升级 article 后存根
<!-- IF wiki.enabled -->
│   └── sources/               待 review 的外部素材
├── resources/                 raw sources
├── assets/<slug>/             素材附件
├── wiki/                      LLM wiki 综合层
│   └── {concepts,people,topics,frameworks,tools,connections,hubs}/
<!-- ENDIF -->
├── series/ / summaries/
└── .zero/                     系统层
```

<!-- szw-init:auto-end [section: directory-layout] -->

<!-- szw-init:auto-start [section: core-abstractions, version: 1.2] -->

## 3. 核心抽象

| 抽象 | 物理体现 | 生命周期 |
|---|---|---|
| **article** | `articles/<slug>/` | brief → research → outline → write → review → publish → complete |
| **editorial assets** | COLUMN.md / EDITORIAL_CONTEXT.md / editorial-adr/ / glossary/ | 长期演进 |
<!-- IF wiki.enabled -->
| **wiki page** | `wiki/<type>/<slug>.md` | stub → active → mature |
| **resource** | `resources/<YYYY-MM-DD-slug>.md` | inbox → reviewed → ingested |
| **attachment** | `assets/<slug>/...` | 与 resource 同生命周期 |
<!-- ENDIF -->

<!-- szw-init:auto-end [section: core-abstractions] -->

<!-- szw-init:auto-start [section: red-lines, version: 1.2] -->

## 4. 红线（不可越过）

- ❌ `published/` 只走 `/szw-publish` 写
- ❌ `EDITORIAL_CONTEXT.md` 走 `/szw-context`
- ❌ ADR 文件走 `/szw-adr`
<!-- IF wiki.enabled -->
- ❌ 不绕过 resources/ 直接 ingest 到 wiki/
- ❌ inbox/sources/ → resources/ 必经用户 review（read: true）
- ❌ essay 全文不进 wiki/
- ❌ `assets/<slug>/` 中已有附件不删
<!-- ENDIF -->
<!-- IF vault.path -->
- ❌ vault import 操作只读 vault
- ❌ 不调用 vault session 工具
<!-- ENDIF -->

<!-- szw-init:auto-end [section: red-lines] -->

<!-- szw-init:auto-start [section: skill-routing, version: 1.2] -->

## 5. skill 路由速查

### 5.1 文章流水线

| 何时 | 命令 |
|---|---|
| 新文章 | `/szw-new-article` |
| brief | `/szw-discuss <slug>` |
| 证据采集 + 诊断（Codex 主跑） | `/szw-research <slug>` |
| 论证地图 + 拆片 | `/szw-outline <slug>` |
| 起稿 / 润色 | `/szw-write <slug>` |
| 反方审稿（Codex 主跑） | `/szw-review <slug>` |
| 多平台打包 | `/szw-publish <slug>` |
| 复盘 / 终结 | `/szw-retro` / `/szw-complete <slug>` |
| 恢复 / 暂停 | `/szw-resume` / `/szw-pause` |
| 进度 | `/szw-progress` |

<!-- IF wiki.enabled -->

### 5.2 wiki 命令族

| 何时 | 命令 |
|---|---|
| vault → szw seed/refresh | `/szw-wiki-import` |
| inbox 素材入站 | `/szw-wiki-ingest --from-inbox` |
| 单素材 ingest | `/szw-wiki-ingest <resources/file>` |
| 创建 stub wiki 页 | `/szw-wiki-create-page <type> <slug>` |
| 查 wiki | `/szw-wiki-query <q>` |
| 给 article 推荐 | `/szw-wiki-suggest <slug>` |
| 健康检查 | `/szw-wiki-lint` |

<!-- ENDIF -->

### 5.3 长期资产

| 何时 | 命令 |
|---|---|
| 改宪法 / ADR / 术语 | `/szw-context` / `/szw-adr` / `/szw-glossary` |
| 配置 | `/szw-config` |

### 5.4 Codex 子 agent 角色

本 Column 默认在 `.zero/szw-config.json` 中将下列子 agent 路由到 Codex：

- `evidence-researcher`（`/szw-research` Phase 1：证据采集）
- `claim-diagnoser`（`/szw-research` Phase 2：判断诊断）
- `skeptical-reviewer`（`/szw-review` Phase 1：反方审稿）
<!-- IF wiki.enabled -->
- `wiki-merger`（`/szw-wiki-import` 冲突 "merge by AI" 子流程，可选） 
<!-- ENDIF -->

当你（Codex）作为这些子 agent 被调用时：

- 输入由 Claude 主对话给定（含 brief / outline / 上下文 JSON）
- 输出符合 Completion marker 协议（如 `## EVIDENCE COMPLETE` / `## DIAGNOSIS PASSED` / `## REVIEW COMPLETE`）
- 不调用 szw 顶层 skill；只产出本子 agent 应产出的 markdown 段落

<!-- szw-init:auto-end [section: skill-routing] -->

<!-- IF wiki.enabled -->
<!-- szw-init:auto-start [section: source-flow, version: 1.2] -->

## 6. 三段式素材流

```
inbox/sources/<file> (read: false)
   ↓ 用户 review
inbox/sources/<file> (read: true)
   ↓ /szw-wiki-ingest --from-inbox
resources/<YYYY-MM-DD-slug>.md  (assets/<slug>/ 不动)
   ↓ ingest 决策树（wiki/WORKFLOWS.md §一）
wiki/<type>/<slug>.md
```

附件相对路径：

| 文件位置 | 引用路径 |
|---|---|
| `inbox/sources/<file>.md` | `![[../../assets/<slug>/img.jpg]]` |
| `resources/<file>.md` | `![[../assets/<slug>/img.jpg]]` |
| `wiki/<type>/<file>.md` | `![[../../assets/<slug>/img.jpg]]` |

<!-- szw-init:auto-end [section: source-flow] -->
<!-- ENDIF -->

<!-- IF vault.path -->
<!-- szw-init:auto-start [section: vault-boundary, version: 1.2] -->

## 7. 与 vault 的边界

- `vault.path`: `<VAULT_PATH>`（存 `.zero/szw-config.local.json`）
- 仅 `/szw-wiki-import` 期间访问 vault，且**只读**
- vault 的 ingest/lint 由 vault 自己的 session 维护

<!-- szw-init:auto-end [section: vault-boundary] -->
<!-- ENDIF -->

<!-- szw-init:auto-start [section: style-prefs, version: 1.2] -->

## 8. 风格偏好

- 中文优先，技术名词保留英文
- 输出符合 Completion marker 协议（子 agent 角色时）
- 不写不必要注释

<!-- szw-init:auto-end [section: style-prefs] -->

<!-- szw-init:auto-start [section: startup-check, version: 1.2] -->

## 9. 启动检查清单

作为子 agent 被调用时：

1. 确认调用方传入的上下文 JSON 完整
2. 按 SKILL.md 定义的 Completion marker 输出
3. 不修改 articles/ 之外的内容（除非 skill 明确允许）

<!-- szw-init:auto-end [section: startup-check] -->

---

## 用户自定义区

> Codex 项目级特殊约束写这里。`/szw-init` 永不动。

(空)
