# Wiki Workflows

> 本文件定义 wiki/ 中 LLM 的核心工作流。
> CONVENTIONS.md 是命名 / frontmatter 约定；本文件是操作流程。

> Initialized: <YYYY-MM-DD>
> schema_version: 1.2

---

## 一、Ingest（摄入）

### 触发

用户运行：`/szw-wiki-ingest <resources/file>` 或 `/szw-wiki-ingest --from-inbox` 或 `/szw-wiki-ingest --batch`

### 前置条件

- 待处理文件在 `resources/` 中（如从 inbox 进入，先经迁移流程，见 §七）
- 该文件 frontmatter 完整（缺失则补全）
- `processed: false`

### 步骤

#### 1. 阅读

- 完整读取该 resource 文件正文
- 理解作者、观点、关键概念、时间背景
- 如果文件指向外部资源（PDF、视频）且本地有 `assets/<slug>/` 附件，一并查看

#### 2. 全局定位

- 读 `wiki/INDEX.md` 看现有 wiki 全貌
- 用 grep 或语义判断找到与本素材相关的现有 wiki 页
- 列出"将要触及的页面"清单（上限 15 页，仿 Karpathy 经验值）

#### 3. 决策树

对于本素材中的每个关键概念 / 人物 / 主题：

```
存在对应 wiki 页？
├── 是 → 这一页是否需要更新？
│   ├── 是 → 加入新观点 / 例证 / 链接
│   │       标注本素材为新来源
│   │       检查是否与现有内容矛盾
│   │       如矛盾：保留两种观点，标 ⚠️ 矛盾
│   └── 否 → 仅在 sources 列表追加本素材
└── 否 → 是否值得创建新页？
    ├── 是 → 在合适子目录创建（concepts/people/topics/frameworks/tools/connections）
    │       使用 stub 状态
    │       tools/ 专用于开源仓库 / 产品 / 技能集
    │       connections/ 专用于"跨页关联发现"
    │       hubs/ 不在 ingest 流程里创建——hub 是事后组织动作（见 §六）
    └── 否 → 仅在 wiki/log.md 留个标注，等更多素材积累
```

#### 4. 跨连接发现

- 本素材是否揭示了**已有 wiki 页之间的新关联**？
- 如果是，在 `wiki/connections/` 创建一个 connection 页
- connection 页的目的是描述"两个或多个事物之间的关系"，而非实体本身

例：
- `connections/wiki-vs-rag.md` — 比较两种知识检索范式
- `connections/karpathy-and-personal-knowledge.md` — Karpathy 多次发表的相关观点

#### 5. 记录溯源

每个修改 / 创建的 wiki 页：
- 在底部 `## Sources` 追加 `[[resources/YYYY-MM-DD-<slug>|标题]] (日期)`
- 在 frontmatter `sources` 数组追加该路径
- 更新 frontmatter `updated` 为今天

#### 6. 更新 resource 文件 frontmatter

仅修改 frontmatter，**不触碰正文**：

```yaml
processed: true
wiki_pages:
  - wiki/concepts/llm-wiki-pattern.md
  - wiki/people/andrej-karpathy.md
  - wiki/topics/personal-knowledge-management.md
summary: "Karpathy 提出的 LLM-Wiki 模式：让 LLM 持续维护一个结构化知识库"
```

#### 7. 更新 INDEX.md

- `wiki/INDEX.md`：如有新建页，在合适章节加一行
- `wiki/<type>/INDEX.md`：同上
- `resources/INDEX.md`：本素材按月分组追加

#### 8. 追加 log.md

```markdown
## [2026-04-10 14:30] ingest | karpathy-llm-wiki

- Source: [[resources/2026-04-04-karpathy-llm-wiki]]
- Created: [[wiki/concepts/llm-wiki-pattern]], [[wiki/people/andrej-karpathy]]
- Updated: [[wiki/topics/personal-knowledge-management]]
- Notes: 首次引入 LLM-Wiki 概念
```

#### 9. 更新反向索引

- `.zero/wiki-cache/reverse.json`：增量更新 by_tag / by_resource / by_wiki_page
- `.zero/wiki-cache/content-hash.json`：更新该页 SHA256

#### 10. 汇报用户

简短地告诉用户：
- 创建了哪些页
- 更新了哪些页
- 是否发现了矛盾或值得讨论的点
- **不要**在汇报里复制粘贴 wiki 页全文

### Ingest 反例（不要这样做）

- ❌ 一次 ingest 修改 30+ 文件（太大，难以审查；用 `--batch` 限 5 篇/批）
- ❌ 在 wiki 页里凭空补充原素材没有的观点
- ❌ 跳过 `## Sources` 章节
- ❌ 修改 resource 文件的正文
- ❌ 不更新 log.md

---

## 二、Query（查询）

### 触发

`/szw-wiki-query <自然语言问题>`

### 步骤

#### 1. 范围判断

- 事实性查询？→ 从 `wiki/` 找
- 溯源查询？→ 从 wiki sources 反查 `resources/`
- 综合性问题？→ 同时用 wiki 和 resources

#### 2. 检索

- 第一步：读 `wiki/INDEX.md`
- 第二步：读相关 wiki 页（用 frontmatter `related` 字段扩展）
- 第三步（必要时）：回 `resources/` 看原文细节

#### 3. 综合回答

- 直接回答问题
- 引用具体 wiki 页：`参见 [[wiki/concepts/foo]]`
- 引用原始来源：`原文出自 [[resources/2026-04-04-bar]]`
- 标注不确定性：观点在多源中存在分歧时明确指出

#### 4. 沉淀机会

如果回答本身是有价值的综合（对比分析 / 跨源洞察）：
- 询问用户："要不要把这个分析写入 `wiki/connections/<X>.md`？"
- 用户同意后才写，标 `derived: true`

### Query 反例

- ❌ 直接全文搜索 `resources/`，跳过 `wiki/INDEX.md`
- ❌ 不引用具体页面就给出答案
- ❌ 自动把 query 结果写入 wiki（需用户确认）

---

## 三、Lint（健康检查）

### 触发

`/szw-wiki-lint`

### 检查项

#### 1. 待 ingest 素材

- `resources/` 中所有 `processed: false` 的文件 → 列出
- `inbox/sources/` 中 `read: true` 但未迁移的项 → 列出

#### 2. 矛盾标记

- 搜索 `wiki/` 中包含 "⚠️ 矛盾" 或 "TODO" 的页面 → 列出，提供修订建议

#### 3. 孤立页

- 统计每个 wiki 页的入链数（被多少其他 wiki 页引用）
- 入链 = 0 的页面 → 列为孤立

#### 4. 缺独立页的高频概念

- 扫描 `wiki/` 中频繁出现但没有独立页的术语 / 人物
- 建议创建 stub 页

#### 5. 断链

- 检查所有 `[[...]]` 链接，目标文件是否存在 → 列出断链

#### 6. 长期未访问

- 基于 frontmatter `updated` 字段，找出 6 个月以上未更新的：
  - `status: stub` 的孤立页 → 建议合并或归档

#### 7. 来源失衡

- 某个 wiki 页的 sources 是否全部来自单一作者 / 单一时期 → 提醒多元化

#### 8. 附件孤儿（v2.1 新增）

- 扫 `assets/<slug>/` 中所有 slug
- 检测 `resources/<slug>.md` 是否存在；不存在 → 标 orphan

#### 9. resources 已 ingest 但 wiki_pages 空

- frontmatter `processed: true` 但 `wiki_pages: []` → 数据不一致

### Lint 输出格式

```markdown
# Wiki Health Report — 2026-04-10

## 待 ingest 素材 (3)
- resources/2026-04-09-paper-x.md (processed: false)
- inbox/sources/2026-04-10-blog-y.md (read: true, 待迁移)
- ...

## 矛盾待解决 (1)
- wiki/concepts/foo.md — 关于 X 的两种说法

## 孤立页 (2)
- wiki/concepts/orphan-1.md
- wiki/people/lonely-person.md

## 缺独立页 (3)
- "Transformer" 在 5 页提及但无独立页
- "Mamba" 在 3 页提及但无独立页

## 断链 (1)
- wiki/topics/foo 引用 [[concepts/missing]]

## 附件孤儿 (1)
- assets/2026-05-01-baz/  (无对应 resources/2026-05-01-baz.md)

## 归档建议 (1)
- wiki/concepts/old-stub (上次更新 2025-09-15, status: stub, 无入链)
```

写入 `.zero/wiki-cache/orphans.json`。

### Lint 重要原则

- **只报告，不执行**——所有归档 / 合并 / 删除必须用户确认
- **优先级排序**——把"待 ingest"放最前，因为最有行动力
- **不建议清理健康内容**——`status: active|mature` 且有入链的不要碰

---

## 四、特殊场景

### A. 用户请求处理 articles/<slug>/ 中的文件

- 这不是 ingest——articles/ 不进 wiki
- 可帮助：整理结构、写 brief / draft、做文章复盘
- **不要**把 articles/ 内容写入 wiki/

### B. 用户在 articles/<slug>/RETRO.md 写了有洞察的复盘

- 默认不动
- 用户明确说"把这个洞察提取到 wiki" → 走 `/szw-wiki-feedback <slug>`（v2）
  - 提取**判断 / 连接**，不进 essay 全文
  - 写到 `wiki/connections/<X>.md` 标 `derived: true`

### C. 批量 ingest

- 用户说"把今天加的全部处理"
- 列出待处理文件
- 询问"共 N 篇，逐一处理还是按主题分组？"
- 一次最多处理 5 篇（`limits.ingest_batch_max`），处理完汇报后再继续
- 每篇之间保持独立，不合并 log

### D. 发现一个素材"无法分类"

- 不要硬塞进某个子目录
- 在 log.md 留下标注，建议用户思考新主题
- 该素材独立成立时，可放进 `wiki/topics/` 作为单一来源页（status: stub）

---

## 五、自检清单

每次完成 ingest 后自查：

- [ ] resource 文件 frontmatter 已更新（processed / wiki_pages / summary）
- [ ] 所有 wiki 修改都有对应的 sources 引用
- [ ] wiki/INDEX.md + 类目录 INDEX.md 已更新
- [ ] log.md 已追加条目
- [ ] reverse.json 已增量更新
- [ ] 没有触碰 resource 文件正文
- [ ] 没有从 articles/ 写入任何东西
- [ ] 给用户的汇报简短清晰

---

## 六、Hub（MOC 导航页）维护

### 何时创建 hub

- wiki 页 > 20 且某主题 / 方法聚合 5+ 相关页时
- 用户明确请求："给 X 做个 hub"
- lint 发现某高入链主题缺入口页时

### hub 不是什么

- **不是** topic 页的替代品（topic 写综述，hub 只导航）
- **不是** 新知识沉淀（不应包含 source 中没有的内容）
- **不是** 必须建的（页数不够时是空壳）

### hub 页结构

```markdown
---
type: hub
title: "..."
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: []
related: [...]
status: active
tags: [hub, ...]
---

# 标题

> 一句话：这个 hub 解决什么导航问题

## 快速入口（3-5 个核心页）

- [[...|名称]] — 一句话为什么是入口

## 全景图（按子主题分组）

### 子主题 A
- [[...|名称]] — 一句话说明

## 推荐阅读顺序

1. ...
2. ...

## 相关 hub

- [[hubs/...|其他 hub]]
```

### hub 维护

- 每次新建 topic / concept / tool 页后，检查是否该加入某 hub 的"全景图"
- hub 页 `updated` 字段跟随子主题实质性变化，不跟随每次加链

---

## 七、inbox → resources 迁移流程（v2.1 新增）

### 触发

`/szw-wiki-ingest --from-inbox`

### 步骤（事务性，失败回滚）

#### 1. 扫描

扫 `inbox/sources/*.md`，按 frontmatter `read` 字段分组：
- `read: true` → 进入迁移 + ingest 流程
- `read: false` → skip（列出来供用户参考）

#### 2. 迁移每个 read=true 项

##### 2.1 校验 frontmatter

必备字段：`type` / `title` / `source` / `captured` / `lang`

缺字段 → 询问用户补全；**不擅自填默认**。

##### 2.2 规范化 filename

- 从 `captured` 取 `YYYY-MM-DD`
- 从 `title` 派生 `slug`（小写连字符）
- 新文件名：`YYYY-MM-DD-<slug>.md`
- slug 冲突（resources/ 已有同名）→ 询问改名

##### 2.3 处理附件路径

- 检测 markdown 内 `![[../../assets/<slug>/...]]` 引用
- `assets/<slug>/` 目录**不动**（不重命名 / 不移动）
- 重写引用：

  ```
  from: ![[../../assets/<slug>/img.jpg]]   (inbox/sources/ → assets/，深 2 层)
  to:   ![[../assets/<slug>/img.jpg]]      (resources/ → assets/，深 1 层)
  ```

  实质：用 regex `!\[\[\.\./\.\./assets/` → `!\[\[\.\./assets/`

##### 2.4 移动文件

`inbox/sources/<old-file>.md` → `resources/<YYYY-MM-DD-slug>.md`

##### 2.5 删除 inbox 原文件

不留备份。assets 是唯一保留的二进制资源。

##### 2.6 触发标准 ingest

走 §一 决策树。

#### 3. 失败回滚

任何步骤失败：
- 恢复 `inbox/sources/<old-file>.md`
- 撤销 `resources/<new-file>.md` 写入
- 撤销 markdown 内附件路径 rewrite
- assets/ 目录不动（迁移流程中本就不动）

#### 4. 输出

```
✅ Migrated + ingested 3 sources
   - inbox/sources/2026-05-04-foo.md → resources/2026-05-04-foo.md
   - inbox/sources/2026-05-05-bar.md → resources/2026-05-05-bar.md
   - inbox/sources/2026-05-05-baz.md → resources/2026-05-06-baz.md (slug renamed)

Wiki pages touched: 9
   created: wiki/concepts/X / wiki/people/Y
   updated: wiki/topics/Z / ...

Skipped (read=false): 2
   - inbox/sources/2026-05-06-todo.md
   - inbox/sources/2026-05-06-pending.md
```

### 不做的事

- 不自动判定 `read=false` → `true`（必须用户显式标）
- 不修改原 inbox 正文（除附件路径 rewrite）
- 不跳过 frontmatter 校验
- 不删 `assets/<slug>/` 目录及内容
