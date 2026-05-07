---
name: szw-wiki-import
description: Import or refresh wiki content from a configured vault into the szw Column. Auto-detects vault wiki/resources/assets subdirs (Karpathy-style 1-wiki/4-resources/6-assets, plain wiki/resources/assets, capitalized variants) and rewrites wikilinks + asset paths to szw conventions. Performs three-way diff (seed-manifest / vault-now / szw-now) for incremental sync; full mode overwrites. Auto-bootstraps wiki layer via sibling /szw-wiki-init when wiki.enabled is false (only forwards --target, no import args; disable with --no-auto-init). Interactive (TTY) prompts for missing vault.path, subdir confirmation, and assets inclusion; non-TTY/CI mode uses flags + auto-detect (--no-prompt for explicit). Rebuilds wiki/INDEX.md, 7 category INDEX.md, resources/INDEX.md, and .zero/wiki-cache/ reverse indexes after changes. Conflicts default to keep-szw + report. Append entry to wiki/log.md.
---

# szw-wiki-import

从已配置的 vault 把 wiki 内容 + 原始素材导入到 szw Column。

## 何时使用

- **首次 seed**（`/szw-init` 时选了 `seed-from-vault`，本 skill 完成实际拷贝）
- **定期 refresh**：vault 端有新增 / 更新，把改动 fast-forward 到 szw
- **重新 build 索引**：vault 没新东西，但想重建 INDEX / cache（用 `--no-import` v2 / 或直接 rebuild-indexes.py）

## 何时不用

- 没配 `vault.path` → 先 `/szw-config set vault.path <path>` 或 `/szw-wiki-init --bootstrap seed-from-vault`
- 想 ingest 自建的 resources → `/szw-wiki-ingest`
- 想查 wiki → `/szw-wiki-query`

---

## 调用语法

| 形式 | 行为 |
|---|---|
| `/szw-wiki-import` | 默认 `--incremental`：三向 diff 后只动改变的项 |
| `/szw-wiki-import --full` | 全量覆盖（vault → szw 所有页；忽略 szw 本地修改） |
| `/szw-wiki-import --dry-run` | 列出将做的事，不写盘 |
| `/szw-wiki-import --pages-only` | 只 import `1-wiki/`，跳过 `4-resources/` |
| `/szw-wiki-import --include-assets` | 同时 cp `vault/6-assets/` → `column/assets/`（默认不 cp，体积考虑） |
| `/szw-wiki-import --force-vault` | 冲突时强制 vault 覆盖（用于 v2 merge prompt 决策的 apply 阶段） |
| `/szw-wiki-import --vault-path <path>` | 临时覆盖 `vault.path`（不持久化） |
| `/szw-wiki-import --target <dir>` | 指定 Column 根 |
| `/szw-wiki-import --no-rebuild` | 跳过 import 后的 INDEX 重建（手动跑 `rebuild-indexes.py`） |
| `/szw-wiki-import --no-auto-init` | 当 `wiki.enabled=false` 时，禁用自动 bootstrap，恢复旧行为（exit 2） |
| `/szw-wiki-import --no-prompt` | 禁用所有交互询问（CI 模式）；缺路径直接 exit 3 |
| `/szw-wiki-import --wiki-subdir NAME` | 显式指定 vault 中的 wiki 子目录（默认 probe `1-wiki`/`2-wiki`/`wiki`/`Wiki`） |
| `/szw-wiki-import --resources-subdir NAME` | 同上，resources（probe `4-resources`/`3-resources`/`resources`/`Resources`） |
| `/szw-wiki-import --assets-subdir NAME` | 同上，assets（probe `6-assets`/`5-assets`/`assets`/`Assets`） |

---

## 执行流程（4 phase）

### Phase 0：Preflight

校验：
- `<target>/.zero/szw-config.json` 存在
- `wiki.enabled = true`
  - 默认行为：若为 false / 缺失，**自动调相邻 skill `szw-wiki-init`** 跑 `init-wiki-layer.sh` + `finalize-wiki-init.py`（仅传 `--target`，**不**把 import 的参数透给 init）；init 建空骨架，import 自己负责 seeding
  - 加 `--no-auto-init` 可禁用此行为，回到旧的 exit 2
  - 自动 bootstrap 失败 → exit 6（找不到 sibling skill 或子脚本失败）
- `vault.path` 解析顺序：`--vault-path` → `.zero/szw-config.local.json` → 交互询问（TTY 时）→ exit 3
- 交互模式触发条件：`stdin.isatty() and not args.no_prompt`。Claude Code 中的 Bash 工具调用通常不是 TTY，AI 应在对话中收集参数后通过 flags 传入；用户在终端直跑时则走交互流程。
- 子目录解析顺序（每个 of wiki / resources / assets）：CLI flag → 交互 prompt → 自动 probe → config 默认 → exit 3
  - probe 候选：见调用语法表的 `--*-subdir` 描述
  - 大小写处理：macOS 文件系统对大小写不敏感，但下游正则改写敏感，因此 detect 后会用 `os.scandir` 还原**实际大小写**作为 subdir 名（如 vault 是 `Wiki/` 时，正则就用 `Wiki/`，确保 markdown 里的 `[[Wiki/...]]` 能被匹配到）
- assets：发现存在时 TTY 询问是否 import（覆盖 `--include-assets`）；非 TTY 时仍以 `--include-assets` 旗为准

### Phase 1：Scan + 三向 diff

```
脚本: scripts/wiki-import.py
```

#### 1.1 扫 vault

- `<wiki_subdir>/{concepts,people,topics,frameworks,tools,connections,hubs}/*.md`（跳过 `INDEX.md`）
- `<resources_subdir>/*.md`（仅当不带 `--pages-only`）

  其中 `<wiki_subdir>` 和 `<resources_subdir>` 由 Phase 0 解析；下面的链接重写示例以 Karpathy 风格 `1-wiki`/`4-resources`/`6-assets` 为例，实际正则按解析结果动态编译。
- 对每个文件：
  1. 读取正文
  2. **重写 wikilink 与附件路径**（vault → szw 风格）：
     - `[[1-wiki/concepts/x|...]]` → `[[wiki/concepts/x|...]]`
     - `[[4-resources/y|...]]` → `[[resources/y|...]]`
     - `![[../6-assets/<slug>/img.jpg]]` → `![[../assets/<slug>/img.jpg]]`
     - `![[../../6-assets/...]]` → `![[../../assets/...]]`
  3. 计算重写后内容的 SHA256 → `vault_now_hash`

#### 1.2 扫 szw 当前

- `wiki/<type>/*.md` + `resources/*.md`
- 对每个文件计算当前 SHA256 → `szw_now_hash`

#### 1.3 加载 seed-manifest

`<target>/.zero/wiki-cache/seed-manifest.json`：

```json
{
  "1-wiki/concepts/llm-wiki-pattern.md": "<sha256>",
  "1-wiki/people/andrej-karpathy.md": "<sha256>",
  "4-resources/2026-04-10-karpathy-llm-wiki.md": "<sha256>",
  ...
}
```

记录每个 vault 文件**上次 import 时的 vault 端 hash**。首次跑时为 `{}`。

#### 1.4 三向 diff

对每个 vault 文件：

| seed → vault | seed → szw | 行为 |
|---|---|---|
| 不变 / 无 seed | szw 不存在 | **add**：写入 + manifest |
| 不变 | szw 不变（== seed） | **skip-equal**（manifest 刷新） |
| 变了 | szw 不变（== seed） | **fast-forward**：写入 + manifest |
| 不变 | szw 变了（!= seed） | **skip-szw-edited**（保留 szw 修改） |
| 变了 | szw 变了 | **conflict**：报告 + 默认 keep-szw（除非 `--force-vault`） |
| szw 不存在但有 seed 记录 | — | （vault 也变了 → 等同 add） |

szw 文件 vault 没有：
- vault 端**没有**该文件（曾在 seed-manifest 中） → **vault-deleted**：报告，不动 szw
- vault 端**没有**该文件（不在 manifest） → **szw-only**：忽略（用户在 szw 自建的页）

#### 1.5 `--full` 模式覆盖

跳过三向 diff；所有 vault 文件直接 `force-write` 到 szw（仍重写链接）。manifest 全量更新。

### Phase 2：Apply

按 Phase 1.4 决策对每个文件执行：

- **add / fast-forward / force-write**：写到 szw，更新 seed-manifest
- **skip-equal**：仅刷新 manifest（无文件变更）
- **skip-szw-edited / conflict / vault-deleted**：不动文件

`--dry-run` 时所有 write 跳过，只报告。

### Phase 3：附件处理

#### 3.1 路径重写（始终做）

Phase 1.1 的链接重写已处理：markdown 内引用 `../6-assets/<slug>/...` → `../assets/<slug>/...`。

#### 3.2 实体复制（仅 `--include-assets`）

`vault/6-assets/<slug>/<file>` → `column/assets/<slug>/<file>`：

- 用 `shutil.copy2` 保留 mtime
- 已存在跳过（不覆盖）
- 输出 `<files>` files, `<bytes>` KB 统计

不带 `--include-assets` 时输出 warning：

```
⚠️  N assets referenced but not imported. To copy:
    /szw-wiki-import --include-assets
```

### Phase 4：Rebuild Indexes

调脚本：

```
python3 scripts/rebuild-indexes.py --target <target>
```

产出：

- `wiki/INDEX.md`（顶层入口；每类页数）
- `wiki/<type>/INDEX.md` ×7（该类下每页摘要 + tag + status）
- `resources/INDEX.md`（按月分组倒序）
- `.zero/wiki-cache/pages.json`（wiki 全页结构化）
- `.zero/wiki-cache/resources.json`（resource 全素材结构化）
- `.zero/wiki-cache/reverse.json`（by_tag / by_type / by_status / by_resource / by_wiki_page）
- `.zero/wiki-cache/content-hash.json`（每页 SHA256）

`--no-rebuild` 时跳过这一步。

### Phase 5：写 wiki/log.md

非 dry-run 且有变更时追加：

```markdown
## [2026-05-06 15:30] import | from vault
- mode: incremental
- vault: /Users/xinz/.../SheanZero
- changed: 5 (added=3, ff=1, force=1)
- conflicts: 0
```

---

## 输出格式

```
✅ Wiki import done at: <target>

Vault: /Users/xinz/.../SheanZero
Mode: incremental

Results:
  added:              3
  fast-forwarded:     1
  skipped (equal):    28
  skipped (szw-edit): 1
  conflicts:          1
  vault-deleted:      0

⚠️  1 conflict — szw local kept (default keep_szw):
  - wiki/topics/claude-code-ecosystem.md

  Resolve options:
    1) Edit szw locally to match desired state
    2) /szw-wiki-import --force-vault  (overwrite all conflicts with vault)
    3) [v2] /szw-wiki-import --merge-prompt  (interactive resolution)

→ Running rebuild-indexes.py...
Indexes rebuilt at: <target>

Wiki pages by type:
  concepts      6
  people        5
  topics        6
  frameworks    1
  tools         8
  connections   7
  hubs          6
  total         39

Resources: 119

👉 Next:
  - /szw-wiki-query <q>     在 wiki 里查
  - /szw-wiki-suggest <slug> 给某 article 推荐相关页
  - /szw-wiki-lint          健康检查
```

---

## 退出码

| 码 | 含义 | 应对 |
|---|---|---|
| 0 | 成功 | — |
| 1 | 参数错 / 路径错 | 检查 cwd / vault path |
| 2 | 非 szw Column / wiki 未启用（仅 `--no-auto-init` 时才会到此码） | 先 `/szw-init` + `/szw-wiki-init`（或去掉 `--no-auto-init`） |
| 3 | vault.path 未配置 / 路径不存在 / 缺 1-wiki+4-resources | 配 vault.path / 修路径 |
| 4 | 检测到 conflict（incremental，默认 keep_szw） | 用 `--force-vault` 或人工解决 |
| 5 | rebuild-indexes 失败 | 看错误信息；不阻断 import 本身 |
| 6 | auto-init 失败（找不到 sibling szw-wiki-init/scripts 或子脚本失败） | 改用 `/szw-wiki-init` 手动初始化，或 `--no-auto-init` 跳过自动逻辑 |

---

## Gates

| 类型 | 触发 | 处理 |
|---|---|---|
| **Pre-flight** | wiki.enabled=true + vault.path 可读 | wiki 未启用时**默认自动调 sibling `szw-wiki-init`** 完成 bootstrap；`--no-auto-init` 时回到 exit 2；vault.path 缺 → exit 3 |
| **Conflict** | 三向 diff 检测 vault 与 szw 都改 | 默认 keep-szw + exit 4；`--force-vault` 时跳过 gate |
| **Schema 不一致** | vault 与 szw 的 frontmatter 字段集差距大 | warning，不阻断 |
| **不写 vault** | 红线 | 脚本只读 vault |

---

## 设计原则

1. **Vault read-only 红线**：脚本对 vault 只读；任何写都到 szw
2. **三向 diff = git merge 思想**：seed-manifest 是 base，vault-now 是 theirs，szw-now 是 ours
3. **冲突默认 keep-szw**：保护用户在 Column 的修改；显式 `--force-vault` 才覆盖
4. **链接重写在 import 时做**：保证导入后 wikilink 正确指向 szw 端文件；不依赖运行时拼接
5. **附件路径不改深度**：vault 与 szw 同结构（resources 在第一层，wiki/<type> 在第二层），相对路径深度天然一致；只换 `6-assets` → `assets`
6. **assets 默认不复制**：体积大；显式 `--include-assets` 才 cp（用户可手动 cp 子集）
7. **rebuild 后 reverse-index 是单一 source**：`/szw-wiki-suggest` `/szw-wiki-query` `/szw-wiki-lint` 都消费它
8. **Auto-init bridge**：发现 `wiki.enabled=false` 时，默认子进程调 sibling `szw-wiki-init/scripts/{init-wiki-layer.sh,finalize-wiki-init.py}`（**只传 `--target`**，import 知识不漏过去），然后 reload config 继续；保留 `--no-auto-init` 让 CI / 编排器把 init 与 import 分离
9. **Subdir 命名解耦**：vault 子目录名（`1-wiki`/`Wiki`/`Notes` 等）通过 probe + 实际文件系统大小写解析；rewriter 正则按解析结果动态编译，不硬编码 Karpathy 数字前缀
10. **交互式默认 ON，但只在 TTY**：终端直跑会询问路径 / 子目录 / assets；脚本化 / Claude Code 调用时（无 TTY）则按 flags + auto-detect 静默运行，必要时由 AI 在对话里向用户收集参数后再调脚本

---

## merge prompt（v2 设计）

v1 冲突默认 keep-szw + 报告。v2 加 interactive prompt：

```
⚠️ 冲突：wiki/topics/claude-code-ecosystem.md

vault 端更新（since seed 2026-04-25）：
  +新增段落：## v2.0 工具列表更新
  +sources +1: 4-resources/2026-05-04-claude-code-v2.md

Column 端修改（since seed 2026-04-25）：
  +新增 connections 引用：[[connections/sdd-skills-stacking]]
  -删除段落：## 旧的 v1 工具图谱

请选择：
  1. keep szw     保留本地版本
  2. take vault   用 vault 覆盖
  3. merge by AI  启用 LLM 合并（产出候选 + diff，用户确认）
  4. defer        跳过本次，留待下次 import
  5. show diff    显示完整 diff 后再选

> _
```

`merge by AI` 调子 agent `wiki-merger`（fan-llm-wiki-extension.md §10），输出 `wiki/<page>.merged.candidate.md`，用户人审接受 / 拒绝。

v2 实现要点：
- 单次 import 冲突 > 5 时降级为"先列冲突清单 + 用户选处理顺序"
- merge 候选作为单独文件保留（不直接写主文件）
- log.md 记录每个冲突的决策

---

## 子 agent 调用

v1 全脚本驱动，无子 agent。v2 加：

| Agent | 角色 | Marker | 跑在 |
|---|---|---|---|
| `wiki-merger` | merge prompt 中 "merge by AI" 子流程 | `## MERGE PROPOSAL READY` | Claude（或 Codex 路由） |

---

## 与其他命令的关系

- **上游**：`/szw-wiki-init --bootstrap seed-from-vault`（手动路径）；或者直接跑本 skill —— 默认 auto-init 会自动调 sibling 完成 bootstrap
- **下游**：
  - `rebuild-indexes.py` 自动调用（除非 `--no-rebuild`）
  - 后续 `/szw-wiki-query` / `/szw-wiki-suggest` / `/szw-wiki-lint` 消费 reverse-index
- **平行**：`/szw-wiki-ingest`（自建 resources 走 ingest，与 vault import 互补）
- **永远不调用**：vault 自身的 ingest / lint（红线）

---

## 模板

本 skill **不渲染模板**——它处理的是 vault 已有内容的导入；模板由 `/szw-wiki-init` 渲染。

---

## 不实现的事（v1）

- **不做 merge prompt 交互**（v2）
- **不渲染 wiki schema 文件**（CONVENTIONS / WORKFLOWS 在 init 时已渲染）
- **不修改 vault 任何文件**（红线）
- **不删除 szw 端文件**（vault-deleted 仅报告）
- **不处理 vault `2-personal/` / `3-projects/`**（vault 红线）
- **不 import vault `1-wiki/index.md`**（szw 自己 rebuild）
- **不 git commit**

---

## 完成 marker

```
## WIKI IMPORT COMPLETE
- Target: <abs path>
- Vault: <vault path>
- Mode: incremental | full
- Changes: <count>
- Conflicts: <count>
- Indexes rebuilt: yes | no
- Next: /szw-wiki-query | /szw-wiki-suggest | /szw-wiki-lint
```

冲突仅报告未解决：

```
## WIKI IMPORT NEEDS REVIEW
- Conflicts: <count>
- Conflict files:
  - wiki/topics/x.md
  - ...
- Action: edit locally OR re-run with --force-vault
```

错误：

```
## WIKI IMPORT BLOCKED
- Reason: <原因>
- Suggestion: <下一步>
```
