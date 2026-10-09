# VS Code Dev Container

仅在用户要求 Dev Container 或相关扩展工作流时读取。本材料保留声明式安装、调试后端、扩展宿主、网络和生命周期验收约束。

### 项目与开发工具分析
- 在选择镜像和 Dev Container 扩展前，先检查仓库中的语言文件、依赖清单、正式入口、测试入口、调试配置和文档工作流，形成“项目能力 -> 编辑器扩展 -> 容器后端依赖”的对应表。
- 只安装能够由项目事实支持的扩展，不根据项目名称猜测。扩展必须服务于至少一项实际工作：语言支持、调试、测试、数据查看、Notebook 或项目使用的文档格式。
- 编辑器扩展写入 `devcontainer.json`，CLI、语言服务器、调试后端和 R/Python 包写入 Dockerfile 或项目依赖安装脚本。不得用手工安装扩展或在运行中临时安装包代替声明式配置。

- 典型映射（作为核查线索，不作为无条件安装清单）：

  | 语言 | VS Code 扩展 | 调试后端（Dockerfile） |
  |------|-------------|---------------------|
  | R | `REditorSupport.r`、`REditorSupport.r-syntax`、`RDebugger.r-debugger` | `vscDebugger`（通过 `install.packages`） |
  | Python | `ms-python.python`、`ms-python.debugpy` | `debugpy`（通过 `pip install`） |
  | C/C++ | `ms-vscode.cpptools` | 内置（扩展自带） |
  | Go | `golang.go` | 内置（扩展自带） |
  | Rust | `rust-lang.rust-analyzer` | 内置（扩展自带） |

  项目经常检查表格数据时可加入 Data Wrangler。最终选择仍须由仓库用途和官方依赖说明确认。

## 声明式配置
必须提供完整的声明式配置，使 VS Code 自动启动 Compose 服务、打开工作区并安装扩展。**禁止**将 Attach Shell 或手动安装扩展作为交付方案。

在项目根目录创建 `.devcontainer/devcontainer.json`：

```json
{
  "name": "<project-name>",
  "dockerComposeFile": "../docker-compose.yml",
  "service": "<compose-service>",
  "workspaceFolder": "<container-workspace-path>",
  "shutdownAction": "none",
  "customizations": {
    "vscode": {
      "settings": {
        "<setting-name>": "<setting-value>"
      },
      "extensions": [
        "<publisher.extension-id>"
      ]
    }
  }
}
```

规则：
- `service` 必须对应 Compose 服务，`workspaceFolder` 必须对应项目卷的容器内路径
- 当 Dev Container 复用的 Compose 服务还承载模型训练、数据生成、后台服务或其他需要跨 VS Code 会话持续运行的任务时，`shutdownAction` 必须设为 `none`；禁止使用 `stopCompose`，否则关闭、重载或断开 VS Code 会停止整个 Compose 项目并中断任务
- 只有 Compose 服务完全由当前编辑器会话独占、确认其中不存在需要持续运行的任务，且用户明确希望关闭编辑器时停止服务时，才可使用 `stopCompose`
- JSON 同一对象中的键必须唯一；新增 VS Code 设置时，必须合并到唯一的 `customizations.vscode.settings` 对象，禁止再次声明 `settings`，否则前面的设置会在解析时被静默覆盖
- 需要在容器内运行的扩展写入 `customizations.vscode.extensions`；纯 UI 扩展（主题、键位、代码片段、语法定义）留在宿主机，作为 Workspace 扩展的硬依赖时可保留声明以明确依赖闭包，但不得强制其在容器扩展宿主中运行。看到 UI 扩展"prefers to run"在本地的提示不属于安装失败
- 新增扩展前检查官方 Marketplace、扩展仓库或 VSIX 中 `extension/package.json` 的 `extensionDependencies`、`extensionPack` 和功能要求，并递归核对依赖；扩展包中的可选成员按项目功能选择
- **扩展下载网络必须按 Dev Container 的实际网络验证**：VS Code Server 可能通过 `--use-host-proxy` 继承宿主机代理。桥接网络中，容器内的 `127.0.0.1` 指向容器自身；若宿主机代理只监听回环地址，扩展清单或 VSIX 下载会出现 `ETIMEDOUT`、`ECONNRESET`，即使扩展已经正确声明也无法自动安装
- Linux 上若必须复用仅监听宿主机回环地址的代理，Compose 开发服务使用 `network_mode: host`，使容器能够访问宿主机的 `127.0.0.1:<proxy-port>`。使用 host 网络后不得再依赖 `ports` 映射；先检查端口冲突及该模式是否符合服务隔离要求。代理监听宿主机可路由地址时，优先使用该地址；非 Linux 环境按平台能力使用 `host.docker.internal`，不要无条件套用 host 网络
- 在唯一的 `customizations.vscode.settings` 中声明扩展下载所需的 VS Code 网络设置。只有确认 Marketplace/CDN 可直连时，才将相应官方域名加入 `http.noProxy`；其他请求可通过无凭据的 `http.proxy` 转发。不得把代理账号、密码或 Token 写入项目配置
- 配置代理后，必须从目标 Compose 服务中分别请求 Marketplace 清单和实际 VSIX 下载地址，并使用与 VS Code Server 相同的直连/代理路径验证。普通网页可访问、版本命令成功或宿主机可下载，都不能证明容器内扩展安装链路可用
- 扩展安装期间不要反复重开窗口或中止容器。安装被中断后，Dev Containers 的安装标记可能使后续连接不立即重试；先检查 Remote Server 日志和容器端扩展注册表。需要重新创建容器验证时，先确认没有不可中断任务并取得删除确认，禁止用手工安装代替自动安装验收
- **debugger 扩展强制要求**：若项目包含可调试源码语言，`customizations.vscode.extensions` 必须包含该语言的 debugger 扩展；若 debugger 扩展需要额外的调试后端包（如 R 的 `vscDebugger`、Python 的 `debugpy`），必须在 Dockerfile 中显式安装。不得以"项目暂时不需要调试"为由省略 debugger 扩展
- **R 执行扩展必须运行在容器内**：`REditorSupport.r` 和 `RDebugger.r-debugger` 需要调用容器内的 R、语言服务器和调试后端，但其清单未定义 `extensionKind`，因此必须在 `customizations.vscode.settings` 中强制为 workspace。`REditorSupport.r-syntax` 只贡献语言与语法定义，应留在 Local Extension Host，不得强制为 workspace：
  ```json
  "remote.extensionKind": {
    "REditorSupport.r": ["workspace"],
    "RDebugger.r-debugger": ["workspace"]
  }
  ```
- 仅在必要时添加 `postCreateCommand`，且只能执行快速、幂等的初始化或验证，不安装大依赖
- 默认不为 Dev Container 添加 Git/SSH 配置。仅当明确需要在容器内执行 Git SSH 远程操作时才安装 `openssh-client`（见本文 Git/SSH 配置），相关禁令与验收见本文 Git/SSH 配置与验证
- **验证**：完成后检查 JSON 语法和重复键，核对 Dev Containers CLI 解析后的 `customizations.vscode.settings` 是否保留全部预期项；执行 `docker compose config --quiet`，确认容器具有 Dev Container 配置标签；连接后获取容器端实际扩展列表，与声明扩展及递归展开的 `extensionDependencies` 逐项比对，并验证关键扩展能够激活，不能以缓存存在或安装命令已启动代替安装成功
- 若设置了 `shutdownAction: none`，验证关闭或断开 VS Code 后 Compose 服务仍为 running；执行该验证前先确认容器内没有不可中断的任务，避免用真实长程任务测试配置

#### Dev Container 的可选 Git/SSH 配置
默认由宿主机或宿主机上的 AI Agent 执行 Git 远程操作，容器不安装 `openssh-client`。仅当用户明确要求在 Dev Container 内执行 `clone`、`fetch`、`pull` 或 `push` 等 SSH 远程操作时，才安装 `openssh-client`，并通过 Dev Containers 转发的宿主机 SSH Agent 认证；不安装 `openssh-server`，也不运行 `sshd`。需要安装时，优先合并到已有系统依赖层；若前面存在高成本依赖层，则放在其后、最终非 root `USER` 之前，避免无关缓存失效：

```dockerfile
RUN apt-get update && \
    apt-get install -y --no-install-recommends openssh-client && \
    rm -rf /var/lib/apt/lists/*
```

启用容器内 Git/SSH 时的安全边界：
- 私钥只保留在宿主机 SSH Agent 中；禁止 `COPY` 私钥、挂载 `~/.ssh`、把私钥写入镜像/卷，或通过环境变量传递私钥
- 禁止为了 Git 拉取/推送而把 `GITHUB_TOKEN`、`GITEE_TOKEN` 等 Token 写入 `devcontainer.json`、Compose、Dockerfile 或容器环境；SSH remote 使用 SSH Agent，HTTPS remote 使用宿主机 credential helper 桥接
- 不硬编码或手动挂载 `SSH_AUTH_SOCK`；Dev Containers 会在 VS Code attach 会话中自动转发。若宿主 Agent 未加载密钥，要求用户在宿主机自行执行 `ssh-add`，不得读取或展示私钥、SSH 配置、账户名或指纹
- 如果 Git 远程操作始终在宿主机完成，不为容器增加 SSH 客户端或认证配置

### Dev Container Git/SSH 验证（仅在启用容器内 Git/SSH 时）
- 宿主机先确认 `ssh-add -l` 表明 Agent 已加载至少一个身份；仅报告成功/失败，不输出路径、账户名或指纹
- 镜像内确认 `command -v ssh` 成功，并确认未安装或启动 `sshd`
- 通过 VS Code attach 后，在 Dev Container 集成终端确认 `SSH_AUTH_SOCK` 指向有效 socket、`ssh-add -l` 能看到转发身份
- 对项目实际 SSH remote 执行非破坏性的认证检查和 `git fetch --dry-run`；不得用提交或推送代替连通性验证
- 确认镜像、Compose、Dev Container 配置和容器环境中没有私钥及 Git 托管平台 Token
