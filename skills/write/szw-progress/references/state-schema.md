# STATE.md Schema

> `parse-state.py` 与 `/szw-progress` 依赖的 STATE.md 表结构契约。
> 也是未来 `szw-resume` / `szw-complete` 解析 STATE.md 的共同参考。
> 修改本文档须同步更新 `scripts/parse-state.py` 和 `skills/write/szw-init/templates/STATE.md`。

---

## 文件位置

`<column_root>/.zero/STATE.md`

`column_root` = 含 `.zero/` 的目录；从 cwd 向上递归查找。

---

## 必需的 H2 段落（按顺序）

| 段落标题（H2） | 内容 | 解析器消费 |
|---|---|---|
| `## Active Articles` | 进行中文章表（4 列） | `parse-state.py active` / `article` |
| `## Recently Completed` | 已完成文章表（4 列） | `parse-state.py completed` |
| `## Column Status` | 专栏全局指标（自由文本） | 暂不消费（v3.0 `/szw-stats` 会用） |
| `## Pending Decisions` | 待决任务（checkbox） | 暂不消费 |
| `## Recent Decisions` | 最近 ADR 引用（自由文本） | 暂不消费 |
| `## Backlog` | 灵感队列（自由文本） | 暂不消费 |

> 顺序非强制，但解析器以 H2 标题文本精确匹配定位段落，**标题措辞不可改**。

---

## `## Active Articles` 表 schema

| 列名 | 类型 | 必需 | 校验 |
|---|---|---|---|
| `Slug` | str | ✅ | 文章目录名；通常 `YYYY-MM-<topic>` 格式（弱约束） |
| `Status` | enum | ✅ | 必须在 9 个 active status 之一（见下） |
| `Last touched` | date | ✅ | `YYYY-MM-DD` 格式 |
| `Next action` | str | ⛔ 可空 | 命令字串提示，仅供参考；解析器有独立的 status→command 映射 |

### 9 个 active status

| Status | 入口命令 | 当前状态含义 |
|---|---|---|
| `created` | `/szw-new-article` | 文章项目刚建，无任何阶段产物 |
| `brief_done` | `/szw-discuss` | brief 写完 |
| `research_done` | `/szw-research`（v2.0） | 证据采集 + 诊断完成 |
| `outline_done` | `/szw-outline`（v2.0） | 大纲设计完成 |
| `draft_done` | `/szw-write` | 草稿起完 |
| `review_failed` | `/szw-review` | 反审有 HIGH issue（最高优先级修复） |
| `review_passed` | `/szw-review` | 反审通过 |
| `published` | `/szw-publish` | 已发布；待 `/szw-complete` 终结 |
| `paused` | `/szw-pause`（v3.0） | 用户主动暂停；`.continue-here` 留 handoff |

### 占位行过滤

模板里的占位行（如 `| <slug> | <status> | <YYYY-MM-DD> | <suggested command> |`）由解析器**自动跳过**：任何单元格匹配 `^<.*>$` 即视为占位。

---

## `## Recently Completed` 表 schema

| 列名 | 类型 | 必需 | 备注 |
|---|---|---|---|
| `Slug` | str | ✅ | 同 Active 表 |
| `Completed at` | date | ✅ | `YYYY-MM-DD` |
| `Disposition` | enum | ✅ | `published` / `archived` |
| `Platforms` | str | ⛔ | 已发平台（`blog, wechat, x, xhs` 子集），archived 时为 `-` |

保留最近 N 条（默认 10）；超出由 `/szw-complete` 自动 trim。

---

## 解析行为约定

### 已实现（`parse-state.py`）

- ✅ 自动跳过表头分隔行（`| --- | --- |`）
- ✅ 自动跳过占位行（`<...>` 形式单元格）
- ✅ 残缺行（列数与表头不符）跳过
- ✅ 全空行跳过
- ✅ H2 段落标题精确匹配
- ✅ 遇到下一个 H2 标题或文档结尾停止解析当前段落

### 未实现（暂不需要）

- ❌ 不支持表前/表后说明文本（blockquote / 段落自由文本被忽略）
- ❌ 不支持表内 inline code 或链接的特殊处理（按字面字串保留）
- ❌ 不支持表跨段落的延续

---

## 输出 JSON schema（供 AI 渲染参考）

### `active` 输出

```json
{
  "column_root": "/path/to/column",
  "active_count": 3,
  "articles": [
    {
      "slug": "2026-05-skills-vs-gsd",
      "status": "review_failed",
      "last_touched": "2026-05-06",
      "days_since_touched": 0,
      "state_md_hint": "/szw-write 2026-05-skills-vs-gsd S2 --mode polish",
      "next_command": "/szw-write",
      "next_command_full": "/szw-write 2026-05-skills-vs-gsd [section] --mode polish",
      "next_reason": "修复 review HIGH issue（最优先级）",
      "priority_rank": [0, 0],
      "article_dir": "articles/2026-05-skills-vs-gsd",
      "article_md_exists": true,
      "is_known_status": true
    }
  ],
  "global_recommendation": {
    "slug": "2026-05-skills-vs-gsd",
    "command": "/szw-write 2026-05-skills-vs-gsd [section] --mode polish",
    "status": "review_failed",
    "reason": "修复 review HIGH issue（最优先级）",
    "priority_bucket": "review_failed"
  }
}
```

字段说明：
- `priority_rank`: `[primary, secondary]`，主级 0=review_failed / 1=paused / 2=其他；次级 = -days_since
- `priority_bucket`: 全局推荐属于哪一桶（`review_failed` / `paused` / `stale` / `most_recent`）
- `state_md_hint`: STATE.md 自带的 Next action 列原值（仅供参考；不参与决策）
- `next_command_full`: 解析器按 status 推导的最终推荐（已带 slug 和 args_hint）

### `article <slug>` 输出

继承 `active` 单条结构，附加：

```json
{
  "artifacts": [
    {"file": "ARTICLE.md", "exists": true, "status_required": true},
    {"file": "01-brief.md", "exists": true, "status_required": false},
    {"file": "05-review.md", "exists": true, "status_required": true}
  ]
}
```

字段说明：
- `status_required: true` —— 当前 status 强约束此文件存在（缺失 = 状态不一致）
- `status_required: false` —— 历史产物，可能存在也可能不存在（取决于走 v1.0 还是 v2.0）

### `completed` 输出

```json
{
  "column_root": "/path/to/column",
  "completed_count": 2,
  "articles": [
    {"Slug": "...", "Completed at": "...", "Disposition": "...", "Platforms": "..."}
  ]
}
```

> 注意：`articles` 列名保留 STATE.md 表头的原大小写（含空格），便于 AI 直接渲染回 Markdown 表。

### `validate` 输出

```json
{
  "valid": true,
  "active_count": 3,
  "completed_count": 2,
  "issues": []
}
```

`issues` 为空数组时 valid=true，exit 0；非空时 valid=false，exit 3。

---

## 退出码契约

| Code | 含义 |
|---|---|
| 0 | 成功 |
| 1 | STATE.md 不存在 |
| 2 | 目标不存在（`article <slug>` 找不到 slug） |
| 3 | STATE.md 解析失败 / `validate` 报告 issues |

---

## 同步更新清单（变更 STATE.md schema 时）

- [ ] `skills/write/szw-init/templates/STATE.md` —— 模板要反映新 schema
- [ ] `skills/write/szw-progress/scripts/parse-state.py` —— 解析器跟上
- [ ] `skills/write/szw-progress/references/state-schema.md` —— 本文档
- [ ] `skills/write/szw-help/SKILL.md` —— "下一步推荐规则"表
- [ ] `study/fan.md` §3.0 —— 状态机定义
- [ ] 未来：`szw-resume/scripts/...` `szw-complete/scripts/...` 的相关脚本
