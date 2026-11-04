# pi agent：随包文档与会话操作

## 定位当前版本

```bash
command -v pi
pi --version
pi --help
```

2026-11-02 本机版本为 1.4.0，入口为 `~/.local/bin/pi`，解析后为 `~/.pi/agent/bin/pi`。随包文档位于：

`~/.pi/agent/install/releases/1.4.0/node_modules/@earendil-works/pi-coding-agent/docs/`

升级后重新定位 release 和包目录，不把此版本路径当作固定接口。仅查看程序、包元数据或目录定位，不读取 `auth.json`、`settings.json`、模型配置等隐藏配置或凭据。

## 按任务读取文档

- `cli.md`：当前 CLI；以 `pi --help` 核对安装版本支持的参数。
- `sessions.md`、`session-format.md`：会话目录、恢复、分支和 JSONL 格式。
- `rpc.md`、`rpc-commands.md`：stdio RPC 协议、查询状态、prompt、取消和会话控制。
- `json.md`：JSON 事件流及执行结束的判断。
- `sdk.md`：仅在确实需要进程内 Node.js/Bun 集成时读取。

## 只读历史

不要为读取历史启动模型。先根据已知项目、会话 ID 或用户指定目录定位文件，再按 `session-format.md` 解析相关记录。默认目录是 `~/.pi/agent/sessions/`，但命令行可覆盖目录；单个目录查不到不代表会话不存在。

会话是有分支的记录，原始 JSONL 的最后一行不一定是当前分支最后一条对话。读取所需元数据、用户和助手消息，避免整份输出系统提示、工具数据或敏感内容。导出会生成文件；查询不隐含授权分享、上传或修改历史。

## 已授权的执行

简单批处理查看 `--print` / `--mode json`；需要长期控制时查看 `--mode rpc`。只读查询不需要启动 RPC。恢复时先核实完整会话 ID 与文件路径，再用 `--session`；避免 `--continue`、选择器或模糊 ID 误选。`--session-id` 可创建不存在的会话，不能用来证明会话存在。

RPC 要关联请求 ID，持续读取事件。成功的 prompt response 只表示已接收或处理；按当前文档判断运行状态。1.4.0 文档要求需要最终稳定状态时等待 `agent_settled`，单独 `agent_end` 后仍可能继续重试或处理后续输入。

不要把 CLI 的“read-only”示例当作完整安全边界：扩展和 MCP 也能带来工具。按任务检查相关开关与实际启用能力，不调用认证输出命令，不传明文密钥，不使用信任开关绕过用户权限要求。

## 验证边界

本次只核实了帮助、版本、文档和会话格式入口，没有启动推理、恢复用户会话或做 RPC 执行测试。文档声明的能力不能报告为本机执行已验证。
