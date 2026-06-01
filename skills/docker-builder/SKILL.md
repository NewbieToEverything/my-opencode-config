---
name: docker-builder
description: Docker镜像构建、模型下载、部署全流程
---

## 必须遵守
- 必须使用 `docker compose`（不是 `docker run`）
- 容器名：必须使用小写字母+短横线
- `image` 参数：所有自定义镜像必须在 `docker-compose.yml` 中显式指定 `image:`
- 健康检查：所有服务必须配置 `healthcheck`
- 若有项目目录，必须显式挂载
- 若有环境变量文件，必须显式挂载

## 第一步：前期工作
### 依赖检查
- Docker 和 Docker Compose 已安装
- NVIDIA Driver 和 nvidia-container-toolkit 已安装
- 磁盘空间充足

### 选择基础镜像
- 分析容器的用途，根据用途选择合适的基础镜像，优先使用官方维护的基础镜像
- 如果需要使用 CUDA，需检查：
  1. 基础镜像的 CUDA 版本与宿主机 NVIDIA Driver 的兼容性
  2. 框架（如 PyTorch、TensorFlow、vLLM 等）版本与 GPU  compute capability（架构代次，如 sm_90/sm_120）的兼容性

### 冲突检测
- 检查备选端口是否被占用
- 检查备选容器名是否已存在
- 若自定义镜像，检查备选镜像名是否已存在
- 检查 GPU 是否被其他容器占用：`nvidia-smi` 查看显存使用

### 下载
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
- 超时直接重试，直到下载完毕。若基础镜像大于 200MB，设定最长等待时间（如 10-15 分钟），超时后继续重试直到下载完成。只有当下载速度稳定低于 50 kb/s 时终止下载，寻找其他解决方案并告知用户。
- 若多次重试仍卡在同一层，放弃该基础镜像，改用纯净的基础镜像（只有基本的 Linux 系统） + pip 安装框架
- 如需使用 GPU，基础镜像下载完毕后需验证 GPU 可透传到容器，若看不到设备，需排查 nvidia-container-toolkit 配置：
  `docker run --rm --gpus all <基础镜像> ls /dev/nvidia*`

#### 代理
Docker 的代理分两层，必须分别处理：
| 阶段 | 走不走代理 | 配置方式 |
|------|-----------|---------|
| `docker pull` 拉取镜像 | 走 daemon 代理 | 配置 `/etc/systemd/system/docker.service.d/proxy.conf` |
| `apt`/`pip`/`curl` 等 build 时网络请求 | 不走 daemon 代理 | `network: host` + build args `HTTP_PROXY`/`HTTPS_PROXY`|

## 第二步：创建 docker-compose.yml 和 dockerfile
### dockerfile
核心原则：
- **RUN 命令合并**：dockerfile 中应合并所有能合并的 RUN 命令（用 `&&` 串联），减少镜像层数，提升构建效率。示例：
```dockerfile
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip install --no-cache-dir --upgrade pip
```
- **先拆依赖层** — 把第三方依赖隔离到中间镜像，主程序出错不用重复编译
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
- pip 源，在 `pip install` 加 `-i` 参数：
  ```
  -i https://pypi.tuna.tsinghua.edu.cn/simple
  ```

#### 用户
1. 检查宿主机用户名
2. 下载完基础镜像后，要确认镜像的默认用户：`docker run --rm <镜像名> id`
  - 若镜像的默认用户 UID 与宿主机一致（`id -u`），直接使用默认用户：`USER <默认用户名>`
  - 若不匹配，在 dockerfile 末尾创建同 UID 的用户：
    ```dockerfile
    RUN groupadd -g <GID> <用户名> && \
        useradd -m -u <UID> -g <GID> -s /bin/bash <用户名>
    USER <用户名>
    ```
3. 需要运行 `apt-get` 的步骤，必须切换至 root 用户，完成后切回第 2 步中确认的镜像用户（`<默认用户>`或者定义的`<用户名>`）
4. 禁止在 `apt-get` 后使用 `chown` 修改默认用户的主目录，除非确认目标组存在


### docker-compose.yml
#### 用户
检查宿主机的用户 `UID/GID：id -u && id -g`，使用 `-u "xxxx:xxxx"` 命令来匹配查询结果

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

### 第三步：构建镜像
- **Cache 策略**：
  - 调整 dockerfile 代码后重新 build 必须使用 `--no-cache`
  - 需要重新 build 来更新镜像的依赖源（apt-get update）时，必须使用 `--no-cache`
  - 因超时等原因重试失败的 build（未修改代码）→ 使用 cache（利用已有层加速构建）
  - 失败不要全部重来，阶段 Dockerfile 改最后几层用缓存即可，不需要 `--no-cache` 全部重来
- 调试构建步骤：`docker compose build --progress=plain`
- 构建命令保留 log：`2>&1 | tee build.log`，失败时方便定位
- 改一个变量，先确认：换源/改版本前先 `curl -v` 确认可达性


## 第四步：VS Code Dev Container 配置
### 方案选择
- 已有容器只需要编辑/查看文件：使用 Attach Shell 模式（优先）
- 需要 VS Code 自动安装扩展、自动打开工作区：使用完整 Dev Container 配置

### Attach Shell 配置
- 在项目根目录创建 `.devcontainer/devcontainer.json`：
  ```json
  {
    "name": "容器名",
    "containerId": "容器名",
    "attachedWorkspaceFolder": "/工作目录"
  }
  ```
- 暴露端口在 `docker-compose.yml` 的 `ports` 中配置，不在 Dev Container 配置中配置

### 扩展安装与持久化
- 扩展安装：Attach Shell 连接后，在 Extensions 面板点击 "Install in Container"
- 扩展存储位置：容器内 `~/.vscode-server/extensions/`
- 持久化方式（二选一）：
  - 在 dockerfile 中安装（需 base image 包含 code-server）
  - 将 `~/.vscode-server/extensions/` 挂载为 volume
- 容器重建后未持久化的扩展会丢失，需重新安装

## 第五步：验证
### 健康检查
- docker compose ps 显示 running
- curl localhost: 端口 /health 返回正常
- 日志无 ERROR

### GPU 验证
如果需要使用 GPU,在容器启动后做如下验证：
- 根据容器用途选择验证命令来确认 GPU 设备存在：
  - 通用容器：`docker exec 容器名 nvidia-smi`
  - 使用了框架的容器：需采用框架特定的命令，如 PyTorch 容器采用 `docker exec 容器名 python3 -c "import torch; print(torch.cuda.is_available())"`
- 若验证失败，检查环境变量 `docker exec 容器名 env | grep NVIDIA`

## 特定用途容器的配置细节
- 容器需要生成含中文的报告（HTML/PNG/PDF）时，读取本 skill 目录下的 `assets/container-data-analysis-chinese-font.md`
- 容器需要编译 R 时，读取本 skill 目录下的 `assets/container-r-package-compilation.md`
