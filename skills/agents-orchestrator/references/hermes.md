# Hermes：本机帮助、文档与传输选择

## 文档入口

运行 `command -v hermes`、`hermes --version`，从版本输出定位实际安装目录。当前本机安装目录为 `/home/liyujun/.hermes/hermes-agent`；这是定位线索，升级或迁移后重新确认。

按任务查本机帮助：

```bash
hermes sessions --help
hermes sessions list --help
hermes sessions export --help
hermes chat --help
```

安装目录内的权威说明：

- `website/docs/user-guide/sessions.md`：会话查询与管理。
- `website/docs/reference/cli-commands.md`：CLI 命令。
- `website/docs/user-guide/features/acp.md`：ACP 使用。
- `website/docs/developer-guide/acp-internals.md`：ACP 内部机制。
- 文档不足时，定点检查 `acp_adapter/server.py` 或对应 CLI 源码；不读取配置和凭据。

Hermes 的 CLI/ACP 不等同于 OpenCode HTTP API；不要套用后者的接口或持久 inbox 保证。

## 本地策略与限制

- 普通委派优先 CLI；显式传 `--source cli`，包括每次 resume。本机测试显示存储 source 为 local，可进入 CLI/桌面历史；省略时 oneshot 来源可能被桌面排除。
- 已知会话使用准确 `--resume SESSION_ID`；不要 latest 或静默 create-if-missing。任务读取不授权恢复执行。
- 需要运行中补充输入、结构化进度或取消时才选 ACP。一个任务保持一个控制端，不并发向同一会话写入；更换传输前核对执行状态。
- 保留用户明确指定的模型；不要套用 OpenCode 默认模型。不使用本机已被用户报告不可用的 Strata；不得因此静默换模型。
- 只读历史先按授权来源/项目缩小范围。现有安全助手：`python3 scripts/hermes_read.py last-message --session EXACT_ID`；模型发现用 `models --provider PROVIDER`。助手仅过滤输出，不改变默认模型。
- CLI 的 slash 命令需要交互式处理；不要通过 one-shot 查询冒充命令执行。客户端超时后先核对服务端任务，不能假定任务已取消。
- 新建 viewer 可能成为第二个 writer；不要为看历史另开同会话 CLI。只操作任务自建进程，不重启共享 gateway。

## 已验证边界

2026-10-28，本机 v0.22.5 已验证：CLI 指定 ID 连续两轮、source local 的人工可见性、限定会话历史导出；ACP 同会话运行中接收补充输入、正常断开后恢复、取消后返回 cancelled。

这些测试没有证明精确 steer 边界、崩溃后队列持久性或权限完整拦截。曾有删除测试未触发权限回调，不能把 ACP 当成天然的审批边界。模型列表存在不证明推理可用。

持续目标只在用户明确要求时读取 [hermes-goals.md](hermes-goals.md)。保留其中关于 goal draft 会触发执行、judge 失败和停止条件的说明。
