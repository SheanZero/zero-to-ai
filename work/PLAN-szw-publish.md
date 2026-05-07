# szw-publish 开发计划

> 自包含的开发蓝图。下个 session 直接读这一份就能开干。
> 设计源：`study/fan.md` §3.5
> 输出路径：`/Users/xinz/Development/zero-to-ai/skills/write/szw-publish/`
> 一句话定位：把 `04-draft.md` 按 `target_platforms` 切成多份平台适配版本，输出到 `published/<slug>/`，推 status `review_passed → published`。**v1.0 流水线收尾节点**。

---

## Step 1：恢复上下文（必读，10 分钟）

按顺序读：

| # | 文件 | 重点 | 时间 |
|---|---|---|---|
| 1 | `work/HANDOFF.md` | 累积工作记录 + 已建 skill 清单 + 架构决策 | 4 分钟 |
| 2 | `work/REVIEW-2026-05-06.md` | 一致性审计 + 16 个未完成 skill 优先级 + 已发现的 P0/P1 问题 | 3 分钟 |
| 3 | `study/fan.md` §3.5 | szw-publish 设计源 | 1 分钟 |
| 4 | `skills/write/szw-review/SKILL.md` | 上游 skill 范式（最新建的；遵照其结构） | 2 分钟 |
| 5 | `skills/write/szw-review/scripts/finalize-review.py` | helper 函数复用模板 | 浏览即可 |

**关键背景**：

- v2.0 主流水线已闭环到 review；v1.0 缺 publish + complete + resume + context + adr
- szw-topic-grill 是被 szw-discuss 包装的 legacy skill
- 风格学习闭环已落地（write history snapshot → review Phase 2 difflib diff → `.zero/style-profile.md` → write 必读）
- claim ID `C<n>` / section ID `S<n>` 跨脚本共享同一规则
- 4 种 verdict gate 模式已建立（outline 二态 / research 三态 / write status 双轨 / review HIGH/passed 互斥）
- 架构决策：**self-contained skills**（不建 `_shared/`）；helper 函数直接拷贝，schema 文档化保证规则一致

**已知待修但本任务可暂缓**（建议建 publish 时直接用"对的"模式）：
- `next_action` 字串带 slug 不一致（5 处不带 / 1 处带）。**publish 直接写带 slug 版本**，对齐 review。
- fan.md 引用 EDITORIAL_CONTEXT §10/§11/§12/§15 但模板只到 §7。**publish SKILL.md 引用按模板实际节号（§3 / §7）**。

---

## Step 2：szw-publish 设计

### 2.1 输入 / 输出 / 状态

| 维度 | 内容 |
|---|---|
| 触发前置 | 04-draft.md 存在；status ∈ {`review_passed`（最优）, `draft_done`（允许带 warning）, `published`（重发）} |
| 输入文件 | `04-draft.md`（必需） + `ARTICLE.md`（拿 title/type/target_platforms） + `01-brief.md`（thesis 摘要） + EDITORIAL_CONTEXT §3 §7 + `style-profile.md`（如有） |
| 输出文件 | `published/<slug>/{blog,wechat,x,xhs}.md`（按 target_platforms 切几份） |
| 状态推进 | `review_passed → published`（自动）；`draft_done → published`（允许，但 warning） |
| 状态拒绝 | `review_failed → published` 拒绝（exit 6，必须先 review 过） |
| STATE.md next | `/szw-complete <slug>`（**带 slug**，对齐 REVIEW P0-2） |
| 不修改 | brief / outline / research / draft / writing-history / style-profile（纯下游消费） |

### 2.2 架构（4 个文件，标准模式）

```
skills/write/szw-publish/
├── SKILL.md
├── scripts/
│   ├── prepare-publish.py    # Phase 0：上下文 + 校验
│   └── finalize-publish.py   # Phase 3：commit；JSON 收 4 份平台 markdown
└── references/
    ├── publish-schema.md      # stdin JSON 契约 + 平台校验规则
    └── platform-format.md     # 4 平台格式约定（字数 / markdown / 图片 / 风格）
```

**不需要 templates/**（每平台格式由 AI 渲染；脚本只管落盘）。

---

## Step 3：脚本接口设计

### 3.1 `prepare-publish.py [--slug <slug>]`

**默认路由优先级**（拷贝自 prepare-review.py 的相同 STATUS_PRIORITY 模板）：

```python
STATUS_PRIORITY = ["review_passed", "draft_done", "published"]
# review_passed > draft_done（首次发） > published（重发）
```

**输出 JSON**：

```json
{
  "column_root": "...",
  "slug": "2026-05-foo",
  "current_status": "review_passed",
  "title": "Skills vs GSD",
  "type": "industry-analysis",
  "target_platforms": ["blog", "wechat"],
  "article_md_path": "articles/2026-05-foo/ARTICLE.md",
  "draft_md_path": "articles/2026-05-foo/04-draft.md",
  "brief_md_path": "articles/2026-05-foo/01-brief.md",
  "review_md_path": "articles/2026-05-foo/05-review.md",
  "long_term_assets": {
    "editorial_context": "EDITORIAL_CONTEXT.md",
    "style_profile": ".zero/style-profile.md",
    "adrs": [{"id":"0001","title":"...","path":"..."}],
    "glossary": [{"term":"...","path":"..."}]
  },
  "publish_dir": "published/2026-05-foo",
  "existing_published_files": ["blog.md", "wechat.md"],
  "warnings": []
}
```

**warnings 触发场景**：
- `current_status == "draft_done"` → "未跑过 review 直接发布；建议先 /szw-review"
- `current_status == "published"` → "重发场景；finalize 默认覆盖 published/<slug>/"
- `current_status == "review_failed"` → 在 prepare 阶段已经 exit 5（见下）
- target_platforms 为空 → "未配置发布平台；finalize 会拒绝"

**退出码**：

| Code | 含义 |
|---|---|
| 0 | 成功 |
| 1 | 不在专栏目录 |
| 2 | slug / ARTICLE.md / 04-draft.md 不存在 |
| 3 | STATE.md 缺失 / 解析失败 |
| 4 | ARTICLE.md frontmatter 解析失败 |
| 5 | status 不在允许集合（拒绝 review_failed → publish） |

### 3.2 `finalize-publish.py commit --slug <slug>`

**stdin JSON schema**：

```json
{
  "platforms": {
    "blog": "# Title\n\n完整 markdown，最长 / 可保留所有 markdown 语法...",
    "wechat": "# Title\n\n微信适配版本...",
    "x": "Tweet 1: ...\n\n---\n\nTweet 2: ...",
    "xhs": "✨ 标题\n\n小红书风格..."
  },
  "diff_from_draft": {
    "blog": "几乎原样保留，仅修小拼写",
    "wechat": "压扁 H4→H3；外链化 1 张图；首段口语化",
    "x": "拆 8 推 thread；首推 hook；末推 CTA",
    "xhs": "重写引子；删除 §4 仅保留 5 个决策卡片"
  },
  "advance_status_to": "published",
  "notes": "首次发布；wechat 版本字数 3.2k 在公众号合理区间"
}
```

**字段约束**：

| 字段 | 类型 | 必需 | 说明 |
|---|---|---|---|
| `platforms` | dict[str, str] | ✅ | key 必须 == ARTICLE.md.target_platforms 集合；value 非空 markdown 字串 |
| `diff_from_draft` | dict[str, str] | ✅ | 每平台一行简述；INDEX / Status Log 用 |
| `advance_status_to` | enum/null | ⛔ | `"published"` 或 `null`（dry-run 不动 status） |
| `notes` | str | ⛔ | 整体说明 |

**校验逻辑**：

```python
target = set(fm.get("target_platforms") or [])
submitted = set(data["platforms"].keys())

if not target:
    return 4, "ARTICLE.md.target_platforms is empty"

extra = submitted - target
if extra:
    return 4, f"platforms 含 ARTICLE.md.target_platforms 之外的 key: {sorted(extra)}"

missing = target - submitted
if missing:
    return 4, f"target_platforms 要求 {sorted(missing)}，platforms JSON 未给"

for p, content in data["platforms"].items():
    if not isinstance(content, str) or not content.strip():
        return 4, f"platforms.{p} must be non-empty string"

if data.get("advance_status_to") not in {"published", None}:
    return 4, "advance_status_to must be 'published' or null"
```

**Status gate**（advance）：

```python
ADVANCEABLE_FROM = {"review_passed", "draft_done", "published"}
# review_passed: 主路径
# draft_done: 跳过 review 强发（warning 但允许）
# published: 重发不变 status

if data.get("advance_status_to") == "published":
    if current_status not in ADVANCEABLE_FROM:
        return 6, f"cannot advance to published from status='{current_status}'"
# advance_status_to=null → 不动 status，仅落盘 + 刷 last_touched
```

**动作步骤**：

1. `mkdir -p published/<slug>/`
2. 每平台 `published/<slug>/<platform>.md` 覆盖式写入
3. 改 ARTICLE.md frontmatter：
   - status → published（如 advance）
   - Status Log 追加：`<date>: published via /szw-publish (platforms: blog, wechat)`
4. 改 STATE.md Active 行：
   - status: published（如 advance；否则保持）
   - last_touched: today
   - next_action: `/szw-complete <slug>`（**带 slug**）
5. 输出完成 marker

**退出码**：

| Code | 含义 |
|---|---|
| 0 | 成功 |
| 1 | 不在专栏目录 |
| 2 | slug / ARTICLE.md / 04-draft.md 不存在 |
| 3 | STATE.md 缺失 / row 找不到 |
| 4 | stdin JSON 缺字段 / 字段值非法 / platforms 与 target_platforms 不匹配 |
| 5 | _（保留）_ |
| 6 | status 转移非法（advance to published from review_failed / 其他） |

**完成 marker**：

```
✅ Published <slug>
   platforms: blog, wechat (2 files)
   wrote: published/<slug>/blog.md
   wrote: published/<slug>/wechat.md
   updated: articles/<slug>/ARTICLE.md (status → published)
   updated: STATE.md (next: /szw-complete <slug>)

👉 Next: /szw-complete <slug>
```

---

## Step 4：关键实现要点

### 4.1 直接拷贝 helper（不要重写）

按 self-contained 决策，从既有 finalize 拷贝（md5 一致原则）：

| 函数 | 拷自 | 备注 |
|---|---|---|
| `find_column_root()` | 任一 finalize-*.py | 5 处实现一致 |
| `parse_active_table_rows()` | 任一 prepare-*.py | 5 处实现一致 |
| `parse_frontmatter()` | 任一 prepare-*.py | 5 处实现一致 |
| `find_active_section_bounds()` | szw-outline/research/review/write 任一 | **3-tuple 版本**；不要拷 szw-discuss 的 4-tuple 版 |
| `update_active_row()` | 任一 finalize-*.py | 5 处实现一致 |
| `update_article_frontmatter()` | szw-outline/finalize-outline.py | **标准版**（4 参数）；不要拷 szw-discuss 的重载版 |

### 4.2 next_action 必须带 slug（修 P0-2）

```python
new_next_action=f"/szw-complete {slug}"   # ✅
# 不要写
new_next_action="/szw-complete"           # ❌ outlier
```

publish 直接写正确版本；之后回过头修前面 5 处 outlier 时一并对齐。

### 4.3 Platform 校验逻辑（关键）

ARTICLE.md.target_platforms 是真相。stdin 的 platforms key 必须**严格等于** target_platforms 集合：
- 多 → 拒绝（防止用户偷加平台没在 brief 里同意过）
- 少 → 拒绝（强制完整发布；如果想跳过某平台，先 /szw-config 改默认 / 改 ARTICLE.md.target_platforms）

### 4.4 重发处理

`existing_published_files` 在 prepare 输出，让 AI 知道是重发。finalize **默认覆盖**：
- 不做 backup（用户想保旧版用 git）
- 不问 confirm（重发是常见操作）
- 重发不强制 advance status（current=published + advance=published 仍允许，相当于 noop status + 刷 last_touched）

### 4.5 Status Log 格式

```python
extra_log = f"published via /szw-publish (platforms: {', '.join(sorted(submitted_platforms))})"
```

如果 advance_status_to=null（dry-run / 不动 status）：

```python
extra_log = f"publish iteration via /szw-publish (platforms: {', '.join(...)}; status unchanged={current_status})"
```

---

## Step 5：4 平台格式约定

写到 `references/platform-format.md`。给 AI 起稿各平台版本时参考。

| 平台 | 字数 | Markdown 支持 | 图片 | 风格特点 |
|---|---|---|---|---|
| `blog` | 不限 | 完整（H1-H6 / 表格 / 代码 / 列表 / 引用 / 链接）| 相对路径 OK | 原汁原味；几乎 = 04-draft.md；可保留所有 §<n> 节 |
| `wechat` | 通常 2k-5k | H3 起（H1 / H2 压平为加粗段） | **必须外链 URL**（公众号不能传相对路径） | 公众号风格；段短；标题口语化；适度加 emoji；不支持表格内嵌图 |
| `x` | 每推 ≤ 280 chars | 纯文本 + 链接（无 markdown） | 外链或拆开附图 | thread 拆 5-10 推；首推 hook；末推 CTA + 文章链接；用 `\n\n---\n\n` 分推 |
| `xhs` | ~800-1500 字 | 纯文本 + emoji | 外链 | 短句；段落多；视觉间隔大；标题带 emoji；首段抓眼球；结尾带 # tag |

**节结构对应**：

| 04-draft.md | blog | wechat | x | xhs |
|---|---|---|---|---|
| `# Title` | 保留 | 加粗段 | 首推主标题 | 加 emoji 标题 |
| `## §<n>. <title>` | 保留 | H3 标题 | 每节拆 1-3 推 | 标题带 emoji + 段落空行 |
| 表格 | 保留 | **拆 bullet 或外链截图** | 不支持 → 改 bullet | 不支持 → 改 bullet |
| 代码块 | 保留 | 保留（公众号支持）| **不支持 → 文字描述** | **不支持 → 文字描述** |
| 链接 | `[text](url)` | `[text](url)` | 直贴 url | 直贴 url 或 "见简介链接" |

---

## Step 6：测试 fixture（端到端验证）

```bash
mkdir -p /tmp/szw-pub/.zero /tmp/szw-pub/articles/2026-05-foo /tmp/szw-pub/published

cat > /tmp/szw-pub/.zero/szw-config.json << 'EOF'
{"version":"1.0","default_platforms":["blog","wechat"]}
EOF

cat > /tmp/szw-pub/.zero/STATE.md << 'EOF'
# Column STATE

## Active Articles

| Slug | Status | Last touched | Next action |
|---|---|---|---|
| 2026-05-foo | review_passed | 2026-05-06 | /szw-publish 2026-05-foo |

## Recently Completed

| Slug | Completed at | Disposition | Platforms |
|---|---|---|---|
| <slug> | <YYYY-MM-DD> | published | blog |
EOF

cat > /tmp/szw-pub/articles/2026-05-foo/ARTICLE.md << 'EOF'
---
slug: 2026-05-foo
title: Foo
type: industry-analysis
target_platforms: [blog, wechat]
status: review_passed
created_at: 2026-05-01
linked_series: null
linked_inbox: null
---

# Foo

## Thesis
T

## Status Log
- 2026-05-06: draft_done via /szw-write
- 2026-05-06: review_passed via /szw-review
EOF

cat > /tmp/szw-pub/articles/2026-05-foo/01-brief.md << 'EOF'
# 01-brief
## Thesis
T
EOF

cat > /tmp/szw-pub/articles/2026-05-foo/04-draft.md << 'EOF'
# Foo

## §1. 第一节
test
EOF

cat > /tmp/szw-pub/articles/2026-05-foo/05-review.md << 'EOF'
# 05-review
verdict: review_passed
EOF

# T1 prepare
cd /tmp/szw-pub && prepare-publish.py
# 期望：slug=2026-05-foo, target_platforms=[blog,wechat], current_status=review_passed

# T2 commit happy path
cat > /tmp/pub.json << 'EOF'
{
  "platforms": {
    "blog": "# Foo\n\n## §1. 第一节\ntest blog version",
    "wechat": "**Foo**\n\n### 第一节\ntest wechat version"
  },
  "diff_from_draft": {"blog":"原样","wechat":"压扁 H1→bold"},
  "advance_status_to": "published",
  "notes": "first publish"
}
EOF
cd /tmp/szw-pub && finalize-publish.py commit --slug 2026-05-foo < /tmp/pub.json
# 期望 exit 0
# 验证：
# - published/2026-05-foo/blog.md 和 wechat.md 存在
# - ARTICLE.md status: review_passed → published
# - STATE.md next: /szw-complete 2026-05-foo

# T3 platforms 缺 wechat → exit 4
echo '{"platforms":{"blog":"x"},"diff_from_draft":{"blog":"x"},"advance_status_to":"published"}' \
  | finalize-publish.py commit --slug 2026-05-foo
# 期望 exit 4：target_platforms 要求 ['wechat']

# T4 platforms 多 x → exit 4
echo '{"platforms":{"blog":"x","wechat":"x","x":"x"},"diff_from_draft":{"blog":"x","wechat":"x","x":"x"},"advance_status_to":"published"}' \
  | finalize-publish.py commit --slug 2026-05-foo
# 期望 exit 4：含意外 key ['x']

# T5 status 错误转移
# 先把 ARTICLE 改回 draft_done + STATE 同步
sed -i.bak 's/status: published/status: review_failed/' /tmp/szw-pub/articles/2026-05-foo/ARTICLE.md
sed -i.bak 's/| 2026-05-foo | published.*/| 2026-05-foo | review_failed | 2026-05-06 | \/szw-write 2026-05-foo S1 --mode polish |/' /tmp/szw-pub/.zero/STATE.md

cat /tmp/pub.json | finalize-publish.py commit --slug 2026-05-foo
# 期望 exit 6：cannot advance to published from review_failed

# 清理
rm -rf /tmp/szw-pub /tmp/pub.json
```

---

## Step 7：完成后的 HANDOFF / REVIEW 更新

完成 szw-publish 后：

1. **HANDOFF.md** 更新：
   - "Last updated" 加 szw-publish
   - 已建 skills 树状图加新行
   - 各脚本测试通过项加 prepare-publish.py / finalize-publish.py
   - §4.1 优先 skills 列表把 szw-publish 标 ✅
   - "v2.0 主流水线已闭环到 publish" 里程碑
   - quick-start 提示更新（下一步推荐 szw-complete）

2. **REVIEW-2026-05-06.md** 不需更新（这是审计快照，不是活文档）

3. 视情况修 P0-2（next_action 带 slug）的 5 处 outlier，让所有 finalize 风格一致

---

## Step 8：建议工作顺序（45-60 分钟）

| Step | 任务 | 时间 |
|---|---|---|
| 1 | 读 HANDOFF / REVIEW / fan.md §3.5 / 参考 review SKILL | 10 分钟 |
| 2 | mkdir + 拷 helper 函数到 `prepare-publish.py` | 5 分钟 |
| 3 | 写 prepare-publish.py 的业务逻辑（routing / publish_dir 列表） | 10 分钟 |
| 4 | 写 finalize-publish.py（拷 update_active_row + update_article_frontmatter；写 commit 主体） | 15 分钟 |
| 5 | 搭 fixture + 5 个测试（happy path / 缺 / 多 / status / dry-run） | 10 分钟 |
| 6 | 写 references/publish-schema.md + platform-format.md | 8 分钟 |
| 7 | 写 SKILL.md（仿 review 结构） | 8 分钟 |
| 8 | 更新 HANDOFF.md | 4 分钟 |

总：约 70 分钟。

---

## Step 9：完成 marker（用于自检）

完成时该有的状态：

- [ ] `skills/write/szw-publish/SKILL.md`（含调用语法 / 输入 / 流程 / Gates / 与上下游集成表 / 示例）
- [ ] `skills/write/szw-publish/scripts/prepare-publish.py`（chmod +x；syntax OK；端到端测过）
- [ ] `skills/write/szw-publish/scripts/finalize-publish.py`（同上）
- [ ] `skills/write/szw-publish/references/publish-schema.md`（stdin JSON 契约 + 校验规则 + 状态推进表）
- [ ] `skills/write/szw-publish/references/platform-format.md`（4 平台格式约定 + 节结构对应）
- [ ] HANDOFF.md 更新（标 ✅ + 里程碑 + quick-start）
- [ ] 5 个 fixture 测试全部通过

---

## 附：参考资源速查

- 设计权威：`study/fan.md` §3.5
- 架构决策：`work/HANDOFF.md` §4.2 self-contained 拷贝
- 已发现的待修问题：`work/REVIEW-2026-05-06.md` §3
- 上游 skill 参考（最像 publish 模式）：
  - `skills/write/szw-review/SKILL.md`（结构最完整的近期作品）
  - `skills/write/szw-review/scripts/finalize-review.py`（helper 函数源 + verdict gate 模式）
  - `skills/write/szw-write/scripts/finalize-write.py`（status advance 双轨模式）
- 下游：`/szw-complete`（未建；publish 只需写 next_action）
