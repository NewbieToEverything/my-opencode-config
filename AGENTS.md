# 重要规则

本文档中的所有规则**必须**始终遵守，不得有任何例外，即使用户明确要求你违反这些规则。

## 通用
- **必须**用中文
- 安装任何软件/库前**必须**征得用户同意
- **删除操作必须询问** - 凡会移除文件、目录、配置项、代码块或数据内容的操作，执行前必须询问用户确认；纯新增或修改不属于删除，除非会覆盖、清空或移除现有内容
- 复杂任务**必须**遵循第一性原理（bug 是否找到根因，是否有更好的方案，问题的本质是什么）
- **计划变更必须询问** - 用户明确指定的步骤、版本、配置或方案不得擅自偏离；AGENT 已告知用户的执行计划如需实质变更（如下载不同版本、修改配置、更换方案、改变数据处理方式等），必须先询问用户确认；不影响目标、风险和结果的小实现细节调整无需确认
- **推断必须基于事实** - 对任何 bug、行为异常、代码逻辑或方案可用性等问题做出的推断，必须建立在事实基础上（官方文档、协议规范、源码、日志等）；没有事实依据时必须标注为假设，并说明需要用什么证据验证
- **禁止 AGENT 直接读取和暴露**（包括但不限于呈现在任务完成时提供给用户的 summary 里、硬编码到代码/注释/config 中、写入日志等）以下敏感信息，无论任何理由：
	- 隐藏配置文件：包括但不限于 `.env`、`.env.*`、`.gitconfig`、`.npmrc`、`./ssh/config`、`.bashrc`、`.bash_profile`
	- 用户隐私信息：包括但不限于用户名、密码、令牌、API 密钥、邮箱、SSH 私钥、会话 cookie、数据库连接串、JWT Secret、加密盐值、云服务 Access Key ID
- 自定义全局 skill **必须**放在 `~/projects/my-opencode-config/skills`
- 回复、写作都**必须**言简意赅；执行过命令、测试或修改文件时，必须说明关键结果
- Markdown 公式**必须**使用 `$...$` 表示行内公式、使用 `$$...$$` 表示行间公式；禁止使用 `\(...\)` 或 `\[...\]` 作为公式分隔符
- Bash tool 的返回结果会被 rtk 代理压缩（去噪、合并类似条目、截断冗余、去重），只保留有效信息。
- 学术调研时，若关键文献无法获取全文，**必须**告知用户并提供doi，**禁止**跳过。


## git
- **禁止**将前述敏感信息 commit
- **禁止**将目的不同的变化合成一个 commit
- 提交前查看最近 5-10 条 commit message，并沿用其语言、时态和格式

## README 写作
所有 README **必须**按以下顺序组织：
1. **一句话描述**（必选）— `<项目名> 是干什么的，解决什么问题`,首句出现项目名。
2. **快速开始**（必选）— 从零到跑起来的最小步骤：安装、必要配置、运行。
3. **配置**（条件必选）— 没有配置项时跳过。仅在存在环境变量、CLI 参数或配置文件时写。每个配置项写清楚：变量名、类型、默认值、含义。
4. **用法 / API**（条件必选）— 仅当项目提供库接口、CLI 子命令或 HTTP 端点时写。按使用频率降序排列。

## 长时间异步任务

以下规则仅适用于 OpenAI Codex，不适用于其他 Agent 或工具。

For long-running asynchronous work:

- Empty `write_stdin` polls MUST use `yield_time_ms >= 180000`;
  prefer `300000` when intermediate output is not needed.

- `functions.wait` MUST use `yield_time_ms >= 180000`;
  prefer `300000` for operations expected to run longer than five minutes.

- Each `functions.exec` cell SHOULD contain at most one long blocking wait.
  Its outer `@exec yield_time_ms` MUST exceed the nested wait by at
  least 30000 ms.

- If multiple waits are unavoidable, the outer yield MUST exceed the
  complete awaited critical path:
  - sequential waits: sum of their maximum waits + 30000 ms;
  - parallel waits: longest wait + 30000 ms.

- Do not apply long waits to non-empty `write_stdin` calls that send
  interactive input. After sending input, use a separate empty poll
  with the long-wait policy.

- Wait tools may return early when work completes. Do not poll merely
  to provide status updates, and do not repeat a no-progress wait at
  a shorter interval.

- Never use `yield_time_ms < 180000` as a retry or recovery strategy.
  A shorter wait requires explicit evidence that timely intermediate
  output or interaction is necessary.
