# 04-draft.md / Write commit Schema

> `/szw-write commit` 通过 stdin 接收的 JSON 字段契约 + 04-draft.md 的节标记约定 + writing-history 文件结构。
> 修改本文档须同步更新 `scripts/finalize-write.py` 的 `REQUIRED_TOP_FIELDS / VALID_*` 集合 + render / replace 逻辑。

---

## stdin JSON top fields

| 字段 | 类型 | 必需 | 说明 |
|---|---|---|---|
| `mode` | enum | ✅ | `draft` / `polish` / `both` |
| `target` | enum/str | ✅ | `full` 或 `S<n>`（如 `S2`） |
| `content` | str | ✅ | 要写入的 markdown；非空 |
| `diff_summary` | str | ✅ | 一行简述变更（INDEX.md 渲染用）；非空 |
| `sections_changed` | list[str] | ✅ | 变更涉及的 section ID 列表（如 `["S2"]`）；可空数组 |
| `advance_status_to` | enum/null | ⛔ | 显式 override；只接受 `"draft_done"` 或 `null` |

### `mode` 含义

| mode | 用途 |
|---|---|
| `draft` | 起初稿（无 polish 步骤）；通常配 target=full |
| `polish` | 仅润色（无 draft 步骤）；常用于 review_failed 后修复 |
| `both` | draft + polish 一次跑完（首次完整起稿默认） |

### `target` 含义

| target | 行为 |
|---|---|
| `full` | 整文件覆盖；首次起稿用 |
| `S<n>` | 仅替换 ## §`<n>`. xxx 节内容；04-draft.md 必须存在；content 必须以 `## §<n>` 开头 |

### `content` 形式约定

- **target=full**：整篇文章 markdown，从 `# Title` 开始
- **target=S<n>**：只包含该节，**第一行必须是 `## §<n>. <title>` heading**（脚本严格校验）

### `advance_status_to` 与自动规则

- `null` 或缺失：脚本按规则自动决定
  - `target=full + mode in {draft, both} + current_status in {brief_done, research_done, outline_done}` → 升 `draft_done`
  - 其他场景：保持当前 status
- `"draft_done"`：显式要求升 status 到 `draft_done`
  - 仅当 `current_status in {brief_done, research_done, outline_done}` 才接受；否则 exit 6

---

## 04-draft.md 节标记约定

每个有编号的章节用：

```
## §<n>. <title>

<body...>
```

例：

```
## §1. 流水线越完整反而拖累单人作者

这是个反直觉的观察...

## §2. Skills 复利模型

Skills 的复利在 AI 越用越懂作者...
```

**节边界由脚本识别**：`^## §\d+[\.\s]`。下一个 `## §M`、其他 `## ` 标题、或 EOF 是节末尾。

非编号 H2（如 `## 引子` / `## 结语`）不被节系统管辖；section 模式的 replace 只处理编号节。

---

## writing-history 文件结构

`<column_root>/.zero/writing-history/<slug>/`

```
INDEX.md                              # 时间线索引
01-both-full-2026-05-06T18-50.md     # 第 1 次：全文 both
02-polish-S2-2026-05-06T19-30.md     # 第 2 次：S2 节 polish
03-polish-full-2026-05-07T10-15.md   # 第 3 次：全文 polish
...
```

### snapshot 文件命名

`NN-<mode>-<target>-<YYYY-MM-DDTHH-MM>.md`

- `NN`: 2 位整数自增（最多 99 篇快照后变 3 位）；脚本自动管理
- `mode`: draft / polish / both
- `target`: full / S<n>
- 时间戳：本地时间，分钟精度

### snapshot 文件内容

```markdown
<!--
mode: <mode>
target: <target>
timestamp: <iso>
sections_changed: <list>
diff_summary: <text>
-->

<原 stdin content 原样保留>
```

snapshot 是**改动当时的内容**，不是改动后的整篇 04-draft.md。
- target=full：snapshot = 整篇
- target=S<n>：snapshot = 仅该节

### INDEX.md 结构

```markdown
# Writing History — <slug>

> Auto-maintained by `/szw-write`. Latest first.

| # | When | Mode | Target | Sections | Diff summary |
|---|---|---|---|---|---|
| 02 | 2026-05-06 19:30 | polish | S2 | S2 | 锐化措辞，去掉"或许" x3 |
| 01 | 2026-05-06 18:50 | both | full | S1, S2, S3 | initial draft (~3500 字) |
```

新行**插在表头部**（最新优先）。

---

## 状态推进决策表

| current_status | target | mode | explicit advance | new_status | 行为 |
|---|---|---|---|---|---|
| brief_done / research_done / outline_done | full | draft / both | null | draft_done | 自动升级 |
| brief_done / research_done / outline_done | full | polish | null | (unchanged) | polish-only 不升级 |
| brief_done / research_done / outline_done | S\<n\> | (任意) | null | (unchanged) | section 改动不升级 |
| draft_done | (任意) | (任意) | null | draft_done | 已升级，保持 |
| review_failed | (任意) | (任意) | null | review_failed | 等 review 重新跑 |
| review_passed | (任意) | (任意) | null | review_passed | 微调不影响通过状态 |
| brief_done / research_done / outline_done | (任意) | (任意) | "draft_done" | draft_done | 显式接受 |
| draft_done / review_* / 其他 | (任意) | (任意) | "draft_done" | exit 6 | 拒绝非法转移 |

STATE.md 同步更新：
- `last_touched` 永远刷新成今天
- `status` 跟随 ARTICLE.md
- `next_action`：升到 `draft_done` 时 → `/szw-review`；其他场景保持原值

---

## 退出码

| Code | 含义 |
|---|---|
| 0 | 成功 |
| 1 | 不在专栏目录 |
| 2 | slug / ARTICLE.md 不存在 |
| 3 | STATE.md 缺失 / 解析失败 / row 找不到 |
| 4 | stdin JSON 缺字段 / 字段值非法 |
| 5 | section 替换失败：04-draft.md 不存在 / 找不到目标 §`<n>` 节 / content 缺 heading / target 形式非法 |
| 6 | advance_status_to 显式指定但当前 status 不允许此转移 |

---

## 同步更新清单

- [ ] `scripts/finalize-write.py` —— `REQUIRED_TOP_FIELDS / VALID_MODES / VALID_ADVANCE / ADVANCEABLE_FROM` + `decide_status_advance()` + `replace_section()` + `write_snapshot()` + `update_history_index()`
- [ ] `scripts/prepare-write.py` —— sections 解析 / mode 推荐
- [ ] `references/write-schema.md` —— 本文档
- [ ] `references/section-naming.md` —— 节标记约定的细节 + AI 起稿约定
- [ ] `study/fan.md` §3.4 —— 命令规约
- [ ] 下游 `/szw-review`：04-draft.md 读取按本节标记约定
- [ ] 下游 `/szw-publish`：04-draft.md 是输入
