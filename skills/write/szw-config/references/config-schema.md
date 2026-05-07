# szw-config.json Schema

> 写作工作流配置项的语义、合法值、修改后果。
> 作为 `/szw-config` 的权威参考。

## 文件位置

`<cwd>/.zero/szw-config.json`

由 `/szw-init` 创建，由 `/szw-config` 维护。

---

## 顶层字段

| 字段 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `version` | string | `"1.0"` | 配置 schema 版本，AI 读取时按版本兼容旧字段 |
| `model_profile` | enum | `"balanced"` | 各阶段使用的模型策略，详见 §1 |
| `writing_lang` | enum | `"zh"` | 主写作语言，影响 humanizer / EDITORIAL_CONTEXT §15 |
| `default_platforms` | string[] | `["blog", "wechat"]` | `/szw-publish` 默认目标平台 |
| `hooks` | object | （见 §2） | hook 开关 |
| `subagents` | object | （见 §3） | 各 phase 的子 agent 路由（特别是 Codex） |
| `limits` | object | （见 §4） | 循环次数 / 字数硬上限 |
| `style_capture` | object | （见 §5） | 风格学习开关与阈值 |
| `gates` | object | （见 §6） | 流水线阻断 gate 配置 |

---

## §1 `model_profile` 取值

| 值 | 含义 | 适用场景 |
|---|---|---|
| `quality` | 处处 Opus（除 verification） | 商业关键专栏起步阶段；不能出错 |
| `balanced` | Opus 规划阶段 + Sonnet 执行阶段（默认） | 日常开发 |
| `budget` | Sonnet 写 + Haiku 研究 / 验证 | 个人项目 / 探索 / 预算紧 |
| `inherit` | 继承当前 session 模型 | OpenCode 等多模型 CLI |

修改后果：所有后续 skill 调用按新 profile 分配模型；不影响已发布文章。

---

## §2 `hooks` 字段

```json
"hooks": {
  "pre_tool_use": true,
  "post_tool_use": true,
  "stop": true
}
```

| 字段 | 默认 | 关闭后果 |
|---|---|---|
| `pre_tool_use` | `true` | 失去对 EDITORIAL_CONTEXT / published 文件的写保护 |
| `post_tool_use` | `true` | STATE.md 不再自动更新；ADR INDEX 不自动同步 |
| `stop` | `true` | 会话结束时不再提示 `/szw-pause` 留 handoff |

---

## §3 `subagents` 路由

```json
"subagents": {
  "evidence_researcher": "codex",
  "claim_diagnoser": "codex",
  "skeptical_reviewer": "codex"
}
```

| 子 agent | 默认路由 | 替代值 |
|---|---|---|
| `evidence_researcher` | `codex` | `claude` / `gemini`（用 Claude 自查容易自我合理化） |
| `claim_diagnoser` | `codex` | 同上 |
| `skeptical_reviewer` | `codex` | 同上（跨 AI 视角是反审的灵魂） |

**强烈建议保持 `codex`**：自审取代反审是流水线最大的失败模式之一。

---

## §4 `limits` 循环 / 字数

```json
"limits": {
  "review_revision_max": 2,
  "diagnose_revision_max": 2,
  "quick_word_limit": 800
}
```

| 字段 | 默认 | 说明 |
|---|---|---|
| `review_revision_max` | `2` | review-write polish 循环最多 2 轮，超出 escalate |
| `diagnose_revision_max` | `2` | research Phase 2 HIGH-risk 内部循环最多 2 轮 |
| `quick_word_limit` | `800` | `/szw-quick` 字数上限，超出自动转 `/szw-new-article` |

调高这些值会增加 AI 自动重试，但失败模式会被掩盖；调低会更快 escalate 给人。

---

## §5 `style_capture` 风格学习

```json
"style_capture": {
  "enabled": true,
  "diff_threshold_pct": 5,
  "merge_after_n_reviews": 10,
  "min_pattern_frequency": 3
}
```

| 字段 | 默认 | 说明 |
|---|---|---|
| `enabled` | `true` | 关闭后 review Phase 2 跳过；失去 AI 越写越像作者的复利 |
| `diff_threshold_pct` | `5` | draft vs history 快照的修改字数百分比阈值；< 5% 时跳过学习 |
| `merge_after_n_reviews` | `10` | 累积 N 次 review 后自动合并 Recent Edits → Stable Patterns |
| `min_pattern_frequency` | `3` | 合并时低于该频次的规则被丢弃 |

---

## §6 `gates` 流水线阻断

```json
"gates": {
  "block_draft_on_missing_brief": true,
  "block_publish_on_missing_review": true,
  "auto_archive_grill_failed": false
}
```

| 字段 | 默认 | 说明 |
|---|---|---|
| `block_draft_on_missing_brief` | `true` | 跳过 `/szw-discuss` 直接 `/szw-write` 时阻断 |
| `block_publish_on_missing_review` | `true` | 没跑 `/szw-review` 直接 `/szw-publish` 时阻断 |
| `auto_archive_grill_failed` | `false` | 拷问失败的文章是否自动移到 articles/archived/ |

关闭 gates 会让流水线更"流畅"但失去质量保险；除非短评 / quick 场景，建议保持 `true`。

---

## 修改建议

| 场景 | 配置调整 |
|---|---|
| 起步阶段 / 不熟练 | `model_profile: quality`，所有 gates 开 |
| 日常 / 已熟练 | 保持默认 |
| 时间紧 / 短评多 | `quick_word_limit` 加大；`block_*` 仍开（不要为了快关 gates）|
| 风格已稳定，不想再学 | `style_capture.enabled: false`（但失去复利红利） |
| 团队多人协作 | `subagents` 全部保持 `codex`（避免自审闭环） |

---

## 增删字段

新增字段时：
1. 提升 `version` 到 `1.1` / `2.0`
2. 在本 schema 文档加说明
3. 在 SKILL.md 的 `--<field>` 子命令清单加路由
4. 旧专栏的 config 自动按 `version` 字段做兼容（缺失字段用默认值填充）

不允许删除已有字段，只能用新版本号弃用。
