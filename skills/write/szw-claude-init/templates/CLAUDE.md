# <column_name> — Claude Code 项目指令

> Last updated by /szw-init: <YYYY-MM-DD>
> szw_init_version: 1.2

本文件是 szw Column 的项目级约束。每次 session 自动加载。

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
| Schema | 本文件 + AGENTS.md + wiki/CONVENTIONS.md + wiki/WORKFLOWS.md |
<!-- ENDIF -->

<!-- szw-init:auto-end [section: project-role] -->

<!-- szw-init:auto-start [section: directory-layout, version: 1.2] -->

## 2. 目录布局速查

```
<column_name>/
├── COLUMN.md                  专栏定位（一次性）
├── EDITORIAL_CONTEXT.md       写作宪法（长期演进；走 /szw-context）
├── ROADMAP.md                 选题路线图（用户管理）
├── CLAUDE.md / AGENTS.md      项目指令（本文件）
├── published/                 已发布成品（只走 /szw-publish 写）
├── articles/<slug>/           单篇文章过程（brief/research/outline/draft/...）
├── editorial-adr/             决策记录（走 /szw-adr）
├── glossary/                  单术语长定义（走 /szw-glossary）
├── inbox/
│   ├── pending/               写作灵感待处理
│   ├── done/                  灵感升级 article 后存根
<!-- IF wiki.enabled -->
│   └── sources/               待 review 的外部素材（read=true 后自动迁移并删除）
├── resources/                 raw sources，wiki ingest 唯一来源
├── assets/<slug>/             素材附件（图片 / PDF）
├── wiki/                      LLM wiki 综合层
│   ├── INDEX.md / log.md
│   ├── CONVENTIONS.md         命名 / frontmatter 约定
│   ├── WORKFLOWS.md           ingest / query / lint 详细流程
│   └── {concepts,people,topics,frameworks,tools,connections,hubs}/
<!-- ENDIF -->
├── series/                    系列连载组织
├── summaries/                 周期汇总
└── .zero/                     系统层（活记忆 / 配置 / 写作历史）
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

不论用户如何要求，下列动作永不执行：

- ❌ `published/` 只走 `/szw-publish` 写，不直接编辑
- ❌ `EDITORIAL_CONTEXT.md` 走 `/szw-context`，不直接编辑
- ❌ ADR 文件走 `/szw-adr`，不手动编号 / 创建
<!-- IF wiki.enabled -->
- ❌ 不绕过 resources/ 直接 ingest 到 wiki/
- ❌ inbox/sources/ → resources/ 必经用户 review（read: true 是显式确认）
- ❌ essay 全文不进 wiki/（仅可提取连接 / 判断到 connections/ 标 derived: true）
- ❌ `assets/<slug>/` 中已有附件不删（除非用户显式删整个 resource）
<!-- ENDIF -->
<!-- IF vault.path -->
- ❌ vault import 操作只读 vault，永不写
- ❌ 不在 szw 内调用 vault session 工具（避免双 owner 冲突）
<!-- ENDIF -->

<!-- szw-init:auto-end [section: red-lines] -->

<!-- szw-init:auto-start [section: skill-routing, version: 1.2] -->

## 5. skill 路由速查

### 5.1 文章流水线

| 何时 | 命令 |
|---|---|
| 新文章 | `/szw-new-article` |
| 拷问选题 + 写 brief | `/szw-discuss <slug>` |
| 证据采集 + 诊断（Codex） | `/szw-research <slug>` |
| 论证地图 + 拆片 | `/szw-outline <slug>` |
| 起稿 / 润色 | `/szw-write <slug> [--mode draft\|polish\|both]` |
| 反方审稿（Codex） | `/szw-review <slug>` |
| 多平台打包 | `/szw-publish <slug>` |
| 发布后复盘 | `/szw-retro <slug>` |
| 终结流水线 | `/szw-complete <slug>` |
| 跨 session 恢复 | `/szw-resume [<slug>]` |
| 暂停留 handoff | `/szw-pause` |
| 看进度 | `/szw-progress` |
| 灵感入站 | `/szw-capture` |
| 短评直出 | `/szw-quick` |

<!-- IF wiki.enabled -->

### 5.2 wiki 命令族

| 何时 | 命令 |
|---|---|
| vault → szw seed/refresh | `/szw-wiki-import [--full\|--incremental\|--dry-run]` |
| inbox 素材 review 后批量入站 | `/szw-wiki-ingest --from-inbox` |
| 单素材 ingest | `/szw-wiki-ingest <resources/file>` |
| 批量 ingest 未处理项 | `/szw-wiki-ingest --batch` |
| 创建 stub wiki 页 | `/szw-wiki-create-page <type> <slug>` |
| 查 wiki | `/szw-wiki-query <q>` |
| 给 article 推荐相关页 | `/szw-wiki-suggest <slug>` |
| 健康检查 | `/szw-wiki-lint` |

<!-- ENDIF -->

### 5.3 长期资产维护

| 何时 | 命令 |
|---|---|
| 改写作宪法 | `/szw-context` |
| 记决策 | `/szw-adr` |
| 单术语扩 | `/szw-glossary` |
| 配置 | `/szw-config [show\|get\|set\|validate\|reset]` |
| 命令参考 | `/szw-help` |

<!-- szw-init:auto-end [section: skill-routing] -->

<!-- IF wiki.enabled -->
<!-- szw-init:auto-start [section: source-flow, version: 1.2] -->

## 6. 三段式素材流

```
inbox/sources/<file> (read: false)
   ↓ 用户 review，标 read: true
inbox/sources/<file> (read: true)
   ↓ /szw-wiki-ingest --from-inbox
   - 校验 frontmatter
   - 规范化 filename: YYYY-MM-DD-<slug>.md
   - 重写 markdown 内附件引用相对路径
   - 移到 resources/，删除 inbox 原文件（assets/<slug>/ 不动）
resources/<YYYY-MM-DD-slug>.md
   ↓ 标准 ingest 决策树（详见 wiki/WORKFLOWS.md §一）
wiki/<type>/<slug>.md（含 sources 溯源）
```

附件统一存 `assets/<slug>/`（slug 与 markdown 文件名同；去 .md）。markdown 用相对路径引用：

| 文件位置 | 引用路径 |
|---|---|
| `inbox/sources/<file>.md` | `![[../../assets/<slug>/img.jpg]]`（深 2 层） |
| `resources/<file>.md` | `![[../assets/<slug>/img.jpg]]`（深 1 层） |
| `wiki/<type>/<file>.md` | `![[../../assets/<slug>/img.jpg]]`（深 2 层） |

迁移时 assets/ 不动，仅 rewrite markdown 内的相对深度。

<!-- szw-init:auto-end [section: source-flow] -->
<!-- ENDIF -->

<!-- IF vault.path -->
<!-- szw-init:auto-start [section: vault-boundary, version: 1.2] -->

## 7. 与 vault 的边界

本 Column 配置了 vault 作为可选 seed source：

- `vault.path`: `<VAULT_PATH>`（机器特定，存 `.zero/szw-config.local.json`）
- 仅 `/szw-wiki-import` 期间访问 vault，且**只读**
- vault 的 ingest/lint 由 vault 自己的 Claude session 维护，本 Column 不调用
- 冲突时默认走 merge prompt（不强制覆盖任一边）

<!-- szw-init:auto-end [section: vault-boundary] -->
<!-- ENDIF -->

<!-- szw-init:auto-start [section: style-prefs, version: 1.2] -->

## 8. 风格偏好

- 中文优先（用户主语言），技术名词保留英文
- 文档简洁，避免装饰；新信息附在已有内容下方，保留时间线
- skill 描述用英文（agent 路由稳定），SKILL.md 内部可中英混排
- 不写不必要注释；仅 WHY 非显然时一行说明

<!-- szw-init:auto-end [section: style-prefs] -->

<!-- szw-init:auto-start [section: startup-check, version: 1.2] -->

## 9. 启动检查清单

每次开始前：

1. 当前任务属于哪种？
   - article 流水线（brief / research / outline / write / review / publish）
<!-- IF wiki.enabled -->
   - wiki 维护（ingest / query / lint）
<!-- ENDIF -->
   - 配置 / 元命令
2. 该任务允许触达哪些目录？
3. 是否需要先 `/szw-progress` 看全局健康？
4. 是否有 active article 需先 `/szw-resume <slug>`？

<!-- szw-init:auto-end [section: startup-check] -->

---

## 用户自定义区

> 下面是给用户手加项目特定约束的区域。`/szw-init` 永不动这里。
> 例如：
> - 本 Column 特殊术语统一规则
> - 引用其他 GitHub repo 时的 commit pin 偏好
> - 对某 sub-agent 的项目级 routing 覆盖

(空)
