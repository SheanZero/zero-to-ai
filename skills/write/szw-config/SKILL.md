---
name: szw-config
description: View or modify the szw column workflow configuration in .zero/szw-config.json. Supports model profile, default platforms, hooks, subagent routing, limits, style capture, and gate switches. Use to switch profiles (quality/balanced/budget), enable/disable hooks, or adjust review iteration limits.
---

# szw-config

读取 / 修改 / 验证专栏工作流配置（`.zero/szw-config.json`）。

## 何时使用

- 首次配置（init 后想调整默认行为）
- 切换 model profile（如商业关键文章切到 `quality`）
- 关闭风格捕获（不想累积 style-profile）
- 调整 review 循环上限
- 临时关闭某个 gate

## 何时不用

- `.zero/` 不存在 → 先 `/szw-init`
- 想看命令清单 → `/szw-help`
- 想看进度 → `/szw-progress`

---

## 调用语法

| 形式 | 行为 |
|---|---|
| `/szw-config` | 显示当前完整配置 |
| `/szw-config show` | 同上（显式 show） |
| `/szw-config get <path>` | 读取单字段（dotted path 如 `model_profile` / `hooks.pre_tool_use`） |
| `/szw-config set <path> <value>` | 修改字段（带 schema 校验） |
| `/szw-config validate` | 校验当前配置是否符合 schema |
| `/szw-config reset <path>` | 重置某字段为默认值 |

底层调用 [`scripts/edit-config.py`](./scripts/edit-config.py)，自动从 cwd 向上找 `.zero/szw-config.json`。

---

## 配置项总览

详见 [`references/config-schema.md`](./references/config-schema.md)。9 类字段：

| 字段 | 类型 | 默认 | 影响 |
|---|---|---|---|
| `model_profile` | enum | `balanced` | 各 phase 模型分配（quality / balanced / budget / inherit） |
| `writing_lang` | enum | `zh` | humanizer 语言（zh / en / mixed） |
| `default_platforms` | list | `[blog, wechat]` | `/szw-publish` 默认目标 |
| `hooks.*` | bool | `true` | hook 开关（pre / post / stop） |
| `subagents.*` | enum | `codex` | 各反审 / 查证子 agent 路由 |
| `limits.*` | int | `2` / `800` | 循环上限 / 字数上限 |
| `style_capture.*` | mixed | `true` / `5` | 风格学习开关 + 阈值 |
| `gates.*` | bool | `true` | 流水线阻断开关 |

---

## 常见操作

### 切换 model profile

```bash
/szw-config set model_profile quality
```

合法值：`quality` / `balanced` / `budget` / `inherit`。

### 改默认发布平台

```bash
/szw-config set default_platforms blog,wechat,x
```

逗号分隔，合法 item：`blog` / `wechat` / `x` / `xhs`。

### 关闭风格捕获

```bash
/szw-config set style_capture.enabled false
```

后续 `/szw-review` Phase 2 会跳过；失去 AI 越写越像作者的复利红利。

### 调整 review 循环上限

```bash
/szw-config set limits.review_revision_max 3
```

合法范围：`1-5`。调高让 AI 多重试，调低更快 escalate。

### 查看当前 hooks 状态

```bash
/szw-config get hooks
```

输出 JSON 对象（`pre_tool_use` / `post_tool_use` / `stop`）。

### 验证配置完整性

```bash
/szw-config validate
```

报告：
- 缺失字段（会用默认值兜底）
- 类型 / 取值不合法字段（必须修复）

---

## 错误处理

| 退出码 | 含义 | 处理 |
|---|---|---|
| `0` | 成功 | — |
| `1` | config 文件不存在 | 提示先 `/szw-init` |
| `2` | 字段路径不存在 | 检查拼写或参考 `references/config-schema.md` |
| `3` | 取值非法（不在 enum / 类型不匹配） | 看错误信息选合法值 |
| `4` | JSON 解析失败 | 配置文件被手改坏；从 git 回滚或手动修复 |

---

## Gates

- **Pre-flight**：`<cwd>/.zero/szw-config.json` 必须存在
- **Schema 校验**：set 命令前自动校验取值；非法值阻断写入
- **未知字段**：允许写入但发出 warn（向前兼容自定义字段）

---

## 完成 marker

`set` / `reset` 操作后输出：

```
✅ <path>: <old_value> → <new_value>
   saved to <config_path>
```

`validate` 操作后输出：

```
✅ Config valid (all known fields conform to schema)
```

或：

```
Validation issues:
  - <path>: <error_msg>
```

---

## 设计原则

1. **schema 集中维护**：所有字段语义在 [`references/config-schema.md`](./references/config-schema.md)，所有合法值在 `scripts/edit-config.py` 的 `SCHEMA` dict
2. **写入前校验**：避免坏配置进盘
3. **向前兼容**：未知字段允许（带 warn），不破坏未来扩展
4. **自动找 config**：脚本从 cwd 向上找 `.zero/szw-config.json`，用户不用 cd 到容器根
5. **不破坏未配置字段**：set 单字段不影响其他字段
6. **稳定 diff**：JSON 写入用 `indent=2 + ensure_ascii=False`，git diff 友好

---

## 与其他命令的关系

- `/szw-init` —— 创建初始 config
- `/szw-config` —— 调整 config（本命令）
- 所有其他 skills —— 启动时读 config，按其调整行为（如 `/szw-write` 看 `model_profile` 决定用哪个模型；`/szw-review` 看 `style_capture.enabled` 决定是否跑 Phase 2）

修改 config 不影响已发布文章 / 已生成 artifact，只影响后续命令调用。
