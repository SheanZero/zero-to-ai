# Section Naming Convention

> 04-draft.md 的章节标记规则 + AI 起稿时如何对齐 outline。
> 由 prepare-write.py 给 AI 提示，由 finalize-write.py 的 section replace 强制。

---

## 唯一约定

每个**有编号**的章节用如下格式开头：

```
## §<n>. <title>
```

- `##` 是 H2（不要用 H3）
- `§` 必须是这个全角字符（U+00A7 SECTION SIGN）
- `<n>` 是节序号，整数（1, 2, 3, ...）
- `.` 是分隔符（必需）
- `<title>` 是节标题

例：

```markdown
## §1. 流水线越完整反而拖累单人作者
## §2. Skills 复利模型
## §3. GSD 的真正定位
```

变体识别（finalize 节替换的正则容忍）：
- `## §1.` ✅
- `## §1 ` ✅（点可省，但用空格代替）
- `##  §1.` ❌（多余空格）—— 避免
- `### §1.` ❌（H3）—— 不属于编号节
- `## §1, ` ❌（中文逗号）—— 避免

---

## 与 outline 的映射

prepare-write.py 输出的 sections 列表里每节有 `id: "S<n>"` 和 `n: <int>`。AI 起稿时**保留这个 n**：outline 的 §1 → draft 的 ## §1.；outline 的 §2 → draft 的 ## §2.

例：
- outline `### §1. 流水线越完整反而拖累单人作者` → draft `## §1. 流水线越完整反而拖累单人作者`
- title 可微调（让正文标题更"读得出来"）；`<n>` 不动

---

## 非编号 H2 是允许的

```markdown
# Skills 比 GSD 更吃 ROI

## 引子            ← 非编号；不是节系统的 first-class 公民

## §1. 第一节内容
...

## §2. 第二节内容
...

## 结语            ← 非编号；同上
```

- 非编号 H2 不能用 `--target S<n>` 替换
- 想替换非编号段落 → 用 `target=full`
- 推荐：把"引子 / 结语"也放到节里（§1 起手 / §N 收尾），便于版本管理

---

## section content 提交规则

target=S\<n\> 时，stdin JSON 的 `content` 字段：

```json
{
  "target": "S2",
  "content": "## §2. 新标题（可改）\n\n新正文段落 1\n\n新正文段落 2\n"
}
```

**第一行必须是 `## §2.` 或 `## §2 ` 开头**。脚本严格校验，缺则 exit 5。

理由：避免"贴 body 但忘 heading"导致 §2 标题丢失；显式提交 heading 让 AI 主动确认 title 是否要改。

---

## section 替换的边界

`finalize-write.py` 的 `replace_section()` 找下列模式作为节末尾：

- 下一个 `## §<m>.` 或 `## §<m> `（其他编号节）
- 下一个 `## ` 开头（任意 H2，包括非编号）
- 文件结尾

例：04-draft.md 是

```
## §1. A
body 1
## §2. B
body 2
## §3. C
body 3
## 结语
ending
```

提交 `target=S2`, content=`## §2. B-new\n\nbody 2 new`：

```
## §1. A
body 1
## §2. B-new       ← 替换了 heading + body
body 2 new
## §3. C           ← 不变
body 3
## 结语
ending
```

提交 `target=S3`, content=`## §3. C-new\n\nbody 3 new`：

```
## §1. A
body 1
## §2. B
body 2
## §3. C-new       ← §3 替换到 ## 结语 之前
body 3 new
## 结语
ending
```

---

## 反模式（避免）

| 反模式 | 后果 |
|---|---|
| 用 `### §1.` (H3) 而不是 `## §1.` (H2) | section 模式找不到节，replace 失败 |
| 用 `## 1. ` 不带 § | 同上 |
| 用 `## §1` 但 title 在下一行（多行 heading） | section 模式找不到 |
| section 提交时 content 没 heading 直接给 body | exit 5 |
| 改 §2 的 `<n>` 编号（如把 §2 改成 §1.5） | section 模式找不到原节，且打破 outline 映射 |
| 节内嵌套 `## ` 子节（如 ##章节内分块用 H2） | 节边界提前结束；用 `### 子节` 避免 |

---

## 与 history snapshot 的关系

snapshot 是**当时提交的内容原样保留**：

- target=full + 1000 字 → snapshot 是这 1000 字
- target=S2 + 200 字 → snapshot 仅这 200 字（仅 §2 部分）

snapshot 不存"差异"，存的是"这次写了什么"。差异由 git history（用户自行 commit）+ INDEX.md 的 diff_summary 字段表达。

---

## AI 起稿时的对齐自查（commit 前）

- [ ] 每节标题用 `## §<n>. <title>` 格式
- [ ] 节编号与 outline 的 §<n> 对得上
- [ ] target=S\<n\> 时 content 第一行包含正确的 heading
- [ ] sections_changed 数组列出实际改动的节 ID（仅供 INDEX 索引；脚本不会反验）
- [ ] 增节（draft 多于 outline）：在 sections_changed 里标新节 ID（如 S5），但要意识到 outline 没定义此节，下次 review 可能会问
- [ ] 减节（draft 少于 outline）：要在 diff_summary 里说明（如"合并 §3 进 §2"）
