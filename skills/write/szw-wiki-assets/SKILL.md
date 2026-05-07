---
name: szw-wiki-assets
description: Manage assets/ directory health. Two operations - (1) orphans detection - scan all .md under wiki/ and resources/ (optionally inbox/) for asset references, diff against actual files in assets/, list unreferenced files with size, optionally prompt-and-delete. (2) localize - scan resources/ markdown for http(s) image/attachment links, download to assets/<resource-slug>/, rewrite links to Obsidian wikilink format ![[../assets/<slug>/<file>]]. Both ops support --dry-run; orphan deletion gates on TTY confirm or --yes; localize uses urllib (stdlib) so no extra deps.
---

# szw-wiki-assets

照看 `assets/` 目录健康：清孤儿 + 远程链接本地化。

## 何时使用

- 完成多次 ingest / 删除 article 后觉得 `assets/` 体积膨胀，想审查孤儿（`/szw-wiki-assets orphans`）
- 写作 / 整理 resource 时引入了远程图片，想下载到本地避免链接腐烂（`/szw-wiki-assets localize`）
- 季度 / 发版前的 wiki 健康巡检（与 `/szw-wiki-lint` v2 互补，本 skill 专注 assets）

## 何时不用

- 想删除 wiki 页（不是 assets）→ `/szw-wiki-lint`（v2）报告，人工或专门删除路径
- 想搬运素材到 wiki → `/szw-wiki-ingest`
- 想从 vault 同步 assets → `/szw-wiki-import --include-assets`

---

## 调用语法

```
/szw-wiki-assets <subcommand> [options]
```

子命令：`orphans` / `localize`。

### orphans

| 形式 | 行为 |
|---|---|
| `/szw-wiki-assets orphans` | 扫 + 列孤儿（默认仅 report） |
| `/szw-wiki-assets orphans --delete` | TTY 询问每个孤儿是否删（y/n/a/q） |
| `/szw-wiki-assets orphans --delete --yes` | 跳过逐项确认（**危险**；CI 用） |
| `/szw-wiki-assets orphans --delete --dry-run` | 列出**会**删的文件，不实际删 |
| `/szw-wiki-assets orphans --include-inbox` | 也扫 `inbox/sources/` 找引用（默认仅 wiki/ + resources/） |

### localize

| 形式 | 行为 |
|---|---|
| `/szw-wiki-assets localize` | 扫 `resources/`，下载远程图片，rewrite 链接 |
| `/szw-wiki-assets localize --scope wiki` | 改扫 `wiki/`（一般不用） |
| `/szw-wiki-assets localize --scope all` | 同时扫 `resources/` 与 `wiki/` |
| `/szw-wiki-assets localize --dry-run` | 列出会下载/改写的链接，不实际下 |
| `/szw-wiki-assets localize --timeout 30` | 单链接超时（默认 15 秒） |
| `/szw-wiki-assets localize --skip-cert` | 关 TLS 证书校验（一般不用） |

公用：`--target DIR` / `--no-prompt`。

---

## 执行流程

### orphans

```
脚本: scripts/manage-assets.py orphans
```

1. 扫 `<target>/wiki/**/*.md` + `<target>/resources/*.md`（含 `--include-inbox` 时加 `inbox/sources/`）
2. 对每个 `.md`，提取所有：
   - Obsidian 链接：`![[X]]` / `[[X]]`（去掉 alias `|...`）
   - Markdown 图片：`![alt](X)` （URL 跳过）
3. 把每条链接相对于 `.md` 所在目录解析为绝对路径
4. 若解析后路径在 `<target>/assets/` 下 → 计入"被引用"集合
5. 实际 `assets/` 文件 ⊖ 被引用 = **孤儿集**
6. 默认仅报告：列文件 + 大小 + 总和
7. 加 `--delete`：
   - TTY：逐项 prompt（y=删 / n=保留 / a=后续全删 / q=停止）
   - `--yes`：直接全删（非 TTY 时必带 `--yes`，否则 exit 4）
   - 删除后清理空 assets/<slug>/ 目录
8. 报告：删了几个 / 多少 KB / errors

### localize

```
脚本: scripts/manage-assets.py localize
```

1. 扫 scope（默认 `resources/`）下 `.md`
2. 用 `re.search(r'!\[[^\]]*\]\(https?://')` 快筛：无远程图片直接跳过
3. 命中文件：用 `urllib.request` 下载（stdlib，无依赖）：
   - 文件名从 URL path 末段推；URL 无扩展名时用 Content-Type 推（mime → ext）
   - 落到 `<target>/assets/<md-stem>/<file>`
   - 已存在 → 复用（幂等）
4. rewrite markdown：`![alt](https://...)` → `![[../assets/<slug>/<file>]]`
   - 相对深度按 `.md` 在 target 下的层数计算（resources/ = `../`，wiki/<type>/ = `../../`）
5. 报告：rewrites 数 / files_changed / errors

---

## 退出码

| 码 | 含义 |
|---|---|
| 0 | 成功（含 dry-run / 无孤儿 / 无远程链接） |
| 1 | 非 szw Column / 参数错（如 scope 不在 [resources, wiki, all]） |
| 2 | `<target>/assets/` 不存在 |
| 3 | localize 部分下载失败 |
| 4 | orphans 部分删除失败，或非 TTY + `--delete` 没带 `--yes` |

---

## Gates

| 类型 | 触发 | 处理 |
|---|---|---|
| **Pre-flight** | `<target>/.zero/szw-config.json` 存在 | 否则 exit 1 |
| **Assets 必备** | `<target>/assets/` 存在（orphans 子命令） | 否则 exit 2 |
| **删除安全** | `--delete` 必须有 TTY 确认 OR `--yes` | 非 TTY + 无 `--yes` → exit 4 |
| **不动 vault** | 红线 | 脚本不接触 vault 路径 |
| **不动 .zero/** | 红线 | 仅 wiki/ resources/ inbox/ assets/ |

---

## 设计原则

1. **不破坏链接**：localize 仅对真正能下载成功的 URL 改写；失败保留原 markdown 不动 + 报告
2. **幂等**：localize 已存在的目标文件不重下；orphans 可重复跑（删完后第二次跑就空）
3. **零依赖**：纯 stdlib（`urllib.request` / `ssl` / `re` / `pathlib`）。不引入 requests / beautifulsoup
4. **分子命令隔离**：orphans 与 localize 不互相依赖；可单独跑
5. **assets 子目录命名跟随 stem**：`resources/<slug>.md` 的下载落到 `assets/<slug>/`，与 CONVENTIONS.md §一一致；冲突时用 sha256 后缀防覆盖（仅当 URL 文件名相同但内容不同时；当前实现遇同名直接复用 v1，v2 加 hash check）
6. **Obsidian wikilink 输出**：rewrite 用 `![[...]]` 格式（CONVENTIONS.md §三推荐）；不与 `![](path)` 混用
7. **删除前清理空目录**：删孤儿后顺手 `rmdir` 空 `assets/<slug>/`，避免无用 stub 子目录留存

---

## 子 agent

v1 全脚本。v2 计划：

| Agent | 角色 | Marker | 跑在 |
|---|---|---|---|
| `wiki-assets-curator` | 处理边缘 case：URL 跳转 / Cookie wall / Cloudflare 拒答 / 内容嗅探 | `## ASSETS CURATED` | Claude（按需 Codex） |

---

## 与其他命令的关系

- **平行**：
  - `/szw-wiki-lint`（v2）—— 报告 wiki 页 / resources / assets 综合健康；本 skill 专注 assets 写操作
  - `/szw-wiki-ingest` —— 处理 inbox→resources 时已经做了 markdown 内 asset 路径深度调整，但**不**下载远程图片；本 skill 的 localize 是补这个洞
  - `/szw-wiki-import --include-assets` —— 从 vault 拷 assets；本 skill 是 szw 端清扫
- **不调用**：rebuild-indexes（assets 不进 reverse-index；删/加 assets 不影响 wiki-cache）
- **永远不**：动 vault；动 .zero/；动 articles/

---

## 不实现的事（v1）

- **不抓 HTML 页面**（只对 markdown 中的 `![alt](http...)` 直链生效）
- **不处理 base64 内嵌图**（`data:image/png;base64,...`；保持原样）
- **不重命名已存在的本地引用**（仅处理 http/https）
- **不下载到 vault**（本 skill 不接触 vault 路径）
- **不改 frontmatter**（仅 body markdown 重写）
- **不 git commit**

---

## 完成 marker

```
## ASSETS ORPHANS REPORT
- Scanned md: <count>
- Orphans: <count> (<total size>)
- Deleted: <count>
- Errors: <count>
```

```
## ASSETS LOCALIZED
- Scope: resources | wiki | all
- Files changed: <count>
- Links rewritten: <count>
- Errors: <count>
```

阻断：

```
## ASSETS BLOCKED
- Reason: <e.g. assets/ missing | --delete without --yes in CI>
- Suggestion: <next step>
```

---

## 反模式

1. **不要 `--delete --yes` 不看 dry-run**：先 `--delete --dry-run` 列出来再决定
2. **不要 localize 完不 commit**：网络不可逆，万一原 URL 几小时后挂了就只剩 assets/ 副本
3. **不要在跑 localize 时同时改 markdown**：会引发并发写竞争；先停手再跑
4. **不要假设所有图床能下**：CDN / Cloudflare / signed URL 经常返回 403；errors 列表会列出来，需手动处理
