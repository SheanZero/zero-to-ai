---
name: szw-discuss
description: Stress-test the topic AND structure it into an article brief in one command. Two-phase workflow (1) interview-style grill (via szw-topic-grill) against the column's editorial constitution (EDITORIAL_CONTEXT + ADRs), (2) structure into 01-brief.md with the grill Q&A as appendix. Use right after /szw-new-article when starting the article pipeline. Auto-routes to the latest active article if no slug given.
---

# szw-discuss

把"选题拷问"和"写 brief"合并成一条命令。AI 主导拷问对话；脚本管 IO + 状态推进。

## 何时使用

- 跑完 `/szw-new-article` 后准备启动流水线
- ARTICLE.md 已存在但 status 还是 `created`
- 用户主动说"开始拷问 / 写 brief / 讨论选题"

## 何时不用

- ARTICLE.md 不存在 → 先 `/szw-new-article`
- status 已是 `brief_done` → 通常去 `/szw-write`；除非用户明说要重新 discuss
- 想看流程现状 → `/szw-progress`

---

## 调用语法

| 形式 | 行为 |
|---|---|
| `/szw-discuss` | 默认：取 STATE.md last_touched 最大的 active slug |
| `/szw-discuss <slug>` | 指定 article |
| `/szw-discuss --abort <slug> --reason "..."` | 手动 abort（grill 失败已确认） |

底层脚本：

```bash
scripts/prepare-discuss.py [--slug <slug>]                    # Phase 0：收集上下文
scripts/finalize-discuss.py commit --slug <slug> < <json>     # Phase 3：落盘 brief + 推进 status
scripts/finalize-discuss.py abort  --slug <slug> --reason "...."  # 移到 archived/
```

---

## 执行流程（4 phase）

### Phase 0：上下文收集（脚本）

```
prepare-discuss.py [--slug <slug>]
```

输出 JSON：
- `slug` 路由结果
- `article` 当前 frontmatter / type / thesis 占位
- `context_paths` —— EDITORIAL_CONTEXT.md / COLUMN.md 路径（按需 Read）
- `adrs` —— 所有 ADR 的 ID + 标题 + 路径
- `warnings` —— 例如"status 已是 brief_done，重跑会覆盖"

收到 JSON 后：
- 读 `context_paths.editorial_context` 的 §3 Principles + §5 Topic Boundaries（用于拷问对齐）
- 视拷问需要按需 Read 单个 ADR 文件

### Phase 1：拷问（AI 主导对话）

参考已有 [`../szw-topic-grill/SKILL.md`](../szw-topic-grill/SKILL.md) 的 9 问。**关键扩展**：每问完一题后默念三件事：

1. 这条答复是否与某条 ADR 直接冲突？（记 alignment_check.adrs_consulted）
2. 这条答复是否与 EDITORIAL_CONTEXT §5 的 Out of Scope 冲突？（记 conflicts）
3. 是否触发 type 侧重的红线？（参考 [`references/article-type-emphasis.md`](./references/article-type-emphasis.md)）

### Escalation / Abort 判断

- **Abort** —— 任意一条直接冲突（如 ADR 0001 + 选题就是 benchmark dump）
  - 跟用户确认"建议放弃这个选题，理由：XXX"
  - 用户同意 → 调 `finalize-discuss.py abort --slug <slug> --reason "..."`
  - 用户坚持继续 → 把冲突写进 `alignment_check.conflicts`（commit 会拒绝，强制走 abort 或修选题）
- **Escalation** —— 拷问 5 题以上用户答"不知道 / 不确定"
  - "选题模糊到拷问无法收敛，建议先 `/szw-capture` 把灵感入 inbox 沉淀，再开 article"
  - 用户同意 → abort
  - 用户坚持 → 继续，并在 `alignment_check.notes` 标注"5+ 题模糊回答"

### Phase 2：结构化 brief（AI 整理）

按 [`references/brief-schema.md`](./references/brief-schema.md) 的 stdin JSON 字段，AI 在对话内完成结构化：

- 把拷问 9 问转成 `grill_qa` 数组（保留 user_answer / ai_recommendation / final 三段）
- 提炼 thesis / reader_payoff / supporting_claims / counterargument / evidence_needed / out_of_scope
- 视 article type 加权（见 [`references/article-type-emphasis.md`](./references/article-type-emphasis.md)）
- 填 `alignment_check`（adrs_consulted / principles_consulted / conflicts / notes）

**对齐 self-check**（在 commit 前）：
- thesis 是否过模糊？industry-analysis 必须断言式
- counterargument 是否单薄？industry/product 类型必须至少 1 条尖锐反方
- evidence_needed 列表是否够具体？避免"找一些数据"这种空话

### Phase 3：落盘（脚本）

```bash
cat <<'EOF' | scripts/finalize-discuss.py commit --slug <slug>
{ ... brief json ... }
EOF
```

脚本动作：
- 渲染 `articles/<slug>/01-brief.md`（正文 + 附录 A 拷问 Q&A + 附录 B 宪法对齐）
- 改写 `articles/<slug>/ARTICLE.md`：
  - frontmatter `status: created → brief_done`
  - frontmatter `target_platforms`（若 JSON 提供新值）
  - Thesis 段落内容替换为 brief 的 thesis
  - Status Log 追加 `brief_done via /szw-discuss` 一行
- 改写 `.zero/STATE.md` Active 表该行：`status / last_touched / next` 三列

---

## 失败处理

| 退出码 | 含义 | 应对 |
|---|---|---|
| `0` | 成功 | — |
| `1` | 不在专栏目录 | 提示 cd 到容器根 |
| `2` | slug 不存在 / ARTICLE.md 缺失 | 跑 `/szw-progress` 看 active 表 |
| `3` | STATE.md 缺失 / 默认路由失败（无 active article） | `/szw-new-article` 起新文章 |
| `4` | stdin JSON 缺字段 / 解析失败 | 看错误信息，参考 brief-schema.md 补字段 |
| `5` | alignment_check.conflicts 非空 | 二选一：(a) 跟用户确认 abort；(b) 修 brief 解冲突 |
| `6` | abort 时 archived/<slug>/ 已存在 | 旧 abort 残留，需手动清理或换 slug |

---

## Gates

- **Pre-flight**：ARTICLE.md 必须存在；status 不强制（允许重 discuss，会覆盖）
- **拷问对齐 gate**：commit 时 `alignment_check.conflicts` 非空 → exit 5；强制走 abort 或修 brief
- **Stdin JSON gate**：8 个 required 字段缺一不可；grill_qa 必须非空
- **Abort gate**：archived/<slug>/ 已存在 → 拒绝（避免覆盖历史 abort）
- **回填一致性**：commit 把 thesis 同步到 ARTICLE.md（让 `/szw-resume` 不读 brief 也能看到）

---

## 完成 marker

### Commit 成功

```
✅ Committed brief for <slug>
   wrote: articles/<slug>/01-brief.md
   updated: articles/<slug>/ARTICLE.md (status → brief_done)
   updated: STATE.md (Active row → brief_done)

👉 Next: /szw-write <slug>
```

### Abort 成功

```
⚠️ Aborted <slug>
   moved: articles/<slug>/ → articles/archived/<slug>/
   reason: <reason>
   updated: STATE.md (Active → Recently Completed, archived)
```

---

## 设计原则

1. **AI 拷问 / 脚本落盘**：grill 是对话过程，脚本碰不到；commit 是确定性 IO，AI 不直接写 STATE.md
2. **拷问与宪法绑定**：每问都要对照 ADR + EDITORIAL_CONTEXT；commit 阶段 conflicts 非空 = 强制 abort
3. **brief 自带追溯**：附录 A 完整保留 grill Q&A，附录 B 保留对齐结论；后续 retro / audit 不用回看对话历史
4. **abort 是首选 escape hatch**：拷问失败不要硬塞 brief；移到 archived/ 保留启发价值
5. **thesis 单点真相**：写在 01-brief.md 是权威源；同步回填 ARTICLE.md 仅作快捷查看（resume 用）
6. **支持重 discuss**：status != created 时 warnings 提示，但不阻断；用户改主意可以重跑

---

## 与其他命令的关系

- `/szw-new-article` —— 必须先（创建 ARTICLE.md + Active 行）
- `/szw-discuss`（本命令） —— 拷问 + brief
- `/szw-research`（v2.0） —— 接 brief 找证据；commit 后 v2.0 推荐它
- `/szw-write`（v1.0） —— 接 brief 直接起稿；commit 后 v1.0 推荐它
- `/szw-progress` —— 看 active 表 / 下一步推荐
- `/szw-resume <slug>` —— 跨 session 回到本 article 的拷问中断点（暂未实现自动恢复对话）

---

## 输出示例

### 示例 1：默认路由 + grill + commit

用户：`/szw-discuss`

```
[内部] 跑 prepare-discuss.py → slug=2026-05-skills-vs-gsd, type=industry-analysis

📍 准备拷问 2026-05-skills-vs-gsd（industry-analysis）。
   读了 EDITORIAL_CONTEXT §3 Principles + §5 Topic Boundaries。
   ADR 关注：0001（no-benchmark-dumping）、0002（tool-review-needs-action）。

开始 9 问拷问。逐题作答。

Q1. 这篇文章挑战哪个流行误解？
   AI 推荐：误解"流水线越完整越专业"
   你的答案？

> （用户答：是的，正是这个）

[...省略 Q2-Q9...]

✅ 拷问通过。无 ADR 冲突。
正在结构化 brief 并落盘...

✅ Committed brief for 2026-05-skills-vs-gsd
   wrote: articles/2026-05-skills-vs-gsd/01-brief.md
   updated: articles/2026-05-skills-vs-gsd/ARTICLE.md (status → brief_done)
   updated: STATE.md (Active row → brief_done)

👉 Next: /szw-write 2026-05-skills-vs-gsd
```

### 示例 2：拷问发现 ADR 冲突 → abort

```
Q4. 这是哪种 article type？

> 我想做一个 GSD vs Skills 的 benchmark 跑分对比，列各种维度的得分

⚠️ 发现冲突：
   你描述的方向是 benchmark 跑分搬运，违反 ADR 0001（no-benchmark-dumping）。

建议：
  1. 改方向 → 写"工作流取舍"而非"得分对比"
  2. 放弃此选题 → /szw-discuss --abort

你选 1 还是 2？

> 2

正在 abort...

⚠️ Aborted 2026-05-skills-vs-gsd
   moved: articles/2026-05-skills-vs-gsd/ → articles/archived/2026-05-skills-vs-gsd/
   reason: 选题方向是 benchmark 跑分搬运，违反 ADR 0001
   updated: STATE.md (Active → Recently Completed, archived)
```

### 示例 3：拷问中模糊回答超过 5 题 → escalation

```
Q6. 你需要找哪些证据？

> 不知道，先看再说

[已 5 题模糊回答]

⚠️ 拷问 5 题以上用户回答"不知道 / 不确定"。

选题尚未到能写的成熟度。建议：
  1. /szw-capture 把当前思考存到 inbox/pending/，沉淀几天再开
  2. 强行继续（brief 会标注"5+ 题模糊"，质量风险）

你选？

> 1

正在 abort（理由：选题成熟度不足，转 inbox 沉淀）...

[abort 输出 + 提示 /szw-capture]
```

---

## 不实现的事

- **不调用证据查询子 agent**：那是 `/szw-research`（v2.0）的事
- **不写 outline / draft**：分别由 `/szw-outline`（v2.0）/ `/szw-write` 负责
- **不修改 EDITORIAL_CONTEXT / ADR**：拷问中发现新原则建议，应口头提示用户跑 `/szw-context` 或 `/szw-adr`，不自动写
- **不 git commit**：用户自行决定何时提交
- **不重启对话恢复拷问**：被打断后下次重跑，从 Q1 重新开始（grill_qa 的 user_answer 短，重答成本可控）
