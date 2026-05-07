---
name: szw-new-article
description: Create a new article project under the column with metadata, type, target platforms, and a dedicated working directory. Each article is its own project with ARTICLE.md and lifecycle status. Use when starting a new article, upgrading an inbox idea, or pulling the next article in a series. Asks for slug / type / platforms interactively, then writes ARTICLE.md and registers the article in STATE.md.
---

# szw-new-article

创建新 article 项目。包装 `scripts/new-article.py`，把交互式选 slug / type / platforms 留给 AI，把落盘和 STATE 更新留给脚本。

## 何时使用

- 想开新文章
- 从 inbox 灵感升级到正式文章
- 从 series 计划里拉下一篇
- 用户明确说"开一篇新的"

## 何时不用

- `.zero/` 不存在 → 先 `/szw-init`
- 想恢复某篇旧文章 → `/szw-resume <slug>`
- 想看现有 active 文章 → `/szw-progress`
- 想批量起草系列 → 用 `/szw-new-series`（v2.0），它内部会调用本命令

---

## 调用语法

| 形式 | 行为 |
|---|---|
| `/szw-new-article` | 默认：进入交互流程（询问 slug / type / platforms / 可选 inbox / 可选 series） |
| `/szw-new-article <topic>` | 给一个主题词；AI 据此推 slug 建议（仍需用户确认） |
| `/szw-new-article --from-inbox <slug>` | 从 inbox/pending/<slug>.md 升级 |
| `/szw-new-article --series <name>` | 关联到系列（要求 INDEX.md 已存在） |

底层脚本签名（非交互）：

```bash
scripts/new-article.py \
  --slug <slug> --type <type> \
  [--platforms <p1,p2>] [--title <title>] \
  [--from-inbox <slug>] [--series <name>]
```

---

## 执行流程

### Step 1：上下文检测
- 跑 `pwd` 确认在专栏目录（脚本会校验，但提前确认避免无效问询）
- 读 `.zero/szw-config.json` 拿 `default_platforms`（用于第 4 步默认值）

### Step 2：询问 slug
- 如果用户给了主题词（`/szw-new-article <topic>`）→ 推一个 slug：
  - 格式 `YYYY-MM-<topic-slug>`，年月用今天
  - topic 转 lowercase + 连字符（如 "Skills vs GSD" → `skills-vs-gsd`）
- 展示推荐："建议 slug：`2026-05-skills-vs-gsd`，这个可以吗？"
- 用户接受 → 记下；用户改 → 验证格式（regex `^[a-z0-9][a-z0-9-]*$`）

### Step 3：询问 article type
- 4 个选项（与 EDITORIAL_CONTEXT 对齐）：

| Type | 适用场景 |
|---|---|
| `industry-analysis` | 行业 / 趋势 / 工具生态分析（侧重判断） |
| `programmer-advice` | 程序员可执行的方法论 / 实践建议 |
| `product-analysis` | 单产品 / 工具的深度评测 |
| `tech-blog` | 通用技术博文（兜底） |

- 询问："这篇是哪种类型？industry-analysis / programmer-advice / product-analysis / tech-blog"
- 用户给完整名 / 给数字（1-4）/ 给关键词都接受

### Step 4：询问 target platforms
- 默认从 config 取（如 `[blog, wechat]`）
- 询问："发布到哪些平台？默认 `blog, wechat`，可改（合法值：blog / wechat / x / xhs）"
- 用户回车接受默认 / 输入逗号分隔列表

### Step 5：可选关联
- 如果调用带 `--from-inbox <slug>`：跳到第 6 步（已有 inbox 关联）
- 否则不主动问；用户主动提才接（如"这是 inbox 里那条 agentic-survey 的"）
- 如果调用带 `--series <name>`：同上

### Step 6：调用脚本
- 拼参数跑 `scripts/new-article.py`
- 退出码非 0 → 解释错误并询问下一步（重命名 / 取消等）

### Step 7：报告 + 推荐下一步
- 打印脚本输出
- 推荐：`/szw-discuss <slug>` 拷问选题

---

## 失败处理

| 退出码 | 含义 | 应对 |
|---|---|---|
| `0` | 成功 | — |
| `1` | 不在专栏目录 | 提示 `/szw-init` 或 cd 到专栏根 |
| `2` | slug 冲突（articles/<slug>/ 已存在） | 询问改 slug 或 `/szw-resume <slug>` 继续旧的 |
| `3` | slug 格式非法 | 给规则说明 + 让用户重新给 |
| `4` | type 非法 | 列 4 个合法值 + 让用户重选 |
| `5` | platform 非法 | 列 4 个合法值 + 让用户重选 |
| `6` | --from-inbox 文件不存在 | 列 inbox/pending/ 实际有什么文件 + 让用户改 |
| `7` | --series INDEX.md 不存在 | 提示 `/szw-new-series`（v2.0）或手建 INDEX.md |
| `8` | STATE.md 缺失或解析失败 | 跑 `parse-state.py validate`（来自 szw-progress）；从 git 回滚或修复 |

---

## Gates

- **Pre-flight**：`<cwd>/.zero/szw-config.json` 必须存在
- **Slug 唯一**：与 `articles/<slug>/` 撞名 → 阻断
- **Slug 格式**：regex 校验
- **Type 枚举**：4 选 1
- **Platform 枚举**：4 选 1
- **STATE.md 完整性**：必须含 `## Active Articles` 标题与表头
- **回滚**：STATE.md 写入失败时自动 `rmtree` 已创建的 `articles/<slug>/`

---

## 完成 marker

成功输出（脚本 stdout）：

```
✅ Created articles/<slug>/ARTICLE.md
   title: <title>
   type: <type>
   platforms: <p1, p2>
   [from inbox: <slug> (moved to inbox/done/)]
   [series: <name> (appended to INDEX.md)]
   STATE.md: row added to ## Active Articles

👉 Next: /szw-discuss <slug>
```

---

## 设计原则

1. **AI 问 / 脚本写**：交互式问答由 AI 控制；落盘 / 校验 / 状态更新交脚本（非交互）
2. **Slug 不可改**：创建后永久绑定到目录名 + STATE.md 行；改名 = 新文章
3. **thesis 留空**：`/szw-new-article` 不主动填 thesis，避免锁定 brief 阶段的拷问空间
4. **inbox 升级即移走**：从 pending → done，避免重复升级
5. **series 支持有限**：仅追加 INDEX.md 一行 bullet（schema 由 v2.0 `/szw-new-series` 定）
6. **原子性回滚**：STATE.md 更新失败时清理已创建的 article 目录（除 inbox 移动外，避免数据丢失）
7. **STATE.md 改动最小化**：只在 `## Active Articles` 表内插入新行；不动其他 section / 不动 Recently Completed 占位行

---

## 与其他命令的关系

- `/szw-init` —— 必须先初始化专栏（创建 .zero/szw-config.json + STATE.md）
- `/szw-progress` —— 创建后用它看 active 表；本命令不主动调
- `/szw-discuss` —— 下一步推荐命令
- `/szw-new-series`（v2.0） —— 创建系列；可批量调用本命令
- `/szw-capture` —— 把灵感入 inbox/pending/；可被本命令的 `--from-inbox` 消费
- `/szw-complete` —— 终结流水线；与本命令对应（创建 vs 完成）

---

## 输出示例

### 示例 1：交互式默认流程

用户：`/szw-new-article skills vs GSD`

```
🎯 准备创建新 article。

建议 slug：2026-05-skills-vs-gsd
要改吗？(回车接受 / 输入新值)

> （用户回车）

类型？
  1. industry-analysis  —— 行业/趋势/工具生态分析
  2. programmer-advice  —— 程序员可执行方法论
  3. product-analysis   —— 单产品深度评测
  4. tech-blog          —— 通用技术博文

> 1

发布平台？默认 blog, wechat（合法值：blog / wechat / x / xhs）

> （用户回车）

正在创建...

✅ Created articles/2026-05-skills-vs-gsd/ARTICLE.md
   title: Skills vs GSD
   type: industry-analysis
   platforms: blog, wechat
   STATE.md: row added to ## Active Articles

👉 Next: /szw-discuss 2026-05-skills-vs-gsd
```

### 示例 2：从 inbox 升级

用户：`/szw-new-article --from-inbox agentic-survey`

```
🎯 从 inbox/pending/agentic-survey.md 升级。

预览 inbox 内容（前 5 行）：
  # Agentic Coding Survey 灵感
  读了 OpenAI 最新 paper，发现 agent benchmark 评分跟实际工作流体验有巨大 gap。
  ...

建议 slug：2026-05-agentic-survey
要改吗？(回车接受 / 输入新值)

> 2026-05-benchmark-gap

类型？(1-4)

> 1

平台？默认 blog, wechat

> blog,wechat,x

正在创建...

✅ Created articles/2026-05-benchmark-gap/ARTICLE.md
   title: Benchmark Gap
   type: industry-analysis
   platforms: blog, wechat, x
   from inbox: agentic-survey (moved to inbox/done/)
   STATE.md: row added to ## Active Articles

👉 Next: /szw-discuss 2026-05-benchmark-gap
```

### 示例 3：slug 冲突

```
> /szw-new-article 2026-05-skills-vs-gsd（重复）

❌ articles/2026-05-skills-vs-gsd/ 已存在。

可能你想：
  1. 用不同 slug 创建新文章 → 改建议
  2. 继续旧文章 → /szw-resume 2026-05-skills-vs-gsd
  3. 看现有进度 → /szw-progress 2026-05-skills-vs-gsd

请选择，或给新 slug。
```

---

## 不实现的事

- **不修改 EDITORIAL_CONTEXT / ADR / 其他长期资产**：只创建 article 项目
- **不调用子 agent**：纯模板渲染 + 状态更新
- **不写 thesis**：那是 `/szw-discuss` Phase 2 的事
- **不打 grill 拷问**：同上
- **不更新 ROADMAP.md**：ROADMAP 是用户主动管理的（除 `/szw-new-series` 会动）
- **不 git commit**：用户决定何时提交；本命令只改文件
