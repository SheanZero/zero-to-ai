---
name: szw-write
description: Unified write command for both first-draft authoring and polishing. Two modes (draft / polish / both) × two scopes (full article / specific outline section S<n>). Each invocation snapshots to .zero/writing-history/<slug>/ for retro and audit. Loads style-profile.md (if exists from szw-review) to mirror author voice. Status auto-advances brief_done/research_done/outline_done → draft_done on first full draft; section iterations and polish keep status. Use after /szw-outline (v2.0) or directly after /szw-discuss (v1.0); also use to fix HIGH issues from /szw-review.
---

# szw-write

把"起稿"和"润色"合到一条命令，支持全文 / 单节两种 scope。AI 主导内容（这是写作核心环节）；脚本管 04-draft.md 落盘 / section 替换 / history 快照 / 状态推进。**v1.0 主流水线的关键节点**——把 brief/outline 的设计转成可读的文章。

## 何时使用

- 跑完 `/szw-outline`（v2.0）或 `/szw-discuss`（v1.0），要起初稿
- review 报 HIGH issue → 回头改某节
- 起完稿想再润一遍（continued polish）

## 何时不用

- 01-brief.md 不存在 → 先 `/szw-discuss`
- 想看进度 → `/szw-progress`
- 想发布 → `/szw-publish`
- 想反审 → `/szw-review`

---

## 调用语法（4 种组合）

| 形式 | mode | target | 用途 |
|---|---|---|---|
| `/szw-write` | both | full | 默认：首次起稿 + 一次性润色 |
| `/szw-write --mode polish` | polish | full | 全文润色（review 后整体修） |
| `/szw-write S2` | both | S2 | 单节迭代（draft + polish） |
| `/szw-write S3 --mode polish` | polish | S3 | 单节润色（review 后修一节） |

底层脚本：

```bash
scripts/prepare-write.py [--slug <slug>] [--section S<n>]    # Phase 0
scripts/finalize-write.py commit --slug <slug> < <json>      # Phase 3
```

---

## 执行流程（4 phase）

### Phase 0：上下文收集（脚本）

```
prepare-write.py [--slug <slug>] [--section S<n>]
```

输出 JSON 关键字段：
- `slug` / `current_status` / `type` / `target_platforms` / `title`
- `brief` —— 解析后的 01-brief.md
- `sections` —— 解析后的 outline 节列表（含 S1/S2/.../id, n, title, core_claim, evidence_needed, reader_payoff, programmer_implication, counterargument, acceptance_criteria）
  - 来自 `03-outline.md`（v2.0 优选）或 brief 派生（`sections_source: brief_derived`，v1.0 兜底）
- `section_ctx` —— 仅 `--section` 模式给：包含目标节定义 + 当前 04-draft.md 中该节内容
- `mode_recommendation` —— `first_draft` / `polish_after_review` / `continued_polish`
- `long_term_assets`：
  - `style_profile` —— `.zero/style-profile.md` 路径（不存在为 null；存在则 AI **必读**作为风格基线）
  - `editorial_context` —— `EDITORIAL_CONTEXT.md` 路径（按需 Read 取 §3 Principles / §7 Style Guide）
  - `adrs` —— ADR 列表（与 prepare-discuss 一致）
  - `glossary` —— 术语文件列表
- `writing_history` —— 已有 snapshot 数 + 最近 5 个文件名（让 AI 知道之前改了什么）
- `warnings`

收到 JSON 后：
- **必读** 01-brief.md / 03-outline.md（首次起稿）
- **必读** style-profile.md（如果存在）—— 作者风格档案是写作复利的核心
- **按需** Read EDITORIAL_CONTEXT 的 §3 / §7 节
- **按需** Read 相关 glossary（术语统一）
- **按需** Read 02-research.md（HIGH-risk claim 的 safer_rewrite）

### Phase 1：Draft（draft / both 模式）

AI 主导，按 outline section 顺序起稿。**关键约束**：

1. **章节标记**：用 `## §<n>. <title>` 格式（详见 [`references/section-naming.md`](./references/section-naming.md)）
2. **acceptance_criteria 自检**：每节写完核对 outline §2 的 ACx
3. **HIGH-risk safer_rewrite**：02-research.md 标的 HIGH-risk claim 用 safer_rewrite 措辞
4. **风格对齐**：
   - **必避** style-profile.md anti-patterns（用户反复删除的词）
   - **优先** style-profile.md 的 sentence preferences（句式偏好 / 节奏）
   - **保留** 中英混用习惯（如 style-profile 标了的话）
5. **section 模式**只写 / 改指定节，不动其他

### Phase 2：Polish（polish / both 模式）

AI 主导精修：

1. **humanizer 过一遍**（参考 `humanizer` skill —— 可在主对话直接对照其反模式清单）
2. **EDITORIAL_CONTEXT.md §7 Banned Patterns** 全检
3. **style-profile anti-patterns** 全检（与 humanizer 互补）
4. **锐化判断** —— 删 "或许 / 可能 / 在某种程度上" 这种弱化词
5. **每节 reader_payoff 检查** —— 确保对得上 outline 的 payoff

### Phase 3：commit（脚本）

```bash
cat <<'EOF' | scripts/finalize-write.py commit --slug <slug>
{
  "mode": "both",
  "target": "full",
  "content": "<整篇 markdown>",
  "diff_summary": "initial draft (~3500 字)",
  "sections_changed": ["S1", "S2", "S3"],
  "advance_status_to": null
}
EOF
```

脚本动作：
- JSON 校验（mode / target / content / diff_summary / sections_changed 必填）
- 写入 04-draft.md：
  - target=full：整文件覆盖
  - target=S\<n\>：找 ## §`<n>` 节整段替换（content 必须以 heading 开头）
- 自动决策 status 推进（详见 [`references/write-schema.md`](./references/write-schema.md) "状态推进决策表"）
- ARTICLE.md：可能改 status + Status Log 追加
- STATE.md：刷 last_touched；可能改 status + next_action
- writing-history：snapshot 写入 + INDEX.md 加新行

---

## 失败处理

| 退出码 | 含义 | 应对 |
|---|---|---|
| `0` | 成功 | — |
| `1` | 不在专栏目录 | cd 到容器根 |
| `2` | slug / ARTICLE.md 不存在 | `/szw-progress` 看 active 表 |
| `3` | STATE.md 缺失 / row 找不到 | 检查 STATE.md 表结构 |
| `4` | stdin JSON 缺字段 / 字段值非法 | 看错误信息修 JSON |
| `5` | section 替换失败：04-draft.md 不存在 / 找不到 §`<n>` 节 / content 缺 heading | 用 target=full 先建初稿；或确认 section ID 与 outline 对得上 |
| `6` | advance_status_to 显式但当前 status 不允许此转移 | 取消显式 advance（让自动规则决定） |

---

## Gates

- **Pre-flight**：01-brief.md 必须存在；status 不强制（warning） outline 缺失只 warning（v1.0 brief_only 路径）
- **section content heading 强校验**：缺 heading → exit 5
- **section ID 校验**：必须 S<n> 形式且 outline 中存在
- **status 转移合法性**：显式 advance 必须从 `{brief_done, research_done, outline_done}` 出发
- **history 自增 NN**：脚本自动；不允许手动指定

---

## 与上下游的紧密集成

### ↑ 与 /szw-discuss 的集成

| 集成点 | 实现 |
|---|---|
| Status precondition | brief_done（最低）；其他状态也接受（warning） |
| 输入文件 | 01-brief.md（必需） |
| thesis 继承 | brief 的 thesis 作为全文锚点 |
| target_platforms 继承 | 不重问；用 brief 的值 |

### ↑ 与 /szw-research 的集成（v2.0）

| 集成点 | 实现 |
|---|---|
| 02-research.md 检测 | prepare 输出 `research_md_path`；存在则 warning 提示 AI 关注 HIGH-risk safer_rewrite |
| safer_rewrite 应用 | AI 起稿 HIGH-risk claim 优先用 safer_rewrite 措辞 |
| evidence 引用 | 起稿引证可链回 02-research.md §1 Evidence Cards |

### ↑ 与 /szw-outline 的集成（v2.0）

| 集成点 | 实现 |
|---|---|
| Status precondition | outline_done（最优）；brief_done 也接受（v1.0 兜底） |
| **section ID 稳定** | outline §1..§N → write S1..SN（同 n）；prepare-write 解析 outline section 7 字段全提供 |
| acceptance_criteria 检查 | 每节写完按 outline 的 ACx 自检 |
| reader_payoff 对齐 | 每节正文应回应 outline 的 reader_payoff |

### ↑ 与 /szw-review 的集成（v2.0）

| 集成点 | 实现 |
|---|---|
| review_failed 触发 polish | review 标某节 HIGH issue → 回 `/szw-write S<n> --mode polish` |
| style-profile 加载 | 必读 `.zero/style-profile.md`（review Phase 2 累积）；起稿和 polish 都对齐 |
| status 不动 | polish 期间 status 保持 review_failed；review 重跑时再决定 review_passed |

### ↓ 与 /szw-review 的集成（下游）

| 集成点 | 实现 |
|---|---|
| Status promotion → draft_done | 触发 review 的 prereq |
| 04-draft.md 是 review 的输入 | review 按节标记读 |
| writing-history 给 review Phase 2 | review 的风格捕获用 history snapshot 做 diff（看用户改了哪些 AI 起稿） |

### ↓ 与 /szw-publish 的集成

| 集成点 | 实现 |
|---|---|
| 04-draft.md 是 publish 的输入 | publish 把它打包成多平台版本 |
| target_platforms 决定打包数 | 来自 ARTICLE.md frontmatter |

---

## 完成 marker

```
✅ Committed write for <slug>
   mode: <mode> · target: <target>
   wrote: articles/<slug>/04-draft.md
   snapshot: .zero/writing-history/<slug>/<NN>-<mode>-<target>-<ts>.md (#NN)
   updated: articles/<slug>/ARTICLE.md
   status: <old> → <new>     # 或 <old> (unchanged) — <reason>
   STATE.md: row updated (last_touched=<date>)

👉 Next: /szw-review <slug>     # 或 continue writing 取决于场景
```

---

## 设计原则

1. **AI 写内容 / 脚本管 IO**：写作不是确定性 IO；JSON 校验 + section replace + snapshot + state 是脚本职责
2. **section ID 是稳定接口**：outline §<n> ↔ draft ## §<n> ↔ write target S<n>；三处一致
3. **history 是写作复利的源**：每次 commit snapshot；INDEX 时间线；review Phase 2 用 history 学风格
4. **status 推进只升一档**：brief_done/research_done/outline_done → draft_done；polish 不动 status；polish 后 review 决定 review_passed
5. **section 模式必须 heading**：避免 body-only 漏改 title 的隐患
6. **style-profile 是必读资产**：存在则用，不在就 warning（不阻断）
7. **outline 缺失允许 v1.0 兜底**：brief 派生 sections（每 supporting_claim 一节）；warning 提示
8. **不 git commit**：用户自行决定何时入版本（可参考 history snapshot 决定 commit 粒度）

---

## 与其他命令的关系

- `/szw-discuss` —— 必备上游
- `/szw-outline`（v2.0） —— 优选上游：section 边界来自这里
- `/szw-research`（v2.0） —— 间接上游：HIGH-risk claim 的 safer_rewrite 在起稿用
- `/szw-write`（本命令） —— draft + polish
- `/szw-review`（v2.0） —— 直接下游：04-draft.md 是输入；history 是 Phase 2 风格捕获的源
- `/szw-publish` —— 直接下游：打包多平台
- `humanizer` skill —— Phase 2 polish 的反模式参考

---

## 输出示例

### 示例 1：首次完整起稿（v2.0）

```
[内部] prepare-write.py → mode_reco=first_draft, sections_source=outline (4 节)

📍 准备起稿 2026-05-foo（industry-analysis），4 节
   读 01-brief.md / 03-outline.md / 02-research.md / EDITORIAL_CONTEXT §7
   ⚠️ style-profile.md 不存在（首次起稿）
   ⚠️ 02-research.md 标 HIGH-risk: C3 (90% 数字)，起稿用 safer_rewrite

[Phase 1] Draft：按 §1/§2/§3/§4 顺序起稿
  §1 (S1): 流水线越完整反而拖累单人作者
  §2 (S2): Skills 复利模型
  §3 (S3): GSD 真正定位
  §4 (S4): 5 个决策标准
  ✅ 各节自检 acceptance_criteria 通过
  ⚠️ §1 用了 C3 的 safer_rewrite

[Phase 2] Polish：
  - humanizer 反模式扫描：3 处
  - 锐化判断：删 5 个"或许/可能"
  - banned patterns 检查：清

[落盘]
✅ Committed write for 2026-05-foo
   mode: both · target: full
   wrote: articles/2026-05-foo/04-draft.md
   snapshot: .zero/writing-history/2026-05-foo/01-both-full-2026-05-06T18-50.md (#01)
   updated: articles/2026-05-foo/ARTICLE.md
   status: outline_done → draft_done
   STATE.md: row updated

👉 Next: /szw-review 2026-05-foo
```

### 示例 2：review 后修单节

```
> /szw-review 报：§2 reader_payoff 弱（HIGH issue）

> /szw-write S2 --mode polish

[内部] prepare-write.py --section S2
  → section_ctx.section + current_in_draft.body 给出
  → mode_reco=polish_after_review

读 03-outline.md §2 的 reader_payoff
读 04-draft.md 当前 §2 内容
读 .zero/style-profile.md（已有，10 篇文章累积）

[Phase 2] Polish §2：
  - 重写第二段，把 reader_payoff 提前
  - 删 2 个 "在某种程度上"（style-profile anti-pattern）
  - 加一个具体例子

[落盘]
✅ Committed write for 2026-05-foo
   mode: polish · target: S2
   wrote: articles/2026-05-foo/04-draft.md (§2 节替换)
   snapshot: .zero/writing-history/2026-05-foo/05-polish-S2-2026-05-06T20-15.md (#05)
   updated: ARTICLE.md
   status: review_failed (unchanged) — auto: keep status (no advance trigger matched)
   STATE.md: row updated

👉 Next: /szw-review 2026-05-foo (re-run after polish)
```

### 示例 3：v1.0 brief_only 兜底（无 outline）

```
[内部] prepare-write.py → sections_source=brief_derived
  warning: 03-outline.md missing → mode='brief_only'：起稿基于 brief 直接派生 sections

⚠️ 没跑 outline。每个 supporting_claim 派生一节（S1/S2/S3）。
   严谨度低于 v2.0；但够用如果文章不复杂。

[起稿... commit ...]

✅ Committed write for ...
   status: brief_done → draft_done
👉 Next: /szw-review ...
```

---

## 不实现的事

- **不调用 humanizer skill**：humanizer 是参考资源；polish 由 AI 自己跑（避免依赖嵌套）
- **不调用 sub-agent**：fan.md §7 的 `humanizer-editor` 是概念名；当前 AI 主对话直接做
- **不 git commit**：用户决定
- **不写 review 报告**：那是 `/szw-review` 的事
- **不修改 outline / brief**：发现 outline 错误 → escalate 回 outline 重跑，不擅自动手
- **不去重 history snapshot**：每次写都是新文件，便于追溯（清理交未来 `/szw-cleanup`）
- **不强制 acceptance_criteria 全过**：AI 自检；如果某 AC 拒绝采用，应在 diff_summary 注明
- **不自动跑 review**：commit 后只提示，让用户决定何时反审
