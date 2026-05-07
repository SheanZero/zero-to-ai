# Section Slice Pattern

> 给 AI 在 Phase 2（拆片）时参考。原则来自 mattpocock/skills 的 `to-issues` 模式（vertical slice）。
> 改自 [`write-progress/flow.md`](../../../../write-progress/flow.md) §13。

---

## 核心原则

**Each section is a vertical argument slice** —— 自含完整论证 + 证据 + 行动。
不是"背景 / 分析 / 结论"那种横向章节（除非每节内部都有清晰 claim）。

---

## 7 个必填字段

每个 section slice 都要有：

| 字段 | 含义 | 缺失会导致 |
|---|---|---|
| `title` | 章节标题；带具体观点（不是"背景介绍"） | 读者不知道这节要看什么 |
| `core_claim` | 1-2 个 claim ID（C1 / C1+C2） | 章节没有论证锚点 |
| `evidence_needed` | 此节需要的证据；链回 02-research.md | 起稿时 AI / 作者不知道找什么 |
| `reader_payoff` | 读完此节的具体收益（不是"了解 X"） | 节缺乏价值密度 |
| `programmer_implication` | 程序员可执行的下一步 | 节没有落点 |
| `counterargument` | 节内的反方 + 回应（与全文 thesis_map.counter 不同层级） | 节缺平衡，论证软 |
| `acceptance_criteria` | 写完此节的完成标准（2-4 条） | 写完没法 self-test |

**Acceptance criteria 写法**：
- ✅ "AC1: 段落能让读者 30 秒内 self-test 自己是否在错误工具上"
- ❌ "AC1: 写得清楚一些"（不可验证）
- ✅ "AC2: 至少给出 1 个真实例子"
- ❌ "AC2: 内容充实"（不可量化）

---

## 4 条规则

### 1. Each section proves one claim

每节只证一个 claim（可以是组合 C1+C2，但目标统一）。多个不相关 claim 塞一节 = 节内论证发散。

**反例**：节 §3 同时讲 "GSD 适合大团队" + "Skills 学习曲线低" → 拆成两节。

### 2. Each section must connect to the main thesis

每节都能回答"这节是怎么推 thesis 的"。不能推就删。

**反例**：节 §5 "agentic coding 历史回顾" 在 thesis "skills vs GSD ROI" 文里 → 删，或拆到背景节并强加 claim。

### 3. Each section should produce a reader takeaway

读完一节读者必须能"做什么"或"想不同"。纯科普不算 takeaway。

**反例**：reader_payoff = "了解 GSD 的设计哲学" → 改 "知道 GSD 是为大团队设计；下次评估时不再以个人作者视角批评它"。

### 4. Prefer 4-6 strong sections over 10 weak sections

宁可少而强，不要多而弱。10 节弱 section 读者 5 节后弃文；4-6 节每节都有 takeaway 读者读到底。

**操作**：Phase 2 拆完先数 section 数。
- < 3 节：thesis 可能太单薄；考虑回 brief 拆出更多 supporting
- 4-6 节：理想区间
- 7-8 节：考虑合并相邻或弱节合到强节
- > 8 节：必须拆文章 / 改 series（见 `/szw-new-series` v2.0）

---

## 横向章节例外

"背景 / 分析 / 结论"这种横向章节**通常应避免**，但有例外：

| 章节 | 何时可以保留 | 何时拆 |
|---|---|---|
| 背景 / 概念铺垫 | 节内有清晰 claim（如"agent 概念被滥用"），不是单纯定义堆 | 单纯定义 → 拆到 glossary 或合并到第一个论证节 |
| 案例分析 | 案例本身推某个 claim | 案例只是 illustration → 嵌入对应论证节 |
| 结论 / takeaway 总结 | 是综合 takeaway 卡（如本设计的"5 个决策标准"），独立 section 才有载体 | 只是 thesis 重述 → 删，让 thesis_map 处理 |

---

## 拆片质检自查（Phase 2 末尾）

在 verdict='passed' 之前问自己：

- [ ] 每节都满足 4 条规则？
- [ ] 4-6 节区间？（接受 3-8）
- [ ] 每节 acceptance_criteria 可验证 / 可量化？
- [ ] thesis_map.supporting 里每个 claim 都至少被 1 节引用？（避免 brief 死代码）
- [ ] 没有相邻两节论证重复？
- [ ] reader_payoff 不是抽象动词（"了解" / "理解"）？

任何一条 ❌ → 内部循环回 Phase 1（最多 2 轮）；2 轮仍 ❌ → verdict='weak_section_unresolved'，escalate 到用户。

---

## 与 brief 的对齐自查

- supporting_claims 列表 vs section_slices 引用的 claim_id：
  - **未被引用的 claim**：要么在 outline 阶段说明"intentionally dropped"，要么回 brief 改
  - **section 引用了 brief 没有的 claim**：禁止；必须先回 brief 加 supporting

- target_platforms：outline 不再问；继承 brief
- counter（thesis_map.counter）：来自 brief.counterargument，可以新加，但不该减
