---
name: docker-builder
description: Docker 镜像构建、模型下载、Dev Container 扩展分析与安装、部署全流程
---

> 实测环境：Linux / Docker + nvidia-container-toolkit / RTX 5070 Ti 16GB（sm_120）。文中带具体速率、架构映射、显存占用的结论以此环境为准，跨机器需重新实测。

## 必填字段（写 compose 时逐条核对）
- 最终部署必须使用 `docker compose`；调试/验证阶段可临时用 `docker run`
- `container_name`：必须使用小写字母+短横线
- `image`：所有自定义镜像必须在 `docker-compose.yml` 中显式指定镜像名
- `healthcheck`：所有服务必须配置生命周期健康检查（不限 HTTP 端点）。**`start_period` 必须覆盖下载模型、编译、格式转换、首次建索引等全部初始化耗时**——这些都发生在监听端口之前。估不准就往大给（数小时）：`restart` 只在容器退出时动作、不看 unhealthy，误判只产生假告警、不会中断任务。
- `restart`：所有服务必须配置（除非有明确理由不需要）
- `volume`：若有以下内容，必须显示挂载
  - 项目目录
  - 环境变量文件

## 第一步：前期工作
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

### 依赖检查
- 确认 Docker 和 Docker Compose 已安装
- 磁盘空间充足
- 如果容器需要使用显卡，需确认 NVIDIA Driver 和 nvidia-container-toolkit 已安装

### 选择基础镜像
- 分析容器的用途
- 根据用途查询本地已有镜像（`references/created-images-containers.local.md`，本机实况；文件不存在时读同目录的 `.md` 模板），若已有满足用途的镜像直接复用；否则搜索远程基础镜像（官方维护的优先）
- 如果需要使用 CUDA，需检查：
  1. 基础镜像的 CUDA 版本与宿主机 NVIDIA Driver 的兼容性
  2. 框架（如 PyTorch、TensorFlow、vLLM 等）版本与宿主机 GPU compute capability（架构代次，如 sm_90/sm_120）的兼容性

### 冲突检测
- 检查备选端口是否被占用
- 检查备选 `container_name` 是否已存在
- 若自定义镜像，检查备选 `image` 是否已存在
- 检查 GPU 是否被其他容器占用

### 下载
#### 代理
Docker 的代理分两层：
| 阶段 | 走不走代理 | 配置方式 |
|------|-----------|---------|
| `docker pull` 拉取镜像 | 走 daemon 代理 | 配置 `/etc/systemd/system/docker.service.d/proxy.conf` |
| `apt`/`pip`/`curl` 等 build 时网络请求 | 不走 daemon 代理 | `network: host` + build args `HTTP_PROXY`/`HTTPS_PROXY`|

- 国内镜像与代理解决的问题不同：CRAN、PyPI、APT 国内镜像只加速各自仓库；R-universe、GitHub Release、rustup 等非镜像来源仍应在需要时走代理。
- 使用 `build.network: host` 时，Linux 构建阶段可通过 `127.0.0.1:<宿主机代理端口>` 访问宿主机代理；未使用 host 网络时才考虑 `host.docker.internal`，并在 Linux 上显式映射 `host-gateway`。
- 代理只能在单次构建命令中通过 `--build-arg HTTP_PROXY=... --build-arg HTTPS_PROXY=...`（必要时同时传入小写变量）临时注入。禁止把代理写入 Dockerfile `ENV`、镜像层或项目的持久配置（build 阶段的验证方式见第三步）
- 正式构建前，使用与构建阶段相同的网络模式和基础镜像，通过代理访问实际失败的下载地址；确认目标源返回成功状态后再重建，不能只测试普通网站。

#### docker 国内镜像源
- **Docker镜像源配置**：使用 `docker pull` 下载基础镜像前，需先配置国内 docker 镜像源。在 `/etc/docker/daemon.json` 中配置多个镜像源以提升可移植性和稳定性：
  ```json
  {
    "registry-mirrors": [
      "https://docker.m.daocloud.io/",
      "https://docker.1ms.run/",
      "https://docker.xuanyuan.me/",
      "https://docker.1panel.live/",
      "https://ghcr.dockerproxy.com/"
    ]
  }
  ```
  配置后执行 `sudo systemctl daemon-reload && sudo systemctl restart docker` 使其生效。
  **注意**：改 daemon 配置会重启 dockerd，中断所有容器；必须先确认所有容器都配了 `restart` 策略（`docker inspect -f '{{.HostConfig.RestartPolicy.Name}}' <容器>`），并先取得用户同意再执行。
- **`registry-mirrors` 的适用边界**：它只拦截**manifest**（清单）请求。镜像源未命中、或 blob 回源时，实际下载仍会走上游 registry——而上游流量是走 daemon 代理的。所以"配了镜像源"不等于"大文件从镜像源下载"。判断实际走哪条路，看 `docker pull` 日志里各层状态与整体速率；大层迟迟不动时，直接显式拉镜像源的完整仓库名（`<mirror>/<repo>:<tag>`）再 `docker tag` 回原名，绕开回落逻辑。
- **显式从镜像源拉取时不能用裸 `curl` 探测可用性**：国内镜像源大多要求鉴权流程，`curl` 直连常返回 401/403，看起来像"镜像不可用"，而 `docker pull <mirror>/<repo>:<tag>` 实际是通的。要判断镜像源是否可用，用 `docker pull` 拉一个小镜像验证。
- 超时后最多重试 3 次，每次间隔 5 秒。
- 若多次重试仍卡在同一层，按下方「下载速率诊断」确认瓶颈；若确认不是按连接限速且重试无改善，才放弃该基础镜像，改用纯净的基础镜像（只有基本的 Linux 系统） + pip 安装框架
- 如需使用 GPU，基础镜像下载完毕后需临时用 `docker run --rm --gpus all <基础镜像> ls /dev/nvidia*` 验证 GPU 可透传到容器

#### 下载速率诊断（按需）

下载卡住、或速率稳定低于 50 kb/s 时，先读 `references/download-speed-diagnosis.md`（如何区分"按连接限速"与"总带宽上限"、并发改造、预先放好文件、断点续传），再决定换源或放弃镜像。**核心：绝大多数"下载慢"是上游按连接限速，换镜像源和改 daemon 代理都无效，只有加并发有效。**

别重新发明轮子，本 skill 已备好工具：

| 场景 | 用 |
|------|-----|
| 不确定是不是按连接限速 | `scripts/net-probe.sh <url> [start-end]` 直接给判据 |
| 拉单个/多个大文件（HF 权重、模型分片、任意 URL） | `scripts/parallel-fetch.py <清单.json> --out <目录> --workers 8` |
| 拉 Docker 镜像并 `docker load` 导入 | `scripts/pull-docker-image.py <镜像:标签> --work <数据盘目录> --load` |
| 已有现成下载器但只有单连接 | 按 `references/download-speed-diagnosis.md` 的「预先放好文件」或「用过滤参数拆并行」改造 |

## 第二步：创建 docker-compose.yml 和 dockerfile
### dockerfile
核心原则：
- **RUN 命令合并**：dockerfile 最终层的 RUN 命令应尽量用 `&&` 串联，减少镜像层数。示例：
```dockerfile
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip install --no-cache-dir --upgrade pip
```
- **先拆依赖层** — 开发调试阶段把第三方依赖隔离到独立 RUN，避免频繁变动的主程序导致依赖层缓存失效
- **先预拉基础镜像** — `docker pull base-image` 提前下载，避免 build 中拉取被代理/限速干扰

#### apt/pip 国内源
自建镜像需在 dockerfile 里为所有的安装服务配置国内镜像源：
- 在 `apt-get update` 之前完成 apt 源全部替换（含 security）：
  ```dockerfile
  RUN sed -i 's|http://archive.ubuntu.com/ubuntu|http://mirrors.tuna.tsinghua.edu.cn/ubuntu|g' \
             /etc/apt/sources.list && \
      sed -i 's|http://security.ubuntu.com/ubuntu|http://mirrors.tuna.tsinghua.edu.cn/ubuntu|g' \
             /etc/apt/sources.list && \
      apt-get update && apt-get install -y <package>
  ```
- `apt-get install` 前必须加 `apt-get update`
- pip 源，在 `pip install` 加 `-i` 参数：
  ```dockerfile
  RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --no-cache-dir <package>
  ```

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

#### 用户
1. 检查宿主机用户名
2. 下载完基础镜像后，临时用 `docker run --rm <镜像名> id` 确认默认用户
  - 若镜像的默认用户 UID 与宿主机一致（`id -u`），直接使用默认用户：`USER <默认用户名>`
  - 若不匹配，在 dockerfile 末尾创建同 UID 的用户：
    ```dockerfile
    RUN groupadd -g <GID> <用户名> && \
        useradd -m -u <UID> -g <GID> -s /bin/bash <用户名>
    USER <用户名>
    ```
3. 需要运行 `apt-get` 的步骤，必须切换至 root 用户，完成后切回第 2 步中确认的镜像用户（`<默认用户>`或者定义的`<用户名>`）
4. 禁止在 `apt-get` 之后用 `chown` 修改**镜像默认用户的主目录**（除非已确认目标组存在）；上游镜像的应用目录需要交给宿主用户时，走 compose 一节的派生镜像方案

### docker-compose.yml
#### 用户
检查宿主机的用户 `UID/GID：id -u && id -g`，使用 `-u "xxxx:xxxx"` 命令来匹配查询结果

**`-u` 与上游镜像冲突时的化解办法**：很多第三方镜像的安装器/服务在启动时要写自己的应用目录（装 Python 包、建软链、写配置）。上游镜像该目录属 root 且未设 `USER`，此时直接加 `-u` 会让容器起不来。**不要放弃 `-u` 规则，也不要退回 root 满盘写**——加一层派生镜像把目录交给宿主用户，再在 compose 里用 `-u`：

```dockerfile
# Dockerfile.local（放在上游仓库内，构建上下文即该仓库）
ARG HOST_UID=1000
ARG HOST_GID=1001
FROM <上游镜像>
ARG HOST_UID
ARG HOST_GID
RUN chown -R ${HOST_UID}:${HOST_GID} <应用目录>   # 该目录要可写，是上游安装器的要求
USER ${HOST_UID}:${HOST_GID}
```
```bash
docker build -t <名字>:latest -f Dockerfile.local \
  --build-arg HOST_UID=$(id -u) --build-arg HOST_GID=$(id -g) .
```
落地后必须验证：`docker run --rm <名字>:latest id` 与 `docker run --rm <名字>:latest ls -ld <应用目录>`，确认用户与属主都已切换。这样 bind mount 里产生的文件归宿主用户所有，日后删除/移动无需 sudo。

#### 内存上限的陷阱
若应用**自己**从 `/proc/meminfo` 或类似接口探测可用内存来决定缓存/预加载大小（容器里读到的是宿主机总量，不是容器限额），那么**不要给该服务设 `mem_limit` / `deploy.resources.limits`**——设了上限并不会真的限制它，只会让它的探测逻辑失真（以为有 125 GB 而实际被限在 8 GB）。需要限制时，改用应用自己的开关（如 `LOW_RAM=on`）。

#### GPU 配置
- 所有需要使用 GPU 的容器，必须在 docker-compose.yml 中添加以下配置：
  ```yaml
  services:
    服务名:
      deploy:
        resources:
          reservations:
            devices:
              - driver: nvidia
                count: all
                capabilities: [gpu]
  environment:
    - NVIDIA_VISIBLE_DEVICES=all
    - NVIDIA_DRIVER_CAPABILITIES=compute,utility
  ```

#### compose 骨架
新写或审查 compose 时，以 `assets/docker-compose-template.yaml` 为起点——它把「必填字段」逐条内联成了注释，不适用的行直接删掉，不要留空占位符。

### 第三步：构建镜像
- **Cache 策略**：
  - Dockerfile 或依赖清单已修改：正常构建，Docker 会从变更层开始自动失效缓存
  - 远程输入已变化但构建文件未变、缓存疑似异常或需要全量验证：使用 `--no-cache`；基础镜像标签可能变化时同时使用 `--pull`
  - 下载量超过 500 MB 或清洁构建超过 5 分钟的依赖单独成层，并按清单变更频率从低到高排列
  - 独立的高成本依赖栈使用独立阶段、预构建基础镜像或 BuildKit cache mount，避免一个依赖栈变化导致其他依赖重新下载
  - 重建高成本层前估算时间和磁盘增量并告知用户；不得因耗时擅自更换依赖或运行模式
- 调试构建步骤：`docker compose build --progress=plain`
- **不要给构建输出加会缓冲的管道**：`| tail -N`、`| grep <pattern>` 在构建跑完前不输出任何内容，看起来像卡死。要看实时进度就用 `--progress=plain` 配 `tee`（`tee` 本身不缓冲）。
- 长时间构建使用可持续读取退出状态的前台会话；日志停止刷新或达到显示上限，不等于构建失败
- 代理只作为临时 build args 传入，不写入镜像 `ENV` 或项目配置。构建后检查容器运行环境无代理残留：`docker exec <容器> env | grep -i proxy`
- 先诊断再换源 — 安装失败时先 `curl -v` 确认目标源是否可达，不要直接切换源或改版本号

#### 临时产物落盘位置
- **绝不写进 compose 所在仓库**：使用含 `COPY . .` 的第三方 Dockerfile 时，构建上下文就是那个仓库根目录，里面的任何文件都会被复制进镜像。build 日志、临时产物一律走 `/tmp` 或用户 cache 目录。
- **`/tmp` 可能是 tmpfs（占内存）**：几百 GB 的镜像 tar、解压出的层会吃光内存并触发 OOM。写到用户 cache 目录或数据盘，用完清理。
- build 日志：`2>&1 | tee /tmp/build.log`。
- **CUDA 架构要按需窄化**：官方基础镜像常把多个架构编进同一个 fat binary。只服务一台机器时，用 `--build-arg CUDA_ARCHITECTURES=<本机架构>` 只编一个（RTX 50 系=120、RTX 40 系=89、RTX 30 系=86、A 系=80），编译时间和镜像体积都显著下降；架构不在默认列表内的卡必须自己指定，否则构建出的引擎在该卡上无法运行。
- **构建上下文的传染性**：使用第三方 Dockerfile（含 `COPY . .`）时，构建上下文必须是那个仓库根目录——compose 文件要放进该仓库内。日志落盘位置见上方「临时产物落盘位置」。
- **导入本地镜像的格式**：存储驱动为 `overlay2`（即未启用 containerd 镜像存储）时，`docker load` 只认 **docker-archive** 格式（`manifest.json` + `<config>.json` + 各 `<id>/layer.tar`），传入 OCI layout（`oci-layout` + `index.json` + `blobs/sha256/*`）会报 `blobs/json: no such file or directory` 之类的错。转换要点：各层 blob 是 gzip，**必须解压成未压缩 `layer.tar`**；解压后按镜像 config 里的 `rootfs.diff_ids` 逐层校验 sha256，任一不符即中止。这样转换是内容寻址的，装不出与上游不一致的镜像。
- **`/tmp` 可能是 tmpfs（占内存）**：大体积中间产物（导入用的镜像 tar、解压出的层）不要写进 `/tmp`，几百 GB 会吃光内存并触发 OOM；写到用户 cache 目录或数据盘，用完及时清理。

## 第四步：VS Code Dev Container 配置
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
- 默认不为 Dev Container 添加 Git/SSH 配置。仅当明确需要在容器内执行 Git SSH 远程操作时才安装 `openssh-client`（见第二步），相关禁令与验收见第二步和第五步
- **验证**：完成后检查 JSON 语法和重复键，核对 Dev Containers CLI 解析后的 `customizations.vscode.settings` 是否保留全部预期项；执行 `docker compose config --quiet`，确认容器具有 Dev Container 配置标签；连接后获取容器端实际扩展列表，与声明扩展及递归展开的 `extensionDependencies` 逐项比对，并验证关键扩展能够激活，不能以缓存存在或安装命令已启动代替安装成功
- 若设置了 `shutdownAction: none`，验证关闭或断开 VS Code 后 Compose 服务仍为 running；执行该验证前先确认容器内没有不可中断的任务，避免用真实长程任务测试配置

## 第五步：验证与更新记录
### 构建验证
- `docker compose ps` 显示 running
- 日志中无 ERROR
- 验证必须覆盖项目的真实最小工作流，而不只是执行版本命令
- 按项目实际能力验证：容器健康、扩展后端或语言服务可加载、代表性输入能生成预期输出、硬件加速可被框架使用

### Dev Container Git/SSH 验证（仅在启用容器内 Git/SSH 时）
- 宿主机先确认 `ssh-add -l` 表明 Agent 已加载至少一个身份；仅报告成功/失败，不输出路径、账户名或指纹
- 镜像内确认 `command -v ssh` 成功，并确认未安装或启动 `sshd`
- 通过 VS Code attach 后，在 Dev Container 集成终端确认 `SSH_AUTH_SOCK` 指向有效 socket、`ssh-add -l` 能看到转发身份
- 对项目实际 SSH remote 执行非破坏性的认证检查和 `git fetch --dry-run`；不得用提交或推送代替连通性验证
- 确认镜像、Compose、Dev Container 配置和容器环境中没有私钥及 Git 托管平台 Token

### GPU 验证
如果需要使用 GPU,在容器启动后做如下验证：
- 根据容器用途选择验证命令来确认 GPU 设备存在：
  - 通用容器：`docker exec 容器名 nvidia-smi`
  - 使用了框架的容器：需采用框架特定的命令，如 PyTorch 容器采用 `docker exec 容器名 python3 -c "import torch; print(torch.cuda.is_available())"`
- 若验证失败，检查环境变量 `docker exec 容器名 env | grep NVIDIA`

### 更新镜像记录
若容器配置完毕，把它记进 `references/created-images-containers.local.md`（本机实况，gitignored；文件不存在时按同目录模板创建）。重点写**当初踩过的坑**——不写这一项的记录，下次改造还得重踩一遍

## 特定用途容器的配置细节
根据需要读取本 skill 目录下的相应文件

**scripts/**（可直接执行）
- `net-probe.sh` — 网络吞吐探针，判定按连接限速 vs 总带宽上限
- `parallel-fetch.py` — 并行分块下载器（JSON 清单驱动，断点续传，sha256 校验）
- `pull-docker-image.py` — 分块拉 Docker 镜像并装配成 docker-archive 后 `docker load`

**references/**（按需读入上下文）
- `download-speed-diagnosis.md` — 下载卡住时的完整诊断流程
- `created-images-containers.md` — 镜像与容器清单的**模板**；本机实况写在同目录的 `.local.md`（已 gitignore），文件不存在时读模板
- `container-data-analysis-chinese-font.md` — 容器内生成中文报告（HTML/PNG/PDF）的字体配置
- `container-r-package-compilation.md` — 容器内安装 R 包的编译依赖

**assets/**（用于输出的模板）
- `docker-compose-template.yaml` — compose 骨架，逐条标注必填字段
