---
name: szw-wiki-ingest
description: Ingest resources/<file>.md into wiki/ knowledge layer following the 9-step decision tree (existence check → update OR create OR defer). Supports --from-inbox to transactionally migrate inbox/sources/*.md (read=true) into resources/ with asset path rewriting (![[../../assets/]] → ![[../assets/]]) and rollback on failure. Updates wiki page sources, sets resource processed=true + wiki_pages list + summary, appends wiki/log.md, then rebuilds INDEX and reverse caches. Caps wiki pages touched per source at ingest_pages_per_source_max (default 15).
---

# szw-wiki-ingest

把 `resources/` 中已 review 的素材 ingest 到 `wiki/` 知识层；可 `--from-inbox` 自动迁移 `inbox/sources/`。

## 何时使用

- **单文件 ingest**：`/szw-wiki-ingest <resources/file>` —— 主动指定一篇 resource 进入 wiki
- **inbox 批迁移**：`/szw-wiki-ingest --from-inbox` —— 把 inbox 中 `read=true` 的项一次性迁移并 ingest
- **批量补处理**：`/szw-wiki-ingest --batch` —— 处理 `resources/` 中所有 `processed=false`（限 5 篇/批）
- **预演**：`/szw-wiki-ingest --dry-run <file>` —— 列将触及的 wiki 页

## 何时不用

- 没建 wiki 层 → 先 `/szw-wiki-init`
- 想从 vault 拷 → 用 `/szw-wiki-import`
- 想查 wiki → `/szw-wiki-query`（v2）
- 想给 article 推荐相关页 → `/szw-wiki-suggest`（v2）

---

## 调用语法

| 形式 | 行为 |
|---|---|
| `/szw-wiki-ingest <resources/file>` | 单文件 ingest |
| `/szw-wiki-ingest --from-inbox` | 扫 inbox/sources/，迁移 read=true + ingest |
| `/szw-wiki-ingest --batch` | 处理 resources/ 中所有 processed=false（限 5 篇） |
| `/szw-wiki-ingest --dry-run <file>` | 列将触及的 wiki 页（不写盘） |
| `/szw-wiki-ingest --force <file>` | 即使 processed=true 也重 ingest |
| `/szw-wiki-ingest --target <dir>` | 指定 Column 根 |
| `/szw-wiki-ingest --no-rebuild` | 跳过 INDEX 重建 |

---

## 执行流程

本 skill 是 **AI 决策树驱动** + 脚本执行 IO 的混合模式。脚本管收集与落盘；AI 在中间决定哪些 wiki 页要触及、写什么内容。

### Phase 0（仅 `--from-inbox` 路径）：迁移 inbox → resources

```
脚本: scripts/migrate-inbox.py
```

#### 0.1 plan

```bash
python3 scripts/migrate-inbox.py plan --target <target>
```

输出 JSON：
- `to_migrate[]`：每个 read=true 项的 `inbox_path` / `frontmatter` / `frontmatter_warnings` / `proposed_resource_path` / `slug_conflict` / `assets_to_rewrite[]` / `blocking`
- `skipped_read_false[]`：read=false 的项（保留在 inbox 等用户）

退出码 3 = 有 blocking 项（如 captured 字段缺失），主对话补全 frontmatter 后重跑 plan。

#### 0.2 主对话 review

- 缺字段 → 补到 inbox/sources/<file> frontmatter
- slug 冲突 → 修改 plan 中 `proposed_resource_path`
- 决定哪些项最终迁移（可剔除某项）

#### 0.3 commit

```bash
python3 scripts/migrate-inbox.py commit --target <target> < <plan.json>
```

事务行为（每个 item 独立）：
1. 读 inbox 文件
2. rewrite 附件路径：`![[../../assets/X]]` → `![[../assets/X]]`
3. 写 `resources/<new>.md`
4. 删 `inbox/sources/<old>.md`
5. 任意一步失败 → 删除已写的 `resources/<new>.md`（inbox 原文件未删时不动）

输出 `migrated[]` / `rolled_back[]` / `errors[]`。退出码 4 表示有 errors，主对话报告。

### Phase 1：prepare-ingest（每个待 ingest 的 resource）

```bash
python3 scripts/prepare-ingest.py --target <target> --resource <resources/file.md>
```

输出 JSON：
- `resource.frontmatter` / `resource.body_excerpt`（前 2000 字符）/ `already_processed`
- `existing_wiki_pages`：按 7 类（concepts/people/topics/frameworks/tools/connections/hubs）列出 slug + title + status
- `related_pages_by_tag`：当前 resource tags 命中的 wiki 页
- `wiki_link_map`：`wiki/<type>/<slug>.md` → `{title, status}`，供 AI 决策时取链
- `config.ingest_pages_per_source_max`

退出码：
- 0 成功
- 1 非 column / wiki 未启用
- 2 resource 不存在
- 3 frontmatter 残缺（缺 type/title/captured/lang）
- 4 already processed（除非 `--force`）

### Phase 2：AI 跑 ingest 决策树

读 Phase 1 输出 + resource 全文（必要时直接 Read），按 `wiki/WORKFLOWS.md` §一 9 步：

```
对资源中的每个关键概念/人物/主题/工具：

存在对应 wiki 页（同 slug 或语义匹配）？
├── 是 → 该页是否需要更新？
│   ├── 是 → 加入新观点 / 例证 / 链接
│   │       检查矛盾（标 ⚠️）
│   │       追加 sources 引用
│   └── 否 → 仅在该页 sources 列表追加本 resource
└── 否 → 是否值得创建新页？
    ├── 是 → 在合适子目录创建（concepts/people/topics/frameworks/tools/connections）
    │       使用 stub 状态 + 完整 frontmatter
    │       hubs/ 不在 ingest 流程里创建（事后组织动作）
    └── 否 → log 留标注，等更多素材
```

**单源触碰 wiki 页上限**：`ingest_pages_per_source_max`（默认 15，配置在 `szw-config.json`）。

### Phase 3：渲染 ingest plan JSON

AI 产出 stdin JSON（喂给 `finalize-ingest.py commit`）：

```json
{
  "summary": "一句话摘要（写入 resource frontmatter）",
  "wiki_actions": [
    {
      "action": "create",
      "path": "wiki/concepts/llm-wiki-pattern.md",
      "frontmatter": {
        "type": "concept",
        "title": "LLM Wiki 模式",
        "status": "stub",
        "tags": ["ai", "knowledge-management"]
      },
      "body": "完整 wiki 页内容（不含 frontmatter）..."
    },
    {
      "action": "update",
      "path": "wiki/people/andrej-karpathy.md",
      "patch": {
        "append_section": "## 关于 LLM Wiki 的观点\n\n...",
        "append_sources": ["resources/2026-05-07-foo.md"],
        "set_updated": "2026-05-07",
        "append_related": ["wiki/concepts/llm-wiki-pattern.md"],
        "append_tags": ["knowledge-management"],
        "set_status": "active"
      }
    }
  ],
  "log_note": "首次引入 LLM-Wiki 概念"
}
```

`patch` 字段全部可选（按需）：
- `append_section`：追加到 body 末尾的 markdown 段
- `append_sources`：本 resource 路径 + 任何额外 source（脚本会去重并自动加入当前 resource）
- `set_updated`：默认今天
- `append_related` / `append_tags`：去重合并
- `set_status`：手动 bump（如 stub → active）

### Phase 4：finalize-ingest commit

```bash
python3 scripts/finalize-ingest.py commit \
    --target <target> --resource <resources/file.md> \
    [--no-rebuild] [--dry-run] < <plan.json>
```

行为：
1. 校验 schema + 上限（`wiki_actions` 数 ≤ max）
2. 对每个 action：
   - `create`：渲染 frontmatter（自动填 type/created/updated/sources/status/derived 默认值）+ body 写入；目标已存在则**降级为 update**（log 警告）
   - `update`：merge sources / 改 updated / 追加 section / 应用其他 patch；目标不存在则**降级为 create**
3. 改 resource frontmatter：`processed=true` + `wiki_pages: [...]` + `summary`
4. 追加 `wiki/log.md`（`## [YYYY-MM-DD HH:MM] ingest | <slug>`）
5. 调 `rebuild-indexes.py`（除 `--no-rebuild`）

退出码：
- 0 成功
- 1 非 column
- 2 wiki_actions 超过上限
- 3 JSON schema 失败 / 缺字段
- 4 wiki 页 type 不在 7 类内
- 5 rebuild-indexes 失败（warning，不阻断 ingest）

---

## 完整端到端调用序列

### 单文件
```bash
# 1. prepare
python3 scripts/prepare-ingest.py \
    --target <col> --resource resources/2026-05-07-foo.md > /tmp/ctx.json

# 2. AI 读 ctx + resource 全文，跑决策树，生成 plan.json

# 3. finalize
python3 scripts/finalize-ingest.py commit \
    --target <col> --resource resources/2026-05-07-foo.md < /tmp/plan.json
```

### --from-inbox
```bash
# 0. plan
python3 scripts/migrate-inbox.py plan --target <col> > /tmp/migrate-plan.json

# 0'. AI 检查 plan（补缺字段、解 slug 冲突），可能修 plan 后写回 /tmp/migrate-plan.json

# 0''. commit
python3 scripts/migrate-inbox.py commit --target <col> < /tmp/migrate-plan.json

# 后续：对 migrated[] 中每个 resource 跑单文件流程
```

---

## Gates

| 类型 | 触发 | 处理 |
|---|---|---|
| **Pre-flight** | `wiki.enabled=true` + resource 存在 | 否则 exit 1/2 |
| **Frontmatter 必备** | resource 缺 type/title/captured/lang | exit 3，主对话补全或剔除 |
| **already_processed** | `processed=true` 且未 `--force` | exit 4，提示用户决定 |
| **页数上限** | `wiki_actions` 数 > 15 | exit 2；AI 应裁剪决策 |
| **路径合法** | `wiki/<type>/<slug>.md`，type ∈ 7 类 | exit 4 |
| **不修 vault** | 红线 | 脚本对 vault 路径只读（实际从未触及） |
| **inbox 删原文件** | commit 阶段成功后 unlink | 失败回滚 resources/ 已写 |

---

## 设计原则

1. **AI 决策 + 脚本 IO**：决策树是 AI 的工作（语义判断）；脚本只负责扫描、JSON、写盘、回滚——不内嵌任何"页是否需要更新"的启发式
2. **单源触碰上限 15**：Karpathy 经验值。超过通常意味着 resource 太杂或 AI 决策没收敛——拒绝而非吞掉
3. **事务性 inbox 迁移**：每 item 独立事务（其他 item 失败不影响已成功）；删原文件**不留备份**（vault 红线之外）
4. **assets/ 目录原地不动**：迁移仅 rewrite markdown 内的相对深度；assets/<slug>/ 子目录从未被移动 / 重命名
5. **降级原则（写入冲突）**：create→已存在 = degrade-to-update；update→不存在 = degrade-to-create。脚本不报错，但 log 标注
6. **rebuild 失败不阻断**：ingest 主要写盘动作已落地；rebuild 失败仅产出 exit 5 + warning，用户可手动重跑

---

## 子 agent 调用

v1 全脚本 + 主对话承担决策树。v2 计划：

| Agent | 角色 | Marker | 跑在 |
|---|---|---|---|
| `wiki-ingester` | 跑决策树（解 wiki_link_map + body）+ 输出 plan JSON | `## INGEST PLAN READY` | Claude |

---

## 与其他命令的关系

- **上游**：
  - `/szw-wiki-init`（建 wiki 层与 schema）
  - `/szw-wiki-import`（从 vault seed resources）
  - 用户手工落 inbox/sources/
- **下游**：
  - `rebuild-indexes.py` 自动调（除 `--no-rebuild`）
  - `/szw-wiki-query` / `/szw-wiki-suggest` / `/szw-wiki-lint`（v2，消费 reverse-index）
- **平行**：
  - `/szw-wiki-import` 也会跑 rebuild-indexes（互不干扰，重建幂等）
- **永不调用**：vault 自身的 ingest / 编辑（vault 对 szw 红线只读）

---

## 不实现的事（v1）

- **不修改 vault 任何文件**（红线）
- **不删除 wiki 页**（删除是 lint 的事）
- **不绕过 resources/ 直接写 wiki**（必须经 resource 溯源）
- **不留 inbox 备份**（不建 inbox/done/，不复制；用户已通过 read=true 表态）
- **不创建 hubs/**（hub 是事后组织动作，不在 ingest 流程内）
- **不主动设 derived=true**（仅 `/szw-wiki-feedback` v2 反向沉淀时才设）
- **不动 assets/<slug>/ 目录本体**（仅 markdown 内引用 rewrite）
- **不 git commit**

---

## 完成 marker

```
## INGEST COMPLETE
- Resource: <rel-path>
- Wiki pages touched: <count> (created=<c>, updated=<u>)
- Summary: <summary>
- Indexes rebuilt: yes | no
- Log: wiki/log.md updated
- Next: /szw-wiki-query | /szw-wiki-suggest | /szw-wiki-lint
```

部分失败（仍写盘，但有错）：

```
## INGEST PARTIAL
- Resource: <rel-path>
- Wiki pages touched: <count>
- Issues: <list>
- Action: 看 wiki/log.md 末条 + stderr
```

阻断（未写盘）：

```
## INGEST BLOCKED
- Reason: <e.g. resource frontmatter incomplete | exceeds page cap | already processed>
- Suggestion: <next step>
```

inbox 迁移完成（即将进入 ingest）：

```
## MIGRATE COMPLETE
- Migrated: <count> file(s)
- Rolled back: <count>
- Errors: <count>
- Next: ingest each migrated resource
```

---

## 反模式

1. **不要把 wiki 页当 resource 处理**（type=concept 而非 type=article 等；frontmatter 字段集不同）
2. **不要在 ingest 时给 wiki 页加大量未在 resource 中提到的内容**（hallucination；ingest 是溯源的）
3. **不要绕过 prepare-ingest.py 直接喂 plan**（缺少 wiki_link_map / existing_wiki_pages 上下文，AI 易决策错）
4. **不要 manual 改 inbox 文件名后再 plan**（plan 推导文件名会变；先决定再迁移）
5. **不要在 commit 后再 patch 同一 resource**（`processed=true` 后默认拒绝；用 `--force` 表态）
