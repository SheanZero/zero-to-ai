# szw-wiki-ingest 开发计划

> 自包含的开发蓝图。下个 session 直接读这一份就能开干。
> 设计源：`study/fan-llm-wiki-extension.md` §4（三段式素材流）+ §7.3（命令详细设计）+ 附录 C（WORKFLOWS.md §一 + §七）
> 输出路径：`/Users/xinz/Development/zero-to-ai/skills/write/szw-wiki-ingest/`
> 一句话定位：把 `resources/` 里的素材 ingest 到 `wiki/`；并支持 `--from-inbox` 自动迁移 inbox/sources/ 中 `read=true` 的项（含 assets/ 路径深度调整 + 事务性回滚 + 删除原文件）。**v1 wiki 命令族第三个**。

---

## Step 1：恢复上下文（必读，约 10 分钟）

按顺序读：

| # | 文件 | 重点 | 时间 |
|---|---|---|---|
| 1 | `work/HANDOFF.md` | 累积工作记录 + 整体架构（注意：未必同步到 wiki 命令族；本 PLAN 是更新版） | 4 分钟 |
| 2 | `study/fan-llm-wiki-extension.md` §4（三段式工作流）+ §7.3（ingest 详细设计）+ 附录 C §一/§七 | 设计源 | 5 分钟 |
| 3 | `skills/write/szw-wiki-import/SKILL.md` | 上一个完成的 wiki 命令；ingest 的工作流结构与之最像（4 phase / 退出码 / log 追加） | 3 分钟 |
| 4 | `skills/write/szw-wiki-import/scripts/wiki-import.py` | 学 frontmatter 处理、SHA256、链接重写、事务模式 | 浏览 |
| 5 | `skills/write/szw-wiki-init/templates/wiki/WORKFLOWS.md` | 已渲染版的 ingest 决策树（init 时复制到 Column 的） | 1 分钟 |

**关键背景**：

- 已完成的 4 个 init 类 skill：`szw-init` / `szw-claude-init` / `szw-wiki-init` / `szw-wiki-import`，全部 v1 跑通端到端测试
- **架构决策**：sub-skill 拆解（init 是 orchestrator，schema 文件由 sub-skill 生成；wiki 命令族独立成单 skill）
- **frontmatter lib 已就绪**：`skills/write/szw-wiki-import/scripts/lib/frontmatter.py`（minimal YAML parser，零依赖）—— 本 skill **复用**它
- **rebuild-indexes.py 已就绪**：`skills/write/szw-wiki-import/scripts/rebuild-indexes.py` —— 本 skill ingest 完成后**直接调它**，不重写
- 红线（v2.1 用户拍板）：
  - `inbox/sources/` → `resources/` 必经 review（`read: true`）
  - 迁移后**删除** inbox 原文件（不留备份；不建 done/）
  - 失败时事务性回滚
  - 不修改 vault 任何内容

---

## Step 2：szw-wiki-ingest 设计

### 2.1 输入 / 输出 / 状态

| 维度 | 内容 |
|---|---|
| 前置 | `wiki.enabled=true`（`/szw-wiki-init` 已跑） |
| 输入 (单文件) | `resources/<file>.md`（必需，frontmatter 完整 + `processed=false`） |
| 输入 (--from-inbox) | `inbox/sources/*.md` 中 `read=true` 的项 |
| 输入 (--batch) | `resources/*.md` 中 `processed=false` 的项（限 5 篇/批） |
| 输出 | `wiki/<type>/<slug>.md`（创建 / 更新；含 sources 溯源）+ 修改 `resources/<file>` frontmatter（processed=true / wiki_pages） |
| 索引重建 | 调 `szw-wiki-import/scripts/rebuild-indexes.py` 增量重建 INDEX 与 reverse |
| log | 追加 `wiki/log.md` 每篇 ingest 一条 grep-friendly 记录 |

### 2.2 调用语法

| 形式 | 行为 |
|---|---|
| `/szw-wiki-ingest <resources/file>` | 单文件 |
| `/szw-wiki-ingest --from-inbox` | 扫 inbox/sources/，迁移 read=true 项 + ingest |
| `/szw-wiki-ingest --batch` | 处理 resources/ 中所有 processed=false 的项 |
| `/szw-wiki-ingest --dry-run <file>` | 列将触及的 wiki 页 |
| `/szw-wiki-ingest --target <dir>` | 指定 Column 根 |
| `/szw-wiki-ingest --no-rebuild` | 跳过 INDEX 重建（手动跑 rebuild-indexes.py） |

### 2.3 架构（标准模式，4-5 个文件）

```
skills/write/szw-wiki-ingest/
├── SKILL.md
└── scripts/
    ├── migrate-inbox.py       # inbox/sources/ → resources/ 事务性迁移（含 assets 路径深度调整）
    ├── prepare-ingest.py      # Phase 0：扫 resources/<file>，输出上下文 JSON 给主对话
    ├── finalize-ingest.py     # Phase 3：JSON commit（更新 wiki 页 + 改 resource frontmatter + log + rebuild）
    └── lib/
        └── frontmatter.py     # symlink 或 cp 自 wiki-import/scripts/lib/
```

**lib/frontmatter.py 选 cp 还是 symlink？**
- **推荐 cp**：与 wiki-import 解耦，避免 fragile dependency。如果 lib API 稳定不再改，可以保持。
- 实际跑：`cp wiki-import/scripts/lib/frontmatter.py wiki-ingest/scripts/lib/`

**不需要 templates/**：本 skill 是产生**用户内容**（wiki 页），不是渲染机器维护的 schema。

### 2.4 ingest 决策树（fan-llm-wiki-extension.md 附录 C §一 + 9 步）

参考 `wiki-init/templates/wiki/WORKFLOWS.md` §一。复制核心：

```
对 resources/<file> 中的每个关键概念/人物/主题/工具：

存在对应 wiki 页？
├── 是 → 该页是否需要更新？
│   ├── 是 → 加入新观点 / 例证 / 链接
│   │       检查矛盾（标 ⚠️）
│   │       追加 sources 引用
│   └── 否 → 仅在该页 sources 列表追加本 resource
└── 否 → 是否值得创建新页？
    ├── 是 → 在合适子目录创建（concepts/people/topics/frameworks/tools/connections）
    │       使用 stub 状态 + 完整 frontmatter
    │       hubs/ 不在 ingest 流程里创建（事后组织动作）
    └── 否 → 在 wiki/log.md 留标注，等更多素材
```

**单源触碰 wiki 页上限**：15（Karpathy 经验值，配置在 `szw-config.json` `wiki.ingest_pages_per_source_max`）。

### 2.5 inbox → resources 迁移（事务性）

参考 `wiki-init/templates/wiki/WORKFLOWS.md` §七。核心 6 步：

```
1. 扫 inbox/sources/*.md，按 read 字段分组
2. 对每个 read=true 项（事务）：
   a. 校验 frontmatter 必备字段（type / title / source / captured / lang）
      缺字段 → 询问补全；不擅自填默认
   b. 规范化 filename: YYYY-MM-DD-<slug>.md（用 captured 日期 + title-derived slug）
      slug 冲突 resources/ 已有 → 询问改名
   c. 重写 markdown 内附件路径：
      ![[../../assets/<slug>/img.jpg]]  (inbox/sources 深 2 层)
      → ![[../assets/<slug>/img.jpg]]   (resources 深 1 层)
      regex: r'!\[\[\.\./\.\./assets/' → '![[../assets/'
      assets/<slug>/ 目录本身不动（不重命名 / 不移动）
   d. 移动 inbox/sources/<file> → resources/<new-name>.md
   e. 删除 inbox/sources/<file>（不留备份）
   f. 触发标准 ingest（§2.4 决策树）
3. 失败回滚：
   - 恢复 inbox/sources/<file>
   - 撤销 resources/<new-name>.md 写入
   - 撤销 markdown 内附件路径 rewrite
   - assets/ 目录本就不动，无需回滚
```

### 2.6 frontmatter 字段（resources / wiki/<type>/<slug>.md）

详见 `wiki-init/templates/wiki/CONVENTIONS.md`。ingest 完成后：

**resources/<file> frontmatter 写入**：
```yaml
processed: true
wiki_pages:
  - wiki/concepts/<slug>.md
  - wiki/topics/<slug>.md
summary: "一句话摘要"
```

**wiki/<type>/<slug>.md frontmatter（新建时）**：
```yaml
type: concept | person | topic | framework | tool | connection | hub
title: "..."
created: 2026-05-07
updated: 2026-05-07
sources:
  - resources/<YYYY-MM-DD-slug>.md
related: []
status: stub
tags: []
derived: false
```

**wiki/<type>/<slug>.md frontmatter（更新已有时）**：
- `updated`: 改为今天
- `sources`: 追加新 resource 路径（去重）

---

## Step 3：脚本接口设计

### 3.1 `migrate-inbox.py`

```
python3 migrate-inbox.py [--target DIR] [--dry-run]

输出 JSON 到 stdout（事务计划，主对话 review 后调用 commit 子命令实际执行）：
{
  "to_migrate": [
    {
      "inbox_path": "inbox/sources/foo.md",
      "frontmatter": {...},
      "frontmatter_warnings": [...],   # 缺字段 → 主对话补全
      "proposed_resource_path": "resources/2026-05-07-foo.md",
      "slug_conflict": false,
      "assets_to_rewrite": ["![[../../assets/foo/img.jpg]] → ![[../assets/foo/img.jpg]]"]
    }
  ],
  "skipped_read_false": ["inbox/sources/bar.md"]
}

退出码:
  0  成功（含 dry-run）
  1  非 szw column / 参数错
  2  inbox/sources/ 不存在
  3  frontmatter 严重错误（无 type / title 等）→ 主对话补全后重跑
```

```
python3 migrate-inbox.py commit [--target DIR] < <plan.json>

读 plan JSON，事务执行：mv 文件 + rewrite markdown + 删除原文件。失败回滚。
返回 JSON：
{
  "migrated": ["resources/2026-05-07-foo.md"],
  "rolled_back": [],
  "errors": []
}
```

### 3.2 `prepare-ingest.py`

```
python3 prepare-ingest.py [--target DIR] --resource <path>

输出 JSON 给主对话决策（哪些 wiki 页要触及）：
{
  "resource": {
    "path": "resources/...md",
    "frontmatter": {...},
    "body_excerpt": "前 1000 字摘要",
    "already_processed": false
  },
  "existing_wiki_pages": {
    "concepts": ["llm-wiki-pattern.md", ...],   # 来自 wiki-cache/pages.json
    "people": [...],
    ...
  },
  "related_pages_by_tag": {
    "<tag>": ["wiki/topics/x.md", ...]   # 来自 reverse.json
  },
  "wiki_link_map": {
    "wiki/concepts/llm-wiki-pattern.md": {"title": "...", "status": "active"}
  }
}

退出码:
  0  成功
  1  非 column / wiki 未启用
  2  resource 不存在
  3  resource frontmatter 残缺
  4  resource processed=true（已 ingest 过；除非 --force）
```

### 3.3 `finalize-ingest.py`

```
python3 finalize-ingest.py commit --resource <path> < <ingest-plan.json>

stdin JSON 描述 AI 决策的 ingest 行动：
{
  "summary": "一句话摘要（写入 resource frontmatter）",
  "wiki_actions": [
    {
      "action": "create",
      "path": "wiki/concepts/foo.md",
      "frontmatter": {...},
      "body": "完整 wiki 页内容（不含 frontmatter）"
    },
    {
      "action": "update",
      "path": "wiki/topics/bar.md",
      "patch": {
        "append_section": "## 新观点\n...",
        "append_sources": ["resources/2026-05-07-foo.md"],
        "set_updated": "2026-05-07"
      }
    }
  ],
  "log_note": "首次引入 LLM-Wiki 概念"
}

脚本动作:
  1. 校验 wiki_actions 数量 ≤ wiki.ingest_pages_per_source_max
  2. 创建 / 更新 wiki 页（render frontmatter via lib）
  3. 修改 resource frontmatter: processed=true, wiki_pages, summary
  4. 追加 wiki/log.md
  5. 调 rebuild-indexes.py（除 --no-rebuild）

退出码:
  0  成功
  1  非 column
  2  wiki_actions 超过上限
  3  JSON schema 校验失败
  4  目标 wiki 页路径无效（type 不在 7 类内）
  5  rebuild-indexes 失败（warning，不阻断 ingest）
```

---

## Step 4：SKILL.md 大纲

参考 `szw-wiki-import/SKILL.md` 结构。要点：

```
1. description（含 inbox 迁移 + 决策树 + 事务性回滚 + 索引重建关键词）
2. 何时使用 / 不用
3. 调用语法表（5 形式）
4. 执行流程（5 phase）
   - Phase 0: prepare-ingest 输出 JSON
   - Phase 1: AI 读 JSON + body 决策（决策树）
   - Phase 2: AI 渲染 ingest plan JSON
   - Phase 3: finalize-ingest commit
   - Phase 4 (--from-inbox 路径): migrate-inbox 在 Phase 0 之前先跑
5. 退出码（0 成功 / 1 column / 2-5 各种）
6. Gates（事务性、上限 15 页、frontmatter 校验、不修改 vault）
7. 设计原则（事务、不留备份、决策树、与 wiki-import 异同）
8. 子 agent（v1 主对话承担；v2 拆 wiki-ingester sub-agent）
9. 与其他命令关系（上游 wiki-init / wiki-import；下游 rebuild-indexes / wiki-suggest）
10. 不实现的事（不修 vault / 不删 wiki / 不绕过 resources / 不留 inbox 备份）
11. 完成 marker（## INGEST COMPLETE / INGEST PARTIAL / INGEST BLOCKED）
```

---

## Step 5：测试场景（端到端）

参考 wiki-import 的 6 场景测试模式。建议覆盖：

| # | 场景 | 预期 |
|---|---|---|
| 1 | 单 resource ingest（无现有 wiki 页） | 创建若干 stub 页 + log + INDEX 重建 |
| 2 | 单 resource ingest（部分 wiki 页已存在） | 创建 + 更新混合 |
| 3 | 已 ingest 过的 resource 重 ingest | exit 4，提示 --force |
| 4 | --from-inbox（含一个 read=true + 一个 read=false） | 迁移 1 个 + skip 1 个 |
| 5 | --from-inbox 含附件路径 rewrite | 检查 rewrite 后 markdown 引用正确 |
| 6 | --from-inbox 模拟 ingest 失败 → 验证回滚 | inbox 文件恢复 + resources 没多 + assets 不动 |
| 7 | --batch（resources/ 中 3 个 processed=false） | 处理前 5 篇（限制内全做） |
| 8 | wiki_actions 超过 15 上限 | exit 2 |

---

## Step 6：建议实施顺序

1. 建目录结构 + cp lib/frontmatter.py（5 分钟）
2. 写 `prepare-ingest.py`（独立脚本，输入 resource，输出上下文 JSON）（30 分钟）
3. 写 `finalize-ingest.py`（脚本主力；JSON commit + frontmatter merge + log + rebuild）（60 分钟）
4. 写 `migrate-inbox.py`（事务性 plan + commit）（45 分钟）
5. 写 SKILL.md（参考 wiki-import）（30 分钟）
6. 烟囱测试（fake column + fake inbox + assets，覆盖 8 场景）（45 分钟）

总计：约 3.5 小时单人开发。

---

## Step 7：参考实现速查

### 来自 szw-wiki-import 的复用模式

**frontmatter 处理**：
```python
sys.path.insert(0, str(Path(__file__).parent / 'lib'))
from frontmatter import parse_frontmatter, render_frontmatter, split_frontmatter
```

**SHA256**：
```python
import hashlib
def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode('utf-8')).hexdigest()
```

**log 追加**（grep-friendly）：
```python
ts = datetime.now().strftime('%Y-%m-%d %H:%M')
entry = f"\n## [{ts}] ingest | {slug}\n- source: resources/{file}\n- created: [...]\n- updated: [...]\n"
with (target / 'wiki' / 'log.md').open('a', encoding='utf-8') as f:
    f.write(entry)
```

**rebuild 调用**（finalize 末尾）：
```python
rebuild_script = Path('skills/write/szw-wiki-import/scripts/rebuild-indexes.py')
# 注意：跨 skill 引用；可以写成相对路径或装个 wrapper
subprocess.run([sys.executable, str(rebuild_script), '--target', str(target)],
               capture_output=True, text=True)
```

> ⚠️ rebuild-indexes.py 跨 skill 引用——v1 直接 cp 一份到 wiki-ingest/scripts/，避免脆弱依赖；或者 wrapper script 路由到固定路径（看哪个简单）。

### 退出码约定（与 wiki-import 对齐）

```
0  成功
1  参数错 / 非 szw column
2  wiki 未启用 / 业务约束违反（如超 15 页上限）
3  vault 路径错 / 输入文件错
4  事务回滚 / conflict / partial
5  rebuild-indexes 失败（warning，不阻断 commit）
```

### Phase 0 prepare 脚本输出 JSON 风格

参考 `wiki-import/scripts/wiki-import.py` 的 `compute_actions` 输出格式：每条行动一个 dict，字段语义化（不用魔法数字）。

---

## Step 8：注意事项 / 红线

- **保持中文优先**（与 user 偏好；SKILL description 用英文，正文中文）
- **frontmatter list 字段顺序**：sources / related / wiki_pages / tags 用 dict 插入顺序保证
- **不重复造轮子**：rebuild-indexes / frontmatter lib 直接复用 / cp 自 wiki-import
- **不修改 vault**：本 skill 完全不接触 vault 路径
- **不动 assets/<slug>/ 目录**：迁移与 ingest 都仅 rewrite markdown 内引用
- **wiki/ 7 类目录边界**：concepts/people/topics/frameworks/tools/connections/hubs；ingest 不创建 hubs/（事后组织动作）
- **derived 字段**：本 skill 不主动设 derived=true；只有 `/szw-wiki-feedback`（v2）从 essay 反向沉淀时设 true
- **inbox 三种子目录**：pending/done/sources/，本 skill 只动 sources/（pending/done 是写作灵感，由 new-article 处理）

---

## Step 9：交付清单（开工前自查）

完成后产出：

- [ ] `skills/write/szw-wiki-ingest/SKILL.md`
- [ ] `skills/write/szw-wiki-ingest/scripts/prepare-ingest.py`
- [ ] `skills/write/szw-wiki-ingest/scripts/finalize-ingest.py`
- [ ] `skills/write/szw-wiki-ingest/scripts/migrate-inbox.py`
- [ ] `skills/write/szw-wiki-ingest/scripts/lib/frontmatter.py`（cp 自 wiki-import）
- [ ] 8 场景烟囱测试通过
- [ ] 更新本文件为 `## DONE` 状态 + 追加测试报告链接

---

## 附录 A：fan-llm-wiki-extension.md 的关键章节

读上游设计文档时聚焦以下章节（其他可跳过）：

| 章节 | 内容 |
|---|---|
| §4.1 | inbox/sources/ 落盘格式（含 read 字段） |
| §4.2 | 阶段 2：review + 自动迁移（6 步详细） |
| §4.3 | 阶段 3：ingest 到 wiki（决策树） |
| §6.1 | v1 命令清单（确认 ingest 在 v1 范围） |
| §7.3 | `/szw-wiki-ingest` 命令详细设计（调用语法 + 退出码） |
| §13.1 | 反模式（11-18 条；含 ingest 相关的 11-13） |
| 附录 C §一 | ingest 9 步决策树（完整版） |
| 附录 C §七 | inbox→resources 迁移流程（步骤详细 + 回滚） |

---

## 附录 B：当前 skills 状态速查

| skill | 状态 | 备注 |
|---|---|---|
| szw-init | v2.1 完成 | orchestrator；调 sub-skills |
| szw-claude-init | v1 完成 | 生成 CLAUDE.md / AGENTS.md |
| szw-wiki-init | v1 完成 | 建 wiki 层 + schema 文件 |
| szw-wiki-import | v1 完成 | 从 vault seed/refresh + rebuild |
| **szw-wiki-ingest** | **TODO（本任务）** | resources → wiki + inbox 迁移 |
| szw-wiki-create-page | 待办 | 创建 stub wiki 页 |
| szw-wiki-query | 待办 | 综合查询 + 可回填 |
| szw-wiki-suggest | 待办 | 给 article 推荐 |
| szw-wiki-lint | 待办 | 健康检查 |

设计源（wiki 命令族整体）：`study/fan-llm-wiki-extension.md` v2.1。

---

## Step 10：完成后追加

完成后在本文件末尾追加：

```markdown
---

## DONE 2026-MM-DD

- 所有交付项 ✅
- 测试结果：详见 `<test-output-or-link>`
- 已知遗留：[列待 v2 的 enhancement]
- 下一步：建议开发 `/szw-wiki-create-page` 或 `/szw-wiki-suggest`
```

---

## DONE 2026-05-07

**交付项** ✅：
- `skills/write/szw-wiki-ingest/SKILL.md`（约 245 行；6 段调用语法 + 5 phase 流程 + 6 退出码 + 3 个 marker + 反模式表）
- `scripts/prepare-ingest.py`（Phase 0：扫 resource frontmatter + 列已有 wiki 页 / wiki_link_map / related_pages_by_tag；4 个退出码门）
- `scripts/finalize-ingest.py`（Phase 3：commit JSON → create / update wiki 页 + 改 resource frontmatter + log + rebuild；DIR_TO_TYPE 映射；degrade-on-conflict）
- `scripts/migrate-inbox.py`（plan + commit 双子命令；frontmatter 转换：剥 inbox-only 字段 / 补 resource 默认 / 重排 / asset rewrite；per-item 事务；blocking 判定含 missing field / slug_conflict / captured invalid）
- `scripts/lib/frontmatter.py`（cp 自 wiki-import）
- `scripts/rebuild-indexes.py`（cp 自 wiki-import）

**端到端测试**（fake column at `/tmp/szw-test-ingest/`）8 场景全 PASS：
1. 单 resource ingest（无现有 wiki）→ 3 stub 页 + log + INDEX 重建
2. 单 resource ingest（含现有 wiki）→ create + update 混合，sources 合并、status bump、related/append_section 全 patch 字段生效
3. 已 processed=true 的 resource → exit 4；`--force` 通过
4. `--from-inbox` plan：read=true / read=false / blocking 三类正确分流；exit 3 当含 blocking
5. asset 路径重写：`![[../../assets/X]]` → `![[../assets/X]]`（仅 markdown 引用，assets/ 目录本体不动）
6. 部分失败回滚：collision 项报 errors，good 项正常迁移；inbox 原文件保留（per-item 原子）
7. `--batch`：通过 SKILL.md 文档约定走外部循环；脚本本身已支持顺序调用
8. wiki_actions > 15 → exit 2，无副作用（dry-run 验证）

**修复过的小 bug**（开发中发现）：
- `type` 字段曾用目录名（`concepts`），改为单数（`concept`）via `DIR_TO_TYPE`
- frontmatter 与 body 之间 1 个换行 → 改为标准的空行（`_attach_body`）
- migrate-inbox blocking 判定遗漏 `missing field: captured` 与 `slug_conflict`

**关键设计权衡**：
- AI 决策树由主对话承担（v1）；脚本仅做 IO + 校验 + rebuild。SKILL.md 中的 9 步决策树是给主对话读的，不内嵌到脚本
- migrate-inbox 在迁移时主动剥离 `read` / `read_notes` 并补 `processed: false` / `wiki_pages: []` / `summary: ""`，让 resource 直接符合 CONVENTIONS.md（PLAN 未要求，但避免下游脏数据）
- 冲突降级（create→已存在 = update；update→不存在 = create）：脚本不报错，记 `create→update(degraded)` 以便 log 与 results 上报
- `rebuild-indexes` 直接 cp 而非 wrapper / 跨 skill 调用，符合 self-contained 原则（HANDOFF §4.2）

**已知遗留 / 待 v2**：
- 没有 `wiki-ingester` sub-agent；决策树由主对话直接跑（v2 拆 sub-agent + marker `## INGEST PLAN READY`）
- `--batch` 在脚本侧没有"限 5 篇/批"硬上限；由 SKILL.md 约定主对话遵守
- 不主动补全缺失 frontmatter：blocking 项需主对话改 inbox 文件后重 plan（PLAN 红线"不擅自填默认"）
- 没有 hub 创建路径（hub 是事后组织，不在 ingest 流程内 — PLAN §2.4 已注明）
- `derived: true` 仅留接口；要等 `/szw-wiki-feedback`（v2）反向沉淀时设
- `summary: ""` 渲染成 `summary: ` 含尾随空格（合法 YAML，但不美观）

**下一步**：
- 推荐：`/szw-wiki-suggest`（给 article 推荐相关 wiki 页；消费 reverse.json）或 `/szw-wiki-create-page`（手动新建 stub）
- 或者回主流水线：`/szw-publish` + `/szw-complete`（让 v1.0 端到端跑通到 published/）
