---
name: docker-builder
description: Docker镜像构建、模型下载、部署全流程
---

## 必须遵守

- 必须使用 `docker compose`（不是 `docker run`）
- 用户匹配：容器的 `UID/GID` 必须与宿主机一致
- 容器名：必须使用小写字母+短横线
- 健康检查：所有服务必须配置 `healthcheck`
- 若有项目目录，必须显式挂载
- 若有环境变量文件，必须显式挂载

## 第一步：前期工作

### 依赖检查
- Docker 和 Docker Compose 已安装
- NVIDIA Driver 和 nvidia-container-toolkit 正常
- 磁盘空间充足

### 选择基础镜像
- 分析容器的用途
- 根据用途选择合适的基础镜像，优先使用官方（例如微软、GitHub、NVIDIA、Docker等）维护的基础镜像
- 如果需要使用 CUDA，需检查备选基础镜像的 CUDA 版本与当前宿主机的 NVIDIA Driver 兼容性

### 冲突检测
- 检查备选端口是否被占用
- 检查备选容器名是否已存在

### 下载
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

## 第二步：创建容器

### apt/pip 国内源

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

### 用户

#### dockerfile
- 确认基础镜像的默认用户：`docker run --rm <镜像名> id`
- 需要运行 `apt-get` 的步骤，必须切换 root：
  1. `USER root`
  2. 运行 `apt-get update && apt-get install ...`
  3. 完成后切回基础镜像的默认用户：`USER <查到的用户名>`
- 禁止在 `apt-get` 后使用 `chown` 修改默认用户的主目录，除非确认目标组存在

#### docker-compose.yml
- 检查宿主机的用户 `UID/GID：id -u && id -g`，使用 `-u "xxxx:xxxx"` 命令来匹配查询结果

### 构建命令

- **Cache 策略**：
  - 调整 dockerfile 代码后重新 build 必须使用 `--no-cache`
  - 需要重新 build 来更新镜像的依赖源（apt-get update）时，必须使用 `--no-cache`
  - 因超时等原因重试失败的 build（未修改代码）→ 使用 cache（利用已有层加速构建）
- 调试构建步骤：`docker compose build --progress=plain`

- **RUN命令合并原则**：dockerfile 中应合并所有能合并的 RUN 命令（用 `&&` 串联），减少镜像层数，提升构建效率。
  示例：
  ```dockerfile
  RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
      pip install --no-cache-dir --upgrade pip
  ```

## 第三步：VS Code Dev Container 配置

### 方案选择
- 已有容器只需要编辑/查看文件：使用 Attach Shell 模式
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
- 使用方式：`Ctrl+Shift+P` → `Dev Containers: Attach to Running Container...` → 选择容器
- 暴露端口在 `docker-compose.yml` 的 `ports` 中配置，不在 Dev Container 配置中配置

### 扩展安装与持久化
- 扩展安装：Attach Shell 连接后，在 Extensions 面板点击 "Install in Container"
- 扩展存储位置：容器内 `~/.vscode-server/extensions/`
- 持久化方式（二选一）：
  - 在 dockerfile 中安装（需 base image 包含 code-server）
  - 将 `~/.vscode-server/extensions/` 挂载为 volume
- 容器重建后未持久化的扩展会丢失，需重新安装

## 第四步：验证与调试

### 健康检查
- docker compose ps 显示 running
- curl localhost: 端口 /health 返回正常
- 日志无 ERROR

### 通用诊断
- `docker compose logs -f` 查看实时日志
- `nvidia-smi` 检查 GPU 显存占用
- `docker exec -it 容器名 /bin/bash` 进入容器调试

## 特定用途容器的配置细节

- 容器需要生成含中文的报告（HTML/PNG/PDF）时，按以下情况处理中文字体：`assets/container-data-analysis-chinese-font.md`
