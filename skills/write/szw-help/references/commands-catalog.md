# szw Commands Catalog

> 26 个命令，按 8 类组织。`v1.0` / `v2.0` / `v3.0` 标注交付阶段。
> Last updated: 2026-05-06

## 1. 专栏生命周期 (3)

| 命令 | 版本 | 用途 |
|---|---|---|
| `/szw-init` | v1.0 | 初始化专栏（自动生成 COLUMN.md / EDITORIAL_CONTEXT.md / ADR / 目录骨架；Mode A 空目录 / Mode B review 已有文件） |
| `/szw-stats` | v3.0 | 专栏数据统计（已发文章 / 在写 / 计划中） |
| `/szw-summary` | v3.0 | 周期汇总（季度 / 年度回顾） |

## 2. 创建入口（项目化） (2)

| 命令 | 版本 | 用途 |
|---|---|---|
| `/szw-new-article` | v1.0 | 创建单篇文章项目（含 ARTICLE.md 元数据，可关联 inbox / series） |
| `/szw-new-series` | v2.0 | 创建多篇连载系列（series-planner 起草大纲，可立即拉第一篇） |

## 3. 文章主流水线 (7)

| 命令 | 版本 | 用途 | 参与度 |
|---|---|---|---|
| `/szw-discuss` | v1.0 | 选题讨论拷问 + 文章 brief（合并；Phase 1 拷问 + Phase 2 结构化） | ★★★★★ HIGH |
| `/szw-research` | v2.0 | 证据采集 + 判断诊断（合并 Codex 双阶段；HIGH-risk 内部循环） | ★★★★ HIGH-MED |
| `/szw-outline` | v2.0 | 论证地图 + 章节拆片（合并；弱 section 内部循环） | ★★★★★ HIGH |
| `/szw-write` | v1.0 | 起稿 + 润色（合并；支持全文 / 章节模式；写作历史日志；加载 style-profile） | ★★★★★ HIGH |
| `/szw-review` | v2.0 | 反方审稿 + 风格捕获（Codex；Phase 2 学习作者风格） | ★★ LOW-MED |
| `/szw-publish` | v1.0 | 多平台打包（blog / wechat / x / xhs） | ★★ LOW |
| `/szw-complete` | v1.0 | 终结文章流水线（active → completed / archived；可选触发 retro） | ★ LOW |

## 4. 轻量出口 (2)

| 命令 | 版本 | 用途 |
|---|---|---|
| `/szw-capture` | v2.0 | 灵感入 inbox（不打断当前工作） |
| `/szw-quick` | v2.0 | 短评直出（≤ 800 字，跳过完整流水线） |

## 5. 长期资产维护 (4)

| 命令 | 版本 | 用途 |
|---|---|---|
| `/szw-context` | v1.0 | 维护 EDITORIAL_CONTEXT.md（术语 / 边界 / 风格演进） |
| `/szw-adr` | v1.0 | 创建 / 更新编辑决策记录 |
| `/szw-glossary` | v3.0 | 单术语长定义维护（glossary/<term>.md） |
| `/szw-evidence-bank` | v3.0 | 证据银行管理（标记 STALE / 退役） |

## 6. 进度路由 (3)

| 命令 | 版本 | 用途 |
|---|---|---|
| `/szw-progress` | v1.0 | 列**所有 active articles** 进度 + 各自下一步推荐（`<slug>` 详情、`--next` 推荐最该做的、`--do "<text>"` 路由、`--completed` 看已完成） |
| `/szw-resume` | v1.0 | **指定 article** 跨 session 恢复（默认 last_touched / `<slug>` 指定 / `--list` 多 article 切换） |
| `/szw-pause` | v3.0 | 留 handoff（`.zero/.continue-here`） |

## 7. 复盘 (2)

| 命令 | 版本 | 用途 |
|---|---|---|
| `/szw-retro` | v3.0 | 发布后复盘（数据 + 反馈 → ADR / 术语候选） |
| `/szw-audit` | v3.0 | 专栏一致性审计（术语漂移 / ADR 违反 / 风格漂移） |

## 8. 系列管理 (1)

| 命令 | 版本 | 用途 |
|---|---|---|
| `/szw-series` | v3.0 | 系列管理（`--list` / `--status` / `--reorder` / `--complete`；创建用 `/szw-new-series`） |

## 9. 配置 (2)

| 命令 | 版本 | 用途 |
|---|---|---|
| `/szw-help` | v1.0 | 命令参考（本命令） |
| `/szw-config` | v1.0 | 配置 model profile / 默认平台 / hooks / 风格捕获 |

---

## 完整流水线示意（v2.0）

```
/szw-init  (一次性初始化)
   ↓
/szw-new-article  ──→  /szw-discuss  ──→  /szw-research  ──→  /szw-outline
                                                                   ↓
   ┌────────────────────────────────────────────────────────────────┘
   ↓
/szw-write  ←──→  /szw-review  (循环：HIGH issue 回 write polish)
   ↓
/szw-publish  ──→  /szw-complete   (终结：active → Recently Completed)
```

## 多 article 并行模型

每个 article 在 ARTICLE.md 里有 `status` 字段；STATE.md 的 Active Articles 表同时记录多篇文章。
所有流水线命令都接受 `<slug>` 参数定位具体 article；不指定时按 STATE.md `last_touched` 取默认。
使用 `/szw-progress` 看全局进度，`/szw-resume <slug>` 在文章间切换。

## 各阶段产物文件

| 文件 | 产出命令 | 位置 |
|---|---|---|
| `01-brief.md` | `/szw-discuss` | `articles/<slug>/` |
| `02-research.md` | `/szw-research` | `articles/<slug>/` |
| `03-outline.md` | `/szw-outline` | `articles/<slug>/` |
| `04-draft.md` | `/szw-write` | `articles/<slug>/` |
| `05-review.md` | `/szw-review` | `articles/<slug>/` |
| `06-platform-package.md` | `/szw-publish` | `articles/<slug>/` |
| `published/<slug>/{blog,wechat,x,xhs}.md` | `/szw-publish` | `<cwd>/published/` |
| `.zero/style-profile.md` | `/szw-review` Phase 2 | `<cwd>/.zero/` |
| `.zero/writing-history/<slug>/` | `/szw-write` 每次调用 | `<cwd>/.zero/` |
