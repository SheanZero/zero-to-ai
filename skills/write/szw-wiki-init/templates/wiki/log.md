# Wiki Operation Log

> Append-only 时间序记录。grep-friendly。
>
> 格式：`## [YYYY-MM-DD HH:MM] <op> | <target>` + 多行细节
>
> 操作类型：
> - `ingest` —— resources → wiki 摄入
> - `query` —— wiki 综合查询
> - `lint` —— 健康检查
> - `import` —— vault → szw seed/refresh
> - `merge` —— vault import 冲突合并
> - `feedback` —— essay → wiki 反向沉淀（v2）
> - `init` —— wiki 层初始化或聚合

---

## [<INIT_TIMESTAMP>] init | wiki layer initialized

- bootstrap mode: <空骨架 | seed-from-vault | skip>
- wiki/ created with 7 category subdirs
- INDEX.md / CONVENTIONS.md / WORKFLOWS.md generated

---
