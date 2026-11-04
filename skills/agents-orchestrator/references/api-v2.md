# OpenCode API：发现入口与安全封装

## 当前版本规范

```bash
opencode --version
opencode api --help
opencode api GET /openapi.json
```

先从规范中查所需 operationId、parameters、requestBody 和响应 schema，再构造请求。升级后以本机规范为准，不在此维护接口清单。

## 常用只读入口

以下命令已于 2026-11-02 在本机 v2.2.5 验证。关键词和 ID 换成任务目标；使用前仍需确认当前规范。

```bash
opencode api session.list --param search=jamovi --param limit=100
opencode api session.message.list --param sessionID=EXACT_ID --param type=user --param order=asc --param limit=3
```

先把会话搜索响应过滤成 ID、标题、目录、父会话和时间。消息内容仅限相关会话；在本地过滤敏感字段后再输出。检查响应 cursor，按需继续分页；返回不足 limit 不是唯一的结束证据。

## 保留的安全封装

脚本从本 skill 目录定位；在目标项目目录运行，使用脚本绝对路径。

- `python3 scripts/providers.py`、`python3 scripts/models.py`：仅输出过滤后的提供商/模型字段。禁止原样打印 provider、integration、config 或 credential 响应。
- `python3 scripts/control.py --help`：查看支持的 create、inspect、send、inbox、messages、wait、interrupt。已知 ID 的只读查询用 `inspect --session EXACT_ID`；`messages`/`inbox` 含任务内容和工具数据，必须限定范围并过滤。

这些脚本负责安全过滤和可复用控制，不是当前 API 的完整替代。参数和分页能力不足时查本机规范；不得绕过权限、自动重试不明确的 prompt 投递或把接收回执当作任务完成。
