# Column STATE

> 活记忆 —— 跨 session 第一件事读它。
> Updated: <YYYY-MM-DD>

## Active Articles

> 进行中的文章列表（非终态），按 `last_touched` 倒序。
> `/szw-progress` 显示这张表 + 全局推荐；`/szw-resume <slug>` 切换上下文。

| Slug | Status | Last touched | Next action |
|---|---|---|---|
| <slug> | <status> | <YYYY-MM-DD> | <suggested command> |

> 空表示无进行中文章，用 `/szw-new-article` 起新文章。

## Recently Completed

> 最近 N 篇已完成的文章（终态：completed / archived），按 `completed_at` 倒序，保留最近 10 条。

| Slug | Completed at | Disposition | Platforms |
|---|---|---|---|
| <slug> | <YYYY-MM-DD> | published / archived | blog, wechat |

## Column Status

- Initialized: <YYYY-MM-DD>
- Mode used at init: <A | B | B-reinit>
- Wiki enabled: <true | false>
- Wiki bootstrap: <none | seed-from-vault | empty-skeleton | skip>
- Articles in progress: <count>
- Articles published: <count>
- Articles archived: <count>
- Wiki pages: <count>
- Resources: <count>
- Inbox sources pending review: <count>

## Pending Decisions

- [ ] 用 /szw-progress 看下一步建议

## Recent Decisions

- (<date>) ADR 0001: no-benchmark-dumping
- (<date>) ADR 0002: tool-review-needs-action
- (<date>) ADR 0003: no-anxiety-farming

## Backlog

> 用 /szw-capture 加灵感

---

## Article Status 枚举

| Status | 由哪个命令进入 | 是否 active |
|---|---|---|
| `created` | `/szw-new-article` | ✅ |
| `brief_done` | `/szw-discuss` | ✅ |
| `research_done` | `/szw-research`（v2.0） | ✅ |
| `outline_done` | `/szw-outline`（v2.0） | ✅ |
| `draft_done` | `/szw-write` | ✅ |
| `review_failed` | `/szw-review` | ✅（最优先级） |
| `review_passed` | `/szw-review` | ✅ |
| `published` | `/szw-publish` | ✅ |
| `paused` | `/szw-pause`（v3.0） | ✅ |
| `completed` | `/szw-complete --published` | ❌（终态） |
| `archived` | `/szw-complete --archived` | ❌（终态） |
