# szw × LLM Wiki 集成方案（fan.md 扩展）v2.1

> 这是 [`fan.md`](./fan.md) 的 patch addendum。把 LLM wiki 作为 **szw 自身拥有的素材层**接入。
>
> **v2.1 修订**：基于用户拍板新增 5 处变更——
> 1. `Column/assets/` 显性目录（素材附件统一存放）
> 2. inbox/sources/ → resources/ 迁移**不留备份**（直接删除原文件）
> 3. CLAUDE.md / AGENTS.md re-init 走**聚合策略**（标记块外用户内容永不动）
> 4. 完整模板生成（附录 A 从骨架展开）
> 5. starter pack 推迟到 v2

---

## TL;DR

- **szw 拥有自己的 wiki**：每个 Column 内部完整复刻 Karpathy 三层（raw sources / wiki / schema）；vault 仅作为可选 seed
- **三段式素材流**：`inbox/sources/` (read=false) → review → 标 read=true → 自动迁移到 `resources/`（**不留备份**）→ ingest 到 `wiki/`
- **附件统一**：`Column/assets/<slug>/` 平铺存图 / PDF；markdown 用相对路径引用；迁移时 assets 不动，只 rewrite 引用的相对深度
- **schema 四件套**：`Column/CLAUDE.md` / `Column/AGENTS.md` / `wiki/CONVENTIONS.md` / `wiki/WORKFLOWS.md` 由 `/szw-init` 生成；re-init 走聚合（用户手加内容永不被动）
- **10 个 wiki 相关 skill**（v1: 6 个；v2: 4 个）
- **wiki 是可选层**：不启用时退化为 fan.md 原版纯文章流水线
- **vault 红线收窄**：仅 import 操作期间只读 vault；其他时间 szw 与 vault 完全无关

---

## 1. 范式

### 1.1 szw 自治：内嵌完整三层

Karpathy [LLM Wiki gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) 三层在 szw 的体现：

| 层 | szw 内的实体 |
|---|---|
| Raw sources | `Column/resources/` + `Column/assets/` |
| Wiki | `Column/wiki/` |
| Schema | `Column/CLAUDE.md` + `Column/AGENTS.md` + `wiki/CONVENTIONS.md` + `wiki/WORKFLOWS.md` |

文章生产流水线（`articles/` / `published/`）是这三层之上的**消费者**：

```
inbox/sources/ (待 review) + assets/<slug>/
   ↓ /szw-wiki-ingest --from-inbox
resources/ (raw sources) + assets/<slug>/（不动）
   ↓ /szw-wiki-ingest <file>
wiki/ (LLM 综合层)
   ↓ /szw-wiki-suggest, /szw-wiki-query
articles/<slug>/ (essay 生产)
   ↓ /szw-publish
published/<slug>/
```

### 1.2 vault 作为可选种子

| 关系 | 说明 |
|---|---|
| vault 角色 | 可选 seed source（不是 storage backend） |
| szw 写 wiki | ✅ owner 权利 |
| import 频率 | 一次 seed + 偶尔 refresh |
| vault 红线生效时机 | 仅 import 操作期间 |
| 没有 vault 也能用 | ✅（空骨架 / 一切都从 inbox 进） |

三种典型场景：

| 场景 | bootstrap 方式 |
|---|---|
| A. 无 vault | `/szw-init` 创建空 wiki 骨架 |
| B. 有 vault 想 seed | `/szw-init` → `/szw-wiki-import --full` |
| C. 多人/多设备 | 每个 Column 自己拥有 wiki，vault 不强绑 |

### 1.3 essay 仍不进 wiki

vault `connections/wiki-as-essay-engine.md` 论点对 szw 也成立：wiki 是 sense-making 素材层，essay 是产物。

- ❌ essay 全文不进 `wiki/`
- ✅ essay 中**产生的原创判断、新连接** 可提取为 `wiki/connections/<X>.md`（标 `derived: true`）
- ✅ 已发布文章可作为 `resources/` 内的 `type: own-article` 被后续文章引用

反向沉淀走 v2 的 `/szw-wiki-feedback`。

---

## 2. 边界与红线

### 2.1 vault 红线（仅 import 期间）

- ❌ import 操作不写 vault 任何文件
- ❌ szw 不在内部调用 vault session 的工具

### 2.2 szw 自治期红线

| 红线 | 说明 |
|---|---|
| 不绕过 resources/ ingest 到 wiki/ | wiki 内容必须能溯源 resources/<file>（除 connection / hub 例外） |
| inbox/sources/ → resources/ 必经 review | `read: true` 是用户显式确认 |
| `published/` 只走 `/szw-publish` 写 | 沿用 fan.md §8.1 hooks |
| `EDITORIAL_CONTEXT.md` 走 `/szw-context` | 同上 |
| essay 全文不进 wiki | §1.3 |
| `assets/<slug>/` 中已有附件不删 | 除非用户显式删整个 resource |

---

## 3. 目录结构（fan.md §9 patch）

### 3.1 显性层修订

```
Column/
│
├── COLUMN.md                          ← 专栏定位
├── EDITORIAL_CONTEXT.md               ← 写作宪法
├── ROADMAP.md                         ← 选题路线图
├── CLAUDE.md                          ← 【新增】Claude Code 项目指令
├── AGENTS.md                          ← 【新增】Codex 项目指令
│
├── published/                         ← fan.md 原
├── articles/                          ← fan.md 原
├── editorial-adr/                     ← fan.md 原
├── glossary/                          ← fan.md 原
│
├── inbox/                             ← 入口层
│   ├── pending/                       ← 写作灵感待处理（fan.md 原）
│   ├── done/                          ← 灵感已升级 article 存根（fan.md 原）
│   └── sources/                       ← 【新增】待 review 的外部素材（read=true 后被自动迁移并删除）
│
├── resources/                         ← 【新增】已 review 素材，wiki ingest 源
│   ├── INDEX.md
│   └── YYYY-MM-DD-<slug>.md
│
├── assets/                            ← 【新增】素材附件统一目录（与 resource slug 同名子目录）
│   ├── 2026-05-06-foo/
│   │   ├── page_01.jpg
│   │   └── diagram.png
│   ├── 2026-05-04-bar/
│   │   └── chart.svg
│   └── wiki-illustrations/            ← 可选：wiki 自创图（未关联具体 resource）
│
├── wiki/                              ← 【新增】LLM wiki 综合层
│   ├── INDEX.md
│   ├── log.md                         ← 仿 Karpathy log.md
│   ├── CONVENTIONS.md                 ← 命名 / frontmatter 约定
│   ├── WORKFLOWS.md                   ← ingest / query / lint 详细流程
│   ├── concepts/{INDEX.md, *.md}
│   ├── people/{INDEX.md, *.md}
│   ├── topics/{INDEX.md, *.md}
│   ├── frameworks/{INDEX.md, *.md}
│   ├── tools/{INDEX.md, *.md}
│   ├── connections/{INDEX.md, *.md}
│   └── hubs/{INDEX.md, *.md}
│
├── series/                            ← fan.md 原
├── summaries/                         ← fan.md 原
│
└── .zero/
    ├── STATE.md                       ← fan.md 原
    ├── szw-config.json                ← 主 config（入 git）
    ├── szw-config.local.json          ← 【新增】机器特定（vault.path），不入 git
    ├── style-profile.md               ← fan.md 原
    ├── evidence/                      ← fan.md 原
    ├── audits/                        ← fan.md 原
    ├── writing-history/               ← fan.md 原
    │
    └── wiki-cache/                    ← 【新增】wiki 反向索引
        ├── reverse.json               ← tag/concept/resource → pages 反查
        ├── content-hash.json          ← 增量同步 SHA256
        ├── seed-manifest.json         ← vault import 来源记账（冲突检测）
        └── orphans.json               ← lint 缓存
```

### 3.2 关键变化总览

| 项 | v1（旧） | v2.1（本稿） |
|---|---|---|
| `Column/wiki/` | 仅 INDEX.md 卡片 | 完整正文 + 7 类目录 |
| `Column/resources/` | 不存在 | 显性层独立目录 |
| `Column/assets/` | 不存在 | 【新】平铺 `<slug>/` 子目录存附件 |
| `Column/inbox/sources/` | 不存在 | 待 review 素材；read=true 后**直接删除**（不留 stub / done/） |
| `Column/CLAUDE.md` & `AGENTS.md` | 不存在 | init 自动生成；re-init 走聚合 |
| `wiki/CONVENTIONS.md` & `WORKFLOWS.md` | 不存在 | init 启用 wiki 时生成 |
| `.zero/wiki-cache/` | 简单索引 | 含 seed-manifest + orphans |

### 3.3 git 跟踪策略

| 路径 | 入 git | 理由 |
|---|---|---|
| `Column/wiki/**/*.md` | ✅ | 跨设备共享 |
| `Column/resources/**/*.md` | ✅ | 同上 |
| `Column/assets/<slug>/*` | ✅ | 附件是 resource 完整性的一部分；体积 git LFS 视情况 |
| `Column/inbox/sources/**/*.md` | ⚠️ 可选 | 默认入；用户可在 .gitignore 跳 |
| `Column/CLAUDE.md` & `AGENTS.md` | ✅ | 团队共享指令 |
| `.zero/wiki-cache/*.json` | ✅ | 可重建但 baseline 有用 |
| `.zero/szw-config.json` | ✅ | 工作流配置 |
| `.zero/szw-config.local.json` | ❌ | 机器特定 |
| `Column/inbox/pending/` | ⚠️ | fan.md §9.2 已建议（碎片化灵感不入版本） |

---

## 4. inbox → resources → wiki 三段式工作流

### 4.1 阶段 1：捕获到 inbox/sources/

获取方式不限（Obsidian Web Clipper / 手动建文件 / vault cp / AI 协助起草）。**szw 不做 capture skill**。

落盘格式：

```yaml
---
type: article | paper | book | podcast | video | repo | tweet | other
title: "原始标题"
source: "https://..."
author: "作者名"
captured: 2026-05-06
lang: zh | en | ...
tags: [tag1, tag2]
read: false                     # 用户 review 后改 true
read_notes: ""                  # 可选简评
---

正文...

![[../assets/2026-05-06-foo/page_01.jpg]]      # 附件相对路径（inbox/sources/ 比 resources/ 深一层）
```

附件直接放 `Column/assets/<slug>/` 平铺，不需要在 inbox 阶段建独立子目录。`<slug>` 与 markdown 文件名（去 `.md`）相同。

### 4.2 阶段 2：review + 自动迁移（v2.1 修订）

`/szw-wiki-ingest --from-inbox` 行为：

```
1. 扫 inbox/sources/*.md，按 frontmatter 分组：
   - read: true  → 进入迁移 + ingest 流程
   - read: false → skip（列出来供用户参考）

2. 对每个 read: true 的项（事务性，失败回滚）：
   a. 校验 frontmatter（必备字段：type / title / source / captured / lang）
      缺字段 → 询问用户补全；不擅自填默认
   b. 规范化 filename：YYYY-MM-DD-<slug>.md（用 captured 日期 + title-derived slug）
      slug 冲突 → 询问用户改名
   c. 处理附件：
      - 检测 markdown 内 ![[../assets/<slug>/...]] 引用
      - assets/<slug>/ 目录**不动**（不重命名，不移动）
      - 重写 markdown 内引用的相对深度：
        from: ![[../assets/<slug>/img.jpg]]   (inbox/sources/ → assets/，相差 2 层)
        to:   ![[../assets/<slug>/img.jpg]]   (resources/ → assets/，相差 1 层)
        实际写为 ../ 一次（resources/ 平级到 assets/）
   d. 移动文件：inbox/sources/<file>.md → resources/<new-name>.md
   e. **删除原 inbox/sources/<file>**（不留备份；assets 是唯一保留的"自己的资源"）
   f. 触发标准 ingest（见 §4.3）

3. 输出统计：
   - 迁移 N 个、ingest M 个（触发 wiki 页变更 X 个）
   - 跳过 K 个（read=false）+ 列表
   - 校验失败 P 个 + 错误细节
```

### 4.3 阶段 3：ingest 到 wiki

复用 vault `workflows.md` §一 9 步决策树（细节见 `wiki/WORKFLOWS.md`）：

```
对 resources/<file> 中的每个关键概念/人物/主题：

存在对应 wiki 页？
├── 是 → 该页是否需要更新？
│   ├── 是 → 加入新观点 / 例证 / 链接
│   │       检查矛盾（标 ⚠️）
│   │       追加 sources 引用
│   └── 否 → 仅在 sources 列表追加
└── 否 → 是否值得创建新页？
    ├── 是 → 在合适子目录创建（concepts/people/topics/frameworks/tools/connections）
    │       使用 stub 状态
    └── 否 → 在 wiki/log.md 留标注，等更多素材
```

每次 ingest 后：
- 更新 `resources/<file>` frontmatter：`processed: true` / `wiki_pages: [...]` / `summary: ...`
- 更新 `wiki/INDEX.md` 与对应分类 INDEX.md
- 追加 `wiki/log.md`：`## [YYYY-MM-DD HH:MM] ingest | <slug>`
- 增量重建 `.zero/wiki-cache/reverse.json`

### 4.4 显式 ingest（不走 inbox）

| 形式 | 行为 |
|---|---|
| `/szw-wiki-ingest <resources/file>` | 单文件 |
| `/szw-wiki-ingest --batch` | 批量 processed=false 的项（限 5 篇/批） |
| `/szw-wiki-ingest --dry-run <file>` | 只列将触及的 wiki 页 |

---

## 5. wiki schema 文件与聚合机制

### 5.1 四份文档分工

| 文件 | 受众 | 内容 | 生成时机 |
|---|---|---|---|
| `Column/CLAUDE.md` | Claude Code | 项目级指令：角色 / 目录 / 红线 / skill 路由 / vault 边界 | `/szw-init` 永远生成 |
| `Column/AGENTS.md` | Codex | 与 CLAUDE.md 对偶；工具名 + sub-agent 路由按 Codex 调整 | `/szw-init` 永远生成 |
| `wiki/CONVENTIONS.md` | LLM + 用户 | wiki 命名 / frontmatter / wikilink / 标签 | `/szw-init` 启用 wiki 时生成 |
| `wiki/WORKFLOWS.md` | LLM + 用户 | ingest / query / lint 详细决策树 | `/szw-init` 启用 wiki 时生成 |

### 5.2 聚合机制（v2.1 新增）

re-init 时遇到已存在的四份文档之一，**不覆盖、不跳过**，走聚合：

```
1. 文件内 init 生成的章节用 HTML 注释标记包裹：

   <!-- szw-init:auto-start [section: red-lines, version: 1.2] -->
   ## 4. 红线
   ...
   <!-- szw-init:auto-end [section: red-lines] -->

2. re-init 解析当前文件：
   - 收集所有标记块（按 section name 索引）
   - 标记块外的内容 = 用户自定义区，标为 PRESERVE

3. 生成新版各 section 内容（按 init 的当前 schema_version）

4. 对每个 section 做 diff：
   - 标记块不存在（首次启用） → 直接插入新 section（按预定顺序）
   - 标记块版本相同 + 内容相同 → skip
   - 标记块版本相同 + 内容不同 → 该 section 已被用户改过；询问用户：
     [a] 保留我的版本（init 跳过此 section）
     [b] 应用 init 新版（覆盖我的修改）
     [c] 显示 diff 后再选
   - 标记块版本旧（schema 升级） → 列入"待更新"，默认应用，可单独跳过

5. 用户自定义区（标记块外）→ 完全保留，原位插回

6. 新章节（init 升级带来的，不在旧文件中存在的 section）→ 直接插入合适位置
```

### 5.3 标记块语法约定

```html
<!-- szw-init:auto-start [section: <slug>, version: <semver>] -->
内容...
<!-- szw-init:auto-end [section: <slug>] -->
```

- `section` slug 命名：`project-role` / `directory-layout` / `core-abstractions` / `red-lines` / `skill-routing` / `vault-boundary` / `source-flow` / `style-prefs` / `startup-check`
- `version` 用 `<schema-version>.<minor>` 形式（如 `1.2`）；schema-version 整体改才升 major

用户**永不该手编辑**标记块内容（改了下次 re-init 会询问），可在标记块**外**自由加章节、注释、备忘。

---

## 6. 命令清单

### 6.1 v1（6 个）

| 命令 | 作用 | 实现 |
|---|---|---|
| `/szw-init`（修订） | 启用 wiki 时跑子流程：建空骨架 / seed from vault / skip；产出四件套 | Week 1 |
| `/szw-wiki-import` | vault → szw 全量 / 增量；冲突走 merge prompt | Week 4 |
| `/szw-wiki-ingest` | resources/ → wiki ingest；含 `--from-inbox` 自动迁移 | Week 4 |
| `/szw-wiki-create-page` | 创建 stub wiki 页 | Week 4 |
| `/szw-wiki-query <q>` | 查询 wiki；好答案可回填 connections/ | Week 4 |
| `/szw-wiki-suggest <slug>` | 给 article 推荐相关 wiki 页 + resources | Week 4 |
| `/szw-wiki-lint` | 健康检查 | Month 2 |

### 6.2 v2（4 个，含 starter pack）

| 命令 | 作用 |
|---|---|
| `/szw-wiki-edit <page>` | 引导编辑（保持 frontmatter 规范） |
| `/szw-wiki-trace <slug>` | 反查 article 用了哪些 wiki / resources |
| `/szw-wiki-feedback <slug>` | 完稿后产 wiki connections/ 反向沉淀建议 |
| `/szw-init --starter-pack <domain>` | 用领域预填的 schema 模板初始化（如 tech-column / research-notes / book-companion） |

### 6.3 不实现（仅 1 项）

| 命令 | 不实现理由 |
|---|---|
| `/szw-wiki-capture` | 用户已否决；通过 Obsidian Web Clipper / 手动 / 其他工具进 inbox/sources/ |

---

## 7. 各命令详细设计

### 7.1 `/szw-init` wiki 子流程

```
Mode A（空目录）：
  ...（fan.md 原流程产出 COLUMN/EDITORIAL_CONTEXT/ADR/STATE/szw-config）

  询问 1：是否启用 wiki 层？
    [推荐] 写技术专栏，wiki 让证据银行复利、防止术语漂移
    [跳过] 短文 / 灵感型博客可不要

    选 No → 跳过 wiki 初始化；CLAUDE.md/AGENTS.md 也不含 wiki 段
    选 Yes → 询问 2

  询问 2：wiki 怎么 bootstrap？
    (a) 从 vault seed → 询问 vault.path → 跑 /szw-wiki-import --full
    (b) 空骨架（建 7 类 INDEX.md 占位 + log.md + CONVENTIONS.md + WORKFLOWS.md）
    (c) 跳过 bootstrap（之后再手动 ingest）

  生成 CLAUDE.md / AGENTS.md（按询问 1 结果决定是否含 wiki 章节）
```

```
Mode B（已有内容）：
  检测：
    1. CLAUDE.md / AGENTS.md 已存在？
       → 走聚合（详见 §5.2）；列出"待更新章节"清单 + 用户决策
    2. 已有 wiki/ 目录？
       → 询问"是否补 CONVENTIONS.md / WORKFLOWS.md schema 文件？"
       → 已存在 → 走聚合
    3. 已有 resources/？
       → 询问"是否对未 ingest 的素材跑 /szw-wiki-ingest --batch？"
    4. 配置了 vault.path 但未 import？
       → 询问"是否跑 /szw-wiki-import --full seed？"
```

### 7.2 `/szw-wiki-import`

| 形式 | 行为 |
|---|---|
| `/szw-wiki-import` | 增量（用 `seed-manifest.json` 比对） |
| `/szw-wiki-import --full` | 全量 seed |
| `/szw-wiki-import --dry-run` | 只列变更 |
| `/szw-wiki-import --pages-only` | 只 import 1-wiki/，跳过 4-resources/ |

#### 7.2.1 增量冲突处理（merge prompt）

每页比对三个 hash：
- `seed_hash`：seed 时 vault 端 SHA256（存 `seed-manifest.json`）
- `vault_now_hash`：当前 vault 端
- `szw_now_hash`：当前 Column/wiki/<page> 端

四种状态：

| seed→vault | seed→szw | 含义 | 行为 |
|---|---|---|---|
| 不变 | 不变 | 无变化 | skip |
| 变了 | 不变 | vault 单边更新 | fast-forward 写入 szw |
| 不变 | 变了 | szw 单边修改 | 保留 szw |
| 变了 | 变了 | **冲突** | 进入 merge prompt |

merge prompt 五选项：

```
⚠️ 冲突：wiki/topics/claude-code-ecosystem.md

vault 端更新（since seed 2026-04-25）：
  +新增段落：## v2.0 工具列表更新
  +sources +1: 4-resources/2026-05-04-claude-code-v2.md

Column/wiki 端修改（since seed 2026-04-25）：
  +新增 connections 引用：[[connections/sdd-skills-stacking]]
  -删除段落：## 旧的 v1 工具图谱

请选择：
  1. keep szw     保留 Column 本地版本
  2. take vault   用 vault 覆盖
  3. merge by AI  启用 LLM 合并（产出候选 + diff，用户确认）
  4. defer        跳过本次，留待下次 import
  5. show diff    显示完整 diff 后再选

> _
```

`merge by AI` 子流程：调 wiki-merger 子 agent，输出 `wiki/<page>.merged.candidate.md`，用户人审。

### 7.3 `/szw-wiki-ingest`（v2.1 含附件处理）

| 形式 | 行为 |
|---|---|
| `/szw-wiki-ingest <resources/file>` | 单文件 ingest |
| `/szw-wiki-ingest --from-inbox` | 扫 inbox/sources/，迁移 read=true 项再 ingest |
| `/szw-wiki-ingest --batch` | 处理 resources/ 中所有 processed=false 的项 |
| `/szw-wiki-ingest --dry-run <file>` | 只列将触及的 wiki 页 |

#### 7.3.1 附件处理细节

**inbox/sources/ → resources/ 迁移时**：
- markdown 内引用 `![[../assets/<slug>/img.jpg]]`（inbox/sources/ 比 assets/ 深 2 层）
- 迁移到 resources/ 后改为 `![[../assets/<slug>/img.jpg]]`（resources/ 比 assets/ 深 1 层）
- 实质：用 regex `!\[\[\.\./\.\./assets/` → `!\[\[\.\./assets/` 替换
- assets/<slug>/ 目录本身**不动**

**ingest 时的附件可见性**：
- ingest 决策树执行时，AI 应该可读 markdown 引用的图（先读文本、再单独 view 图，仿 Karpathy 原文做法）
- 若 wiki 页要引用同一附件：相对路径 `![[../../assets/<slug>/img.jpg]]`（wiki/<type>/ 比 assets/ 深 2 层）

**附件孤儿检测**（lint 阶段）：
- 扫 `assets/<slug>/` 中所有 slug
- 检测 `resources/<slug>.md` 是否存在；不存在 → 标 orphan，写 orphans.json
- lint 仅报告，不删（用户决定）

#### 7.3.2 退出码

| 码 | 含义 |
|---|---|
| 0 | 成功 |
| 1 | 不在 Column 目录 |
| 2 | resources/<file> 不存在 |
| 3 | frontmatter 缺必备字段 |
| 4 | wiki/ 未初始化 |
| 5 | inbox 无 read=true 项（仅 --from-inbox，warning） |
| 6 | 附件迁移失败（assets/<slug>/ 路径冲突等） |

### 7.4 `/szw-wiki-create-page`

```
/szw-wiki-create-page <type> <slug> [--title "..."] [--source <resources/file>]
```

`type ∈ {concept, person, topic, framework, tool, connection, hub}`。

行为：校验格式 → 渲染 frontmatter → 写 stub → 更新 wiki/INDEX.md + wiki/<type>/INDEX.md → 追加 wiki/log.md。

### 7.5 `/szw-wiki-query`

仿 vault workflows.md §二，输入自然语言问题：

1. 读 `wiki/INDEX.md` 找相关页
2. Read 相关 wiki 页（用 frontmatter `related` 扩展）
3. 必要时回 `resources/` 看原文
4. 综合回答 + 引用具体页 + 引用 source
5. 答案有沉淀价值时询问"要写成 wiki/connections/<X>.md 吗？"
   - 同意 → 调 `/szw-wiki-create-page connection <X>` 标 `derived: true`

### 7.6 `/szw-wiki-suggest`

```
/szw-wiki-suggest <slug>
/szw-wiki-suggest --thesis "<关键词>"
```

输出按 type 分组的相关 wiki 页 + 关联 resources。

排序：tag 重合 × type 优先级（connections > topics > concepts > tools > people > frameworks > hubs）× status（mature > active > stub）× 入链数。

### 7.7 `/szw-wiki-lint`

输出健康报告（不直接修，仅建议；仿 vault workflows.md §三）：

```markdown
# Wiki Health Report — 2026-05-06

## 待 ingest 素材 (3)
- resources/2026-05-04-foo.md (processed: false)
- inbox/sources/2026-05-05-bar.md (read: true，待迁移)

## 矛盾待解决 (1)
- wiki/topics/agent-architecture.md — 关于 X 的两种说法

## 孤立页 (2)
- wiki/concepts/orphan-1.md
- wiki/people/lonely-person.md

## 缺独立页的高频概念 (3)
- "Transformer" 在 5 页提及

## 断链 (1)
- wiki/topics/foo 引用 [[concepts/missing]]

## ⚠️ 附件孤儿 (2)
- assets/2026-05-01-baz/  (无对应 resources/2026-05-01-baz.md)
- assets/2026-04-27-old/   (resources 已删但 assets 保留)

## ⚠️ resources/ 已 ingest 但 wiki_pages 字段空 (1)
- resources/2026-05-01-baz.md
```

缓存到 `.zero/wiki-cache/orphans.json` 给 `/szw-progress` 显示。

### 7.8 v2 命令（简述）

- **`/szw-wiki-edit <page>`**：交互式编辑；保持 frontmatter `updated` / sources / related 同步
- **`/szw-wiki-trace <slug>`**：反查 article 引用了哪些 wiki / resources；输出 trace 树
- **`/szw-wiki-feedback <slug>`**：完稿后扫文章，提取"产生但 wiki 还没的连接 / 判断"，建议 `wiki/connections/<X>.md` 候选（标 `derived: true`）
- **`/szw-init --starter-pack <domain>`**：v2 加领域预填模板（tech-column / research-notes / book-companion / personal-growth），用领域特定的 ADR / 术语种子 / wiki 骨架启动

---

## 8. `szw-config.json` 扩展（fan.md §10 patch）

### 8.1 主 config（入 git）

```json
{
  "wiki": {
    "enabled": true,
    "schema_version": "1.2",
    "ingest_batch_max": 5,
    "ingest_pages_per_source_max": 15,
    "lint_orphan_threshold_days": 180,
    "auto_suggest_in_research": true,
    "auto_suggest_in_discuss": true,
    "evidence_confidence_default": "medium"
  },
  "vault": {
    "wiki_subdir": "1-wiki",
    "resources_subdir": "4-resources",
    "incremental_default": true,
    "snapshot_summary_chars": 200,
    "icloud_skip_placeholders": true,
    "import_conflict_strategy": "prompt"
  },
  "inbox": {
    "sources_subdir": "sources",
    "auto_migrate_on_ingest": true,
    "delete_after_migration": true
  },
  "assets": {
    "subdir": "assets",
    "lint_orphan_check": true
  }
}
```

### 8.2 local config（不入 git）

```json
{
  "vault": {
    "path": "/Users/xinz/Library/Mobile Documents/iCloud~md~obsidian/Documents/SheanZero"
  }
}
```

### 8.3 关键字段

| 字段 | 默认 | 影响 |
|---|---|---|
| `wiki.enabled` | `false` | 为 false 时 wiki 命令报 exit 4 |
| `wiki.schema_version` | `"1.2"` | re-init 聚合用的 schema 比对版本 |
| `inbox.delete_after_migration` | `true` | 迁移后删原文件（v2.1 默认行为） |
| `assets.lint_orphan_check` | `true` | lint 检测附件孤儿 |
| `vault.import_conflict_strategy` | `"prompt"` | 默认走 merge prompt |
| `wiki.evidence_confidence_default` | `"medium"` | wiki 引用作 evidence 的默认 confidence |

---

## 9. 现有 skill 修改清单（fan.md §11 patch）

| Skill | v2.1 修改 |
|---|---|
| `szw-init` | **大改**：加询问 1/2；产出四件套（CLAUDE/AGENTS/CONVENTIONS/WORKFLOWS）；re-init 走聚合（§5.2）；启用时建空骨架或 seed |
| `szw-config` | schema 加 `wiki.* / vault.* / inbox.* / assets.*` 字段；`vault.path` 路由到 local config |
| `szw-new-article` | 加 flag `--from-wiki-signal` |
| `szw-discuss` | prepare 阶段调 `/szw-wiki-suggest` 输出 wiki_refs[] |
| `szw-research` | prepare 加 wiki_refs[]；finalize evidence card 加 wiki_ref / resource_ref |
| `szw-progress` | 显示 wiki 健康摘要（待 ingest / 待 review / 孤立 / 附件孤儿）来自 orphans.json |
| `szw-help` | 加 wiki 命令族速查 |
| `szw-context` | 涉及术语演进时提示同步 wiki/concepts/ 与 glossary/ |

不动：`szw-write` / `szw-publish` / `szw-complete` / `szw-resume` / `szw-pause` / `szw-adr` / `szw-glossary` / `szw-evidence-bank` / `szw-outline` / `szw-review`

---

## 10. 子 agent 注册表扩展（fan.md §7 patch）

| Agent | 角色 | 调用 skill | Marker | 跑在 |
|---|---|---|---|---|
| `wiki-importer` | vault → szw seed/refresh | szw-wiki-import | `## WIKI IMPORT COMPLETE` | 脚本 |
| `wiki-merger` | merge prompt 中 "merge by AI" | szw-wiki-import | `## MERGE PROPOSAL READY` | Claude |
| `wiki-ingester` | resources → wiki 决策树执行 | szw-wiki-ingest | `## INGEST COMPLETE` / `## INGEST PARTIAL` | Claude |
| `wiki-suggester` | reverse-index 推荐相关页 | szw-wiki-suggest, szw-discuss / szw-research prepare | `## SUGGESTIONS READY` | Claude |
| `wiki-querier` | wiki 综合查询 | szw-wiki-query | `## QUERY ANSWERED` | Claude |
| `wiki-linter` | 健康检查（含附件孤儿） | szw-wiki-lint | `## LINT COMPLETE` | Claude |
| `wiki-feedbacker` | essay → wiki connections 候选 | szw-wiki-feedback (v2) | `## FEEDBACK READY` | Claude |
| `init-aggregator` | re-init 时 schema 文件聚合 | szw-init | `## AGGREGATION READY` / `## AGGREGATION DEFERRED` | Claude |

---

## 11. 实施顺序（fan.md §12 patch）

### Week 1（init 阶段，wiki 子流程预留）

- [ ] `szw-init` Mode A 询问 1 / 2
- [ ] `szw-init` 产出 CLAUDE.md / AGENTS.md（用附录 A 完整模板）
- [ ] `szw-init` 启用 wiki 时产出 CONVENTIONS.md / WORKFLOWS.md / log.md / 7 类空 INDEX.md
- [ ] `szw-init` re-init 聚合机制（init-aggregator 子 agent）
- [ ] `szw-config` schema 含 wiki / vault / inbox / assets 段

### Week 4 后半（v1 流水线 + research 上线后）

- [ ] `scripts/wiki-import.py`（含 SHA256 / 冲突检测 / iCloud 占位）
- [ ] `/szw-wiki-import` SKILL（含 merge prompt）
- [ ] `scripts/wiki-ingest.py`（含 inbox 迁移 / 附件路径重写 / frontmatter 校验）
- [ ] `/szw-wiki-ingest` SKILL
- [ ] `/szw-wiki-create-page` SKILL（脚本）
- [ ] `/szw-wiki-query` SKILL
- [ ] `/szw-wiki-suggest` SKILL
- [ ] `/szw-research` prepare 接 wiki_refs
- [ ] `/szw-discuss` prepare 接 wiki_refs
- [ ] **真实文章验证**：跑一篇文章 ingest 一批 resources，验证决策树 + 附件迁移正确性

### Month 2 初

- [ ] `/szw-wiki-lint`（含附件孤儿）
- [ ] `/szw-progress` 显示 wiki 健康摘要
- [ ] `/szw-new-article --from-wiki-signal`

### Month 2 后期 / v3

- [ ] `/szw-wiki-edit`
- [ ] `/szw-wiki-trace`
- [ ] `/szw-wiki-feedback` + 反向沉淀工作流
- [ ] `/szw-init --starter-pack <domain>`
- [ ] hooks：`Column/wiki/**` 直接写入触发 "建议走 /szw-wiki-edit" 提示

### 验收准则

| 验收项 | 方法 |
|---|---|
| init 产出完整 | 跑 `/szw-init` Mode A 启用 wiki，确认 CLAUDE/AGENTS/CONVENTIONS/WORKFLOWS 都存在且含标记块 |
| re-init 聚合不破坏用户内容 | 手编辑 CLAUDE.md 标记块外加章节，跑 re-init，自定义章节应保留原位 |
| 三段式素材流跑通 | inbox/sources/<file> read=false → review → read=true → `/szw-wiki-ingest --from-inbox` → 文件出现在 resources/，inbox 原文件已删除，wiki 有相应页 |
| 附件不丢 | 迁移后 assets/<slug>/ 目录文件齐全，markdown 内引用路径已重写正确 |
| import 不写 vault | `inotifywait` 监控 vault；跑 import 应零变更 |
| 冲突 merge prompt 正确 | 手造冲突，跑 import 进 prompt |
| evidence 复用 wiki | 跑一篇文章 `/szw-research`，wiki_ref 命中率 ≥ 50% |

---

## 12. 风险与待决问题

### 12.1 风险

| 风险 | 缓解 |
|---|---|
| inbox/sources 滞留过多 | `/szw-progress` 显示待 review 数；超阈值告警 |
| frontmatter 不齐 | ingest 询问补全；不擅自填默认 |
| merge prompt 用户疲劳 | 单次 import 冲突 > 5 时先列冲突清单，让用户选处理顺序 |
| schema 文件被手改后 re-init 误覆盖 | 标记块机制 + 询问 + 默认保留用户修改 |
| vault.path 跨设备路径不同 | local config 不入 git；首次跨设备引导设置 |
| 附件目录膨胀 | git LFS / `.gitattributes` 配置；定期 lint 报告体积 |
| 附件迁移路径计算错 | dry-run 输出 rewrite 详情；事务性回滚 |

### 12.2 待决问题（剩余）

| 问题 | 我的倾向 |
|---|---|
| `wiki/log.md` 与 `.zero/STATE.md` 关系 | 分离（不同语义） |
| AGENTS.md 与 CLAUDE.md 是否完全对偶 | 95% 重叠；区别仅工具名 + sub-agent 路由 |
| 附件 git LFS 阈值 | 单文件 > 1MB 提示用 LFS（v2 加） |

---

## 13. 与 fan.md 兼容性检查

| fan.md 决策 | 兼容性 |
|---|---|
| §1.1 命名规则 `/szw-*` | ✅ |
| §1.2 设计原则 | ✅ 强化（沿用 vault 思想，schema 复用） |
| §3.0 Article 状态机 | ✅ |
| §3.1 `/szw-init` | ⚠️ 大改：加 wiki 子流程 + 四件套 + 聚合 |
| §6 命名空间路由 | ✅ 加 `szw-ns-wiki`（命令膨胀到 32+ 时） |
| §7 子 agent | ✅ 加 8 个 wiki agents |
| §8 hooks | ✅ 加 `wiki/**` 直写防护（v3） |
| §9 目录布局 | ⚠️ 加 wiki/ + resources/ + assets/ + inbox/sources/ + CLAUDE.md/AGENTS.md |
| §10 config | ✅ 加 wiki / vault / inbox / assets 段 + local config |
| §11 与现有 skills 集成 | ✅ vault 仍是外部依赖 |
| §12 实施顺序 | ⚠️ Week 1 init 接入 wiki 询问；wiki 命令族 Week 4 |
| §13 反模式 | ✅ 加 5 条（见下） |
| §14 与 GSD 对齐 | ✅ wiki 是 szw 独有扩展面 |

### 13.1 反模式补充（fan.md §13 patch）

| # | 反模式 | 立即该做 |
|---|---|---|
| 11 | 跳过 inbox/sources/ review 直接放 resources/ | 走 `/szw-wiki-ingest --from-inbox`；review 是质量闸门 |
| 12 | 手改 wiki/log.md 或 wiki/INDEX.md | 机器维护文件；改了下次 ingest 自愈但当下混乱 |
| 13 | wiki 引用作 evidence 时不链回 resources/ | wiki 是综合层；evidence 链必须回到 raw source 才能算 high confidence |
| 14 | essay 全文回填 wiki | 走 `/szw-wiki-feedback` 只提取连接 / 判断 |
| 15 | vault import 冲突无脑 take_vault | 默认走 prompt |
| 16 | 在标记块内手编辑 CLAUDE.md/AGENTS.md | 改标记块外用户区；标记块内 re-init 会询问覆盖 |
| 17 | 手动 mv assets/<slug>/ 子目录 | assets 子目录名 = markdown 文件名（去 .md），手 mv 会断链；改名走 `/szw-wiki-edit`（v2） |
| 18 | inbox/sources/ 引用 assets/ 时用 ../assets/ 而非 ../../assets/ | inbox/sources/ 比 assets/ 深 2 层；ingest 迁移时会重写为 1 层 |

---

## 14. 决策原因（meta）

### 为什么从"消费者"改成"owner"？

用户反馈点透：
1. 不是所有人都有 vault；从零起 szw 仍需要 wiki 作素材层
2. 即使有 vault，专栏自身也应有独立的素材积累
3. "在 inbox 增加 read 复选项 + 自动迁移"明确要求 szw 拥有写权

### 为什么不用 vault 作 storage backend？

- vault 是用户的私人生活知识库（PARA），覆盖面比 szw 写作素材广
- 每个 Column 应该是自洽单元，能独立 git / 跨设备 / 跨人协作
- vault 写入会触发 vault 的 ingest 流程，与 szw 的 ingest 重叠

### 为什么 inbox 还要分 pending / done / sources？

| 子目录 | 角色 | 流向 |
|---|---|---|
| `inbox/pending/` | 写作灵感（"我想写"） | → article（`/szw-new-article --from-inbox`） |
| `inbox/done/` | 灵感升级 article 后存根 | 终态 |
| `inbox/sources/` | 待 review 的外部素材（"我读到的"） | → resources/（迁移后**删除**） |

写作灵感 vs 阅读素材是两条流向；vault 自身也分 0-Inbox 与 thoughts/。

### 为什么 inbox/sources/ 迁移不留备份？

- 用户拍板："都是自己的资源"——不需要双份冗余
- assets/<slug>/ 是真正"丢了就找不回来"的二进制资产，必须保留
- markdown 本身在 resources/ 已有完整副本（带新 frontmatter `processed: true` + `wiki_pages: [...]`），inbox 端的 stub 没有信息增量
- 简化目录结构（不需要 `inbox/sources/done/`）

### 为什么 assets/ 用根级平铺而非各层各自带 _attachments/？

- 与 vault `6-assets/` 同构（用户已习惯）
- 迁移最简：assets/<slug>/ 不动，只 rewrite markdown 引用相对深度
- 一图多引：wiki 页可引用同一 resource 的图，不用复制
- git 监控集中：附件体积监控只看一个目录

### 为什么 schema 文件分四份而不合并？

- `Column/CLAUDE.md` / `AGENTS.md`：项目级约束，每次 session 全加载
- `wiki/CONVENTIONS.md` / `WORKFLOWS.md`：wiki 局部约定，按需加载

合并会让 CLAUDE.md 过长；分层加载更省 context。

### 为什么 re-init 走聚合而非覆盖？

- 用户拍板：保留手加内容
- schema 会演进；强制覆盖会丢失用户的项目特定约束
- 标记块机制让"机器可改区"与"用户区"清晰隔离

### 为什么 essay 反向沉淀放 v2？

- v1 优先把 owner 模式跑通
- 反向沉淀依赖 article 已能在 wiki 上消费（v1 完成后才有体感）
- Karpathy V2 update 的 `derived: true` 模式 v2 落地

---

## 附录 A：CLAUDE.md / AGENTS.md 完整模板

由 `/szw-init` 生成。下面是 CLAUDE.md 模板；AGENTS.md 见 §A.2 差异说明。

### A.1 CLAUDE.md 完整模板

````markdown
# {COLUMN_NAME} — Claude Code 项目指令

> Last updated by /szw-init: {DATE}
> szw_init_version: 1.2

本文件是 szw Column 的项目级约束。每次 session 自动加载。

> **维护规则**：本文件的章节用 `<!-- szw-init:auto-* -->` 标记块包裹。
> - 标记块**内**的内容由 `/szw-init` 维护，re-init 时会询问是否更新
> - 标记块**外**的内容（包括文末"用户自定义区"）init 永不动
> - 想加项目特定约束 → 写到文末用户自定义区

<!-- szw-init:auto-start [section: project-role, version: 1.2] -->

## 1. 项目角色

这是一个**技术专栏 Column**，由 [szw 工作流](https://github.com/sheanzero/zero-to-ai) 管理。

{IF wiki.enabled:}
本 Column 同时是 [Karpathy LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) 模式的本地实例：

| Karpathy 三层 | 本 Column 体现 |
|---|---|
| Raw sources | `resources/` + `assets/` |
| Wiki | `wiki/`（含 7 类：concepts / people / topics / frameworks / tools / connections / hubs） |
| Schema | 本文件 + AGENTS.md + wiki/CONVENTIONS.md + wiki/WORKFLOWS.md |
{ENDIF}

<!-- szw-init:auto-end [section: project-role] -->

<!-- szw-init:auto-start [section: directory-layout, version: 1.2] -->

## 2. 目录布局速查

```
{COLUMN_NAME}/
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
│   └── sources/               待 review 的外部素材（read=true 后自动迁移并删除）
{IF wiki.enabled:}
├── resources/                 raw sources，wiki ingest 唯一来源
├── assets/<slug>/             素材附件（图片 / PDF）
├── wiki/                      LLM wiki 综合层
│   ├── INDEX.md / log.md
│   ├── CONVENTIONS.md         命名 / frontmatter 约定
│   ├── WORKFLOWS.md           ingest / query / lint 详细流程
│   └── {concepts,people,topics,frameworks,tools,connections,hubs}/
{ENDIF}
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
{IF wiki.enabled:}
| **wiki page** | `wiki/<type>/<slug>.md` | stub → active → mature |
| **resource** | `resources/<YYYY-MM-DD-slug>.md` | inbox → reviewed → ingested |
| **attachment** | `assets/<slug>/...` | 与 resource 同生命周期 |
{ENDIF}

<!-- szw-init:auto-end [section: core-abstractions] -->

<!-- szw-init:auto-start [section: red-lines, version: 1.2] -->

## 4. 红线（不可越过）

不论用户如何要求，下列动作永不执行：

- ❌ `published/` 只走 `/szw-publish` 写，不直接编辑
- ❌ `EDITORIAL_CONTEXT.md` 走 `/szw-context`，不直接编辑
- ❌ ADR 文件走 `/szw-adr`，不手动编号 / 创建
{IF wiki.enabled:}
- ❌ 不绕过 resources/ 直接 ingest 到 wiki/
- ❌ inbox/sources/ → resources/ 必经用户 review（read: true 是显式确认）
- ❌ essay 全文不进 wiki/（仅可提取连接 / 判断到 connections/ 标 derived: true）
- ❌ `assets/<slug>/` 中已有附件不删（除非用户显式删整个 resource）
{ENDIF}
{IF vault.path 已配置:}
- ❌ vault import 操作只读 vault，永不写
- ❌ 不在 szw 内调用 vault session 工具（避免双 owner 冲突）
{ENDIF}

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

{IF wiki.enabled:}

### 5.2 wiki 命令族

| 何时 | 命令 |
|---|---|
| 起步建 wiki | `/szw-init` 启用 wiki |
| vault → szw seed/refresh | `/szw-wiki-import [--full\|--incremental\|--dry-run]` |
| inbox 素材 review 后批量入站 | `/szw-wiki-ingest --from-inbox` |
| 单素材 ingest | `/szw-wiki-ingest <resources/file>` |
| 批量 ingest 未处理项 | `/szw-wiki-ingest --batch` |
| 创建 stub wiki 页 | `/szw-wiki-create-page <type> <slug>` |
| 查 wiki | `/szw-wiki-query <q>` |
| 给 article 推荐相关页 | `/szw-wiki-suggest <slug>` |
| 健康检查 | `/szw-wiki-lint` |

{ENDIF}

### 5.3 长期资产维护

| 何时 | 命令 |
|---|---|
| 改写作宪法 | `/szw-context` |
| 记决策 | `/szw-adr` |
| 单术语扩 | `/szw-glossary` |
| 配置 | `/szw-config [show\|get\|set\|validate\|reset]` |
| 命令参考 | `/szw-help` |

<!-- szw-init:auto-end [section: skill-routing] -->

{IF wiki.enabled:}
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
{ENDIF}

{IF vault.path 已配置:}
<!-- szw-init:auto-start [section: vault-boundary, version: 1.2] -->

## 7. 与 vault 的边界

本 Column 配置了 vault 作为可选 seed source：

- `vault.path`: `{VAULT_PATH}`（机器特定，存 `.zero/szw-config.local.json`）
- 仅 `/szw-wiki-import` 期间访问 vault，且**只读**
- vault 的 ingest/lint 由 vault 自己的 Claude session 维护，本 Column 不调用
- 冲突时默认走 merge prompt（不强制覆盖任一边）

<!-- szw-init:auto-end [section: vault-boundary] -->
{ENDIF}

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
   - wiki 维护（ingest / query / lint）
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
````

### A.2 AGENTS.md 与 CLAUDE.md 的差异

AGENTS.md 95% 内容与 CLAUDE.md 相同；区别：

#### 标题与开头
```markdown
# {COLUMN_NAME} — Codex 项目指令

> Last updated by /szw-init: {DATE}
> szw_init_version: 1.2

本文件是 szw Column 给 Codex 的项目级约束。
```

#### §5.1 工具名调整
- `Read/Edit/Write/Bash` → `read/edit/write/bash`（Codex 风格）
- 引用 skill 时格式不变（`/szw-*` 通用）

#### §5 加 §5.4 Codex 专属角色
```markdown
<!-- szw-init:auto-start [section: codex-roles, version: 1.2] -->

## 5.4 Codex 子 agent 角色

本 Column 默认在 .zero/szw-config.json 中将下列子 agent 路由到 Codex：

- `evidence-researcher`（/szw-research Phase 1：证据采集）
- `claim-diagnoser`（/szw-research Phase 2：判断诊断）
- `skeptical-reviewer`（/szw-review Phase 1：反方审稿）

当你（Codex）作为这些子 agent 被调用时：
- 输入由 Claude 主对话给定（含 brief / outline / 上下文 JSON）
- 输出符合 Completion marker 协议（如 `## EVIDENCE COMPLETE` / `## DIAGNOSIS PASSED`）
- 不调用 szw 顶层 skill；只产出本子 agent 应产出的 markdown 段落

<!-- szw-init:auto-end [section: codex-roles] -->
```

#### §6（如启用 wiki）的 wiki-merger 角色
若启用 wiki，AGENTS.md §6 加一段：

```markdown
当用户在 /szw-wiki-import 遇到冲突选择 "merge by AI" 且 .zero/szw-config.json 配置 wiki-merger 路由到 Codex 时，你将被调起执行三向 merge，输出标 `## MERGE PROPOSAL READY`。
```

---

## 附录 B：wiki/CONVENTIONS.md 骨架（含附件命名）

直接复用 vault `conventions.md` 七节结构，加 szw-specific 项：

```markdown
# Wiki Conventions

> 本文件规定 wiki/ 与 resources/ 与 inbox/sources/ 与 assets/ 中文件的命名、frontmatter、链接、标签约定。
> ingest / query / lint 流程详见 `WORKFLOWS.md`。

## 一、文件命名

### resources/
格式：`YYYY-MM-DD-{slug}.md`

### inbox/sources/
同 resources/ 命名格式（review 通过迁移到 resources/ 时不需重命名）

### wiki/
格式：`{slug}.md`，7 类目录：concepts/ people/ topics/ frameworks/ tools/ connections/ hubs/

### assets/
**子目录命名**：与 markdown 文件名同名（去 .md）
- `resources/2026-05-06-foo.md` → `assets/2026-05-06-foo/`
- `wiki-illustrations/` 例外：wiki 自创图（未关联具体 resource）

**附件文件命名**：自由，建议用语义化（`page_01.jpg` / `architecture-diagram.png` / `interview-transcript.pdf`）

## 二、Frontmatter

### resources/<file>
（沿用 vault 4-resources 约定）

### inbox/sources/<file>
（resources frontmatter + 加：）
- `read: false | true`（用户 review 后改 true）
- `read_notes: ""`（可选简评）

### wiki/<type>/<slug>.md
（沿用 vault 1-wiki 约定 + 加 szw 字段：）
- `derived: false | true`（是否为反向沉淀页，标记综合产物）

## 三、链接格式

### Wiki 内部链接
（Obsidian wikilink，仿 vault）
- `[[wiki/concepts/llm-wiki-pattern|LLM Wiki 模式]]`

### Wiki → Resource 溯源
（沿用 vault `## Sources` 段约定）

### Markdown → Asset 引用（v2.1 新增）
| markdown 位置 | 引用路径 |
|---|---|
| `inbox/sources/<file>.md` | `![[../../assets/<slug>/img.jpg]]` |
| `resources/<file>.md` | `![[../assets/<slug>/img.jpg]]` |
| `wiki/<type>/<file>.md` | `![[../../assets/<slug>/img.jpg]]` |

ingest 迁移时自动 rewrite 相对深度。

### 跨 Column → vault（如 vault.path 已配置）
- 用绝对路径 `file:///<vault>/...`
- 仅用于 wiki/ 中 import 来的页

## 四、标签 / 五、Markdown / 六、日期 / 七、特殊文件

（沿用 vault conventions.md，路径相对 Column/）
```

---

## 附录 C：wiki/WORKFLOWS.md 骨架

复用 vault `workflows.md` 六节，加新章节：

```markdown
# Wiki Workflows

## 一、Ingest（摄入）
（沿用 vault 9 步决策树）
触发：`/szw-wiki-ingest <resources/file>` 或 `/szw-wiki-ingest --from-inbox`

## 二、Query（查询）
（沿用 vault 4 步流程）
触发：`/szw-wiki-query <q>`
新增：好答案询问写入 connections/ 时标 derived: true

## 三、Lint（健康检查）
（沿用 vault 7 检查项 + szw 加项：）
- inbox/sources/ 中 read: true 但未迁移的项
- assets/<slug>/ 孤儿（无对应 resource）

## 四、特殊场景
（沿用 vault A/B/C/D）

## 五、自检清单
（沿用 vault）

## 六、Hub 维护
（沿用 vault）

## 七、【szw 新增】inbox → resources 迁移流程

### 触发
`/szw-wiki-ingest --from-inbox`

### 步骤（事务性）
1. 扫 inbox/sources/*.md，按 frontmatter `read` 字段分组
2. 对每个 read=true 项：
   a. 校验 frontmatter 必备字段（type / title / source / captured / lang）
      缺字段 → 询问补全
   b. 规范化 filename：`YYYY-MM-DD-<slug>.md`
   c. 处理附件路径：
      - 检测 markdown 内 `![[../../assets/<slug>/...]]` 引用
      - assets/<slug>/ 目录**不动**
      - 重写引用：`![[../../assets/...]]` → `![[../assets/...]]`
   d. 移到 resources/<new-name>.md
   e. **删除 inbox/sources/<old-file>**（不留备份）
   f. 触发标准 ingest（§一）
3. 失败时回滚：恢复 inbox 原文件、撤销 resources 写入、撤销 assets 引用 rewrite

### 不做的事
- 不自动判定 read=false → true
- 不修改原 inbox 正文
- 不跳过 frontmatter 校验
- 不删 assets/<slug>/ 目录及内容
```

---

## 附录 D：Karpathy 论断映射

| Karpathy 论断 | szw v2.1 落地 |
|---|---|
| "the wiki is a persistent, compounding artifact" | szw owner 持续维护自己的 wiki |
| "Cross-references are already there" | reverse.json 持续累积 |
| "You read it; the LLM writes it" | wiki/log.md / INDEX.md 由命令生成；用户走 `/szw-wiki-edit` 引导 |
| "Three layers" | 完整复刻：resources/+assets/ + wiki/ + (CLAUDE+AGENTS+CONVENTIONS+WORKFLOWS) |
| "Good answers can be filed back" | `/szw-wiki-query` 询问写入 connections/ 标 derived: true |
| "Index.md works at moderate scale" | INDEX.md + reverse.json 至 500 页足够 |
| "log.md grep-friendly" | wiki/log.md 沿用 `## [YYYY-MM-DD HH:MM] op | ...` |
| "intentionally abstract" | szw 是具体实例化，用户可在 CONVENTIONS / WORKFLOWS 微调 |
| "share with your LLM and instantiate together" | init 两询问 + 聚合机制让用户与 LLM 共演化 |

### Karpathy V2 update 机制借鉴

| V2 机制 | 落地 |
|---|---|
| `purpose.md`（知识库目标） | `EDITORIAL_CONTEXT.md` 即此 |
| 长文两阶段（先分析后生成） | `wiki/WORKFLOWS.md` §一决策树天然两阶段 |
| 可信度分级 | szw research 已有 risk(L/M/H) + confidence(high/medium/low) |
| SHA256 缓存 | `.zero/wiki-cache/content-hash.json` |
| 引用图谱删除 | `/szw-wiki-lint` 检测 + 用户决定 |
| Query 反写 + `derived: true` | `/szw-wiki-query` / `/szw-wiki-feedback` (v2) |
| SessionStart hook 自动感知 | `Column/.claude/settings.json` v3 加 |
| 兼容旧库 | `wiki.enabled=false` 时退化为 fan.md 原版 |

---

## 15. 下一步

落地需先拍板的实施级问题（v2.1 已大部分确定）：

| 项 | 状态 |
|---|---|
| CLAUDE.md re-init 策略 | ✅ 聚合（已拍板） |
| starter pack 时机 | ✅ v2（已拍板） |
| inbox/sources 迁移备份 | ✅ 不留（已拍板） |
| CLAUDE.md / AGENTS.md 模板 | ✅ 完整生成（见附录 A） |
| assets/ 设计 | ✅ 根级平铺，按 slug 子目录（已拍板） |
| vault.path 入 git | ✅ 不入（local config） |
| INDEX.md 链接格式 | ✅ `file:///` 绝对（默认） |

剩余待拍板（实现阶段再细化即可）：

- `wiki/log.md` 与 `.zero/STATE.md` 关系：保持分离（不同语义）
- 附件 git LFS 阈值：单文件 > 1MB 提示用 LFS（v2 加）
- merge prompt 冲突 > 5 时降级策略：先列冲突清单（v1.5 加）

确认后即可进入实施：

1. `scripts/{wiki-import,wiki-ingest,wiki-create-page}.py` 实现
2. `skills/write/szw-wiki-{import,ingest,create-page,query,suggest,lint}/SKILL.md` 实现
3. `szw-init` 大改（加询问流程 + 四件套生成 + 聚合机制）

---

## 附 E：参考资料

- 母方案：[`fan.md`](./fan.md)
- v1 / v2（被本稿替换）：见 git history
- vault 自身 schema：`SheanZero/{CLAUDE.md, conventions.md, workflows.md}`
- Karpathy 原文（vault ingested）：`SheanZero/4-resources/2026-04-10-karpathy-llm-wiki.md`
- vault wiki 概念页：`SheanZero/1-wiki/concepts/llm-wiki-pattern.md`
- Karpathy V2 update 笔记：`SheanZero/4-resources/2026-04-12-karpathy-skill-v2.md`
- vault essay engine 论点：`SheanZero/1-wiki/connections/wiki-as-essay-engine.md`
