# OpenCode：本机规范与本地约束

## 文档入口

先运行 `command -v opencode`、`opencode --version` 和 `opencode api --help`。接口与参数以 `opencode api GET /openapi.json` 为准；只提取本次操作需要的路径和 schema，不保存整份副本到 skill。

会话操作和安全封装入口见 [api-v2.md](api-v2.md)。安装版本改变后重新确认所需接口，避免照搬旧版 CLI 参数。

## 本地执行策略

默认委派模型为 `opencode/deepseek-v4.1-flash-free`，variant 为 `max`；用户明确选择优先。先用 `scripts/providers.py` 和 `scripts/models.py` 的过滤输出确认模型存在且支持档位；不匹配时报告，不静默替换。只读查询无需发现模型或启动推理。

不要使用 `--auto`。Codex 负责验收，OpenCode 负责授权范围内的执行；未被要求接管时，返工交给原会话。

## 本机行为与限制

- CLI 的只读 API 也可能先连接后台服务。沙箱内 `service.ensure` 失败不能证明会话不存在或服务损坏。用有限诊断确认失败阶段，必要时按平台权限机制重试同一只读请求；不得重启服务绕过。
- `scripts/control.py messages` 只返回默认页；完整历史应按当前 API 的 cursor 分页。
- API 的 idle/succeeded 不代替模型错误检查和产物验收。SSE 只作补充，重连后核对持久状态。
- 2026-10-28 测试验证了同一会话续接、补充输入和产物；未证明精确 steer 边界、崩溃恢复或去重保证。读取帮助不扩大验证范围。
- 如需看 TUI，创建独立 viewer，不接管用户终端。单纯查历史用 API；无需创建 viewer。记录自建进程，不擅自关闭用户进程。

## Authorized free-quota recovery

The user explicitly authorizes this bounded fallback when the OpenCode free-model quota is exhausted. Do not trigger on generic network/authentication errors or merely slow output.

1. Establish quota exhaustion from the owned session's error, messages or actual TUI. Record the current session ID, project location, model/variant, outstanding input and partial artifacts.
2. Run `opencode-proxy status`. Toggle the reported state once: `on` becomes `off`, `off` becomes `on`. If state is ambiguous, stop instead of guessing. Do not print proxy addresses, environment values or credentials.
3. The helper's installed help states that on/off restarts the shared OpenCode background service. This can interrupt other sessions: inspect active work through the safe session interface first. If unrelated sessions are running, pause this recovery and obtain approval for interrupting them; do not restart their work silently. Do not substitute manually editing environment/configuration.
4. Reconnect after restart. Fetch the exact saved session; verify model and reasoning variant. Inspect pending/delivered inputs and partial results before resuming. Do not blindly duplicate the previous task. Continue the same session and check whether quota is still exhausted.
5. If free quota is exhausted again after the single toggle, switch that session to provider `deepseek`, model `deepseek-flash` (currently displayed as **DeepSeek V4.1 Flash 1017**), variant `max` if advertised. This potentially paid provider switch is explicitly authorized by this user policy. Requery enabled models first; if the ID or advertised identity no longer matches V4.1 Flash, stop for clarification rather than selecting another DeepSeek model.
6. Confirm `session.get` shows the intended model/variant, then continue the outstanding task in the same session. If this provider also fails or lacks quota, report the blocker; no further proxy toggles or model substitutions in this recovery chain.

Apply at most one toggle and one DeepSeek fallback per quota-recovery chain. Record the original/final state and model; do not restore proxy state automatically after completion, since that would restart the shared service again. Never claim quota or inference has recovered solely because a status/model-switch command succeeded.

Verified discovery on 2026-10-28: `opencode-proxy` supports `on|off|status`; both switching commands restart the shared backend. `deepseek/deepseek-flash` is enabled and named DeepSeek V4.1 Flash 1017. No proxy switch or paid inference was performed while documenting this policy.
