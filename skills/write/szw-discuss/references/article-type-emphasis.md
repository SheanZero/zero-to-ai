# Article Type Emphasis（brief 阶段）

> 4 种 article type 在 brief 阶段的侧重提示。给 AI 在 grill 拷问 + 结构化 brief 时参考。
> 不是模板枚举（那样太死板）；是"思考权重"建议。

---

## industry-analysis（行业分析）

**核心**：判断 + 论证链 + 反方观点
**brief 重点**：
- `thesis` —— 必须断言式（不是"探讨"），有可被反驳的强观点
- `supporting_claims` —— 每条挂证据/数据；至少 3 条
- `counterargument` —— **强必需**；至少 1 条尖锐反方
- `evidence_needed` —— 行业数据 / 公开声明 / 趋势报告（research 阶段重点）
- `reader_payoff` —— 读者读完能做出哪个具体决策

**典型 grill 重点问**：Q1 误解 / Q3 思维改变 / Q7 反方 / Q9 行动落点

**反模式**：
- 罗列 benchmarks（违反 ADR 0001）
- 没有论证链的"信息汇总"
- 没有反方观点的单边陈述

---

## programmer-advice（程序员建议）

**核心**：可执行步骤 + 适用条件 + 失效边界
**brief 重点**：
- `thesis` —— 一句话方法论 / 实践
- `supporting_claims` —— 每条对应一个具体场景或步骤
- `reader_payoff` —— **强必需**：读者读完能照做的 N 步操作
- `out_of_scope` —— **强必需**：什么场景下本建议失效（避免被人用错）
- `evidence_needed` —— 实际跑过的代码 / 工具 / 命令记录

**典型 grill 重点问**：Q2 受众（资历）/ Q3 思维改变 / Q9 takeaway（必须可操作）

**反模式**：
- 抽象空泛的"应该" / "建议"
- 没有边界条件的"银弹"建议
- 程序员看完不知道下一步做什么

---

## product-analysis（产品评测）

**核心**：评测维度 + 实测证据 + 行动建议
**brief 重点**：
- `thesis` —— 对产品的核心判断（推荐 / 不推荐 / 适合谁不适合谁）
- `supporting_claims` —— 每条对应一个评测维度（性能 / DX / 价格 / 生态）
- `evidence_needed` —— **强必需**：实际跑过的 benchmark / 案例 / 截图
- `counterargument` —— 产品方 / 粉丝会怎么辩护
- `reader_payoff` —— 读者读完知道是否要采用 / 切换 / 跳过

**典型 grill 重点问**：Q1 误解 / Q4 类型 / Q6 证据 / Q9 行动（推荐/拒绝）

**反模式**：
- 功能清单堆砌（不是评测）
- 没有实测就下判断
- 评测后不给"该不该用"的判断（违反 ADR 0002）

---

## tech-blog（通用技术博文）

**核心**：兜底类型；适合不属于上面 3 类的内容
**brief 重点**：
- 仍然要有 `thesis` —— 哪怕是"科普 X 概念"也要有立场
- `reader_payoff` —— 读者读完能多懂什么
- `supporting_claims` 和 `counterargument` 可以更轻
- `evidence_needed` 视主题而定

**典型场景**：教程 / 概念解释 / 个人感悟 / 工具试用记

**反模式**：
- 用 tech-blog 兜底逃避 industry-analysis 应有的论证密度
- 流水账式记录没有 takeaway

---

## 跨类型反模式（任何 type 都要避免）

| 反模式 | 违反 |
|---|---|
| 纯 benchmark 跑分搬运 | ADR 0001 |
| 工具评测后不给行动建议 | ADR 0002 |
| 焦虑营销 / 蹭热点 | ADR 0003 |
| thesis 模糊到 9 问拷问回答不了 5 个以上 | szw-discuss escalate gate |
| brief 与 EDITORIAL_CONTEXT.md §5 Out of Scope 冲突 | brief alignment gate |

---

## AI 使用提示

- grill 阶段问完 9 问后，**先按本文做自查**，再进 Phase 2 结构化
- 把侧重映射到 `alignment_check.notes` 字段（让人审 brief 时知道哪些维度被加权）
- 如果某 type 强必需的字段（如 industry-analysis 的 counterargument）单薄，建议 escalate 让用户补强而非降级 commit
