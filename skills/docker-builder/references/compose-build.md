# 构建与 Compose

这些字段是本机部署约定，不是所有 Docker 项目的通用必填规范。仅处理当前请求涉及的配置。

## 本机 Compose 约定（写配置时核对）
- 最终部署必须使用 `docker compose`；调试/验证阶段可临时用 `docker run`
- `container_name`：必须使用小写字母+短横线
- `image`：所有自定义镜像必须在 `docker-compose.yml` 中显式指定镜像名
- `healthcheck`：所有服务必须配置生命周期健康检查（不限 HTTP 端点）。四个时间参数必须成对给出，**缺 `start_interval` 视为不合格**：
  - `start_interval: 10s` — `start_period` 内的间隔，给短值，让容器尽快转 `healthy`
  - `interval: 5m` — **稳态**间隔，给长值。容器一旦常驻，这个间隔就是永久的
  - `timeout` — 按检查本体最慢一次的实测给，不要用默认 30s
  - `start_period` — **必须覆盖下载模型、编译、格式转换、首次建索引等全部初始化耗时**——这些都发生在监听端口之前。估不准就往大给（数小时）；没有长初始化的项目给 1–2 分钟即可
  - 版本门槛：`start_interval` 需 Docker Engine ≥ 25.0、Compose ≥ 2.20.2

  `restart` 只在容器退出时动作、不看 unhealthy，误判只产生假告警、不会中断任务。
- `restart`：所有服务必须配置（除非有明确理由不需要）
- `volume`：若有以下内容，必须显示挂载
  - 项目目录
  - 任务要求使用的环境变量文件（由用户提供引用，不读取内容；不能据此授权挂载任意隐藏配置）

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

以下沿用本机约定；修改既有项目源先遵守方案变更确认。APT 示例仅适用于相应 Ubuntu sources.list 格式，先核对发行版和源格式，不套用到 deb822 或其他发行版。
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

#### 用户
1. 仅检查数值 UID/GID，不读取或展示宿主机用户名；容器账户使用固定非个人名称（如 app）
2. 下载完基础镜像后，临时用 `docker run --rm <镜像名> sh -c 'id -u; id -g'` 确认默认用户
  - 若镜像的默认用户 UID 与宿主机一致（`id -u`），直接使用默认用户：`USER <UID>:<GID>`
  - 若不匹配，在 dockerfile 末尾创建同 UID 的用户：
    ```dockerfile
    RUN groupadd -g <GID> app && \
        useradd -m -u <UID> -g <GID> -s /bin/bash app
    USER app
    ```
3. 需要运行 `apt-get` 的步骤，必须切换至 root 用户，完成后切回第 2 步中确认的镜像用户（`<镜像UID>:<镜像GID>`或者定义的`app`）
4. 禁止在 `apt-get` 之后用 `chown` 修改**镜像默认用户的主目录**（除非已确认目标组存在）；上游镜像的应用目录需要交给宿主用户时，走 compose 一节的派生镜像方案

### docker-compose.yml
#### 用户
检查宿主机的用户 `UID/GID：id -u && id -g`，在 Compose 中使用 `user: "<UID>:<GID>"`；临时 docker run 验证才使用 `-u "<UID>:<GID>"`

**`-u` 与上游镜像冲突时的化解办法**：很多第三方镜像的安装器/服务在启动时要写自己的应用目录（装 Python 包、建软链、写配置）。上游镜像该目录属 root 且未设 `USER`，此时直接加 `-u` 会让容器起不来。**不要放弃 `-u` 规则，也不要退回 root 满盘写**——加一层派生镜像把目录交给宿主用户，再在 Compose 中显式设置 `user`：

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
落地后必须验证：`docker run --rm <名字>:latest sh -c 'id -u; id -g'` 与 `docker run --rm <名字>:latest stat -c "%u:%g" <应用目录>`，确认用户与属主都已切换。这样 bind mount 里产生的文件归宿主用户所有，日后删除/移动无需 sudo。

## 内存探测与上限

Docker 的内存限制会约束容器；应用若按宿主机内存估算缓存，可能超过该限额并触发 OOM。不能因此一律取消 `mem_limit` 或 `deploy.resources.limits`。核对实际生效的容器限额及应用内存探测逻辑，再同时设置合理的容器预算和应用缓存/低内存参数（如应用确实支持的 `LOW_RAM`）。不能假定所有应用支持同名参数。

依据：[Docker 资源限制](https://docs.docker.com/engine/containers/resource_constraints/)。


## Compose 骨架

参考 [模板](../assets/docker-compose-template.yaml)，输出配置按项目能力选择字段；删除已有配置前确认。不要保留占位值。

### 第三步：构建镜像
- **Cache 策略**：
  - Dockerfile 或依赖清单已修改：正常构建，Docker 会从变更层开始自动失效缓存
  - 远程输入已变化但构建文件未变、缓存疑似异常或需要全量验证：使用 `--no-cache`；基础镜像标签可能变化时同时使用 `--pull`
  - 下载量超过 500 MB 或清洁构建超过 5 分钟的依赖单独成层，并按清单变更频率从低到高排列
  - 独立的高成本依赖栈使用独立阶段、预构建基础镜像或 BuildKit cache mount，避免一个依赖栈变化导致其他依赖重新下载
  - 重建高成本层前估算时间和磁盘增量并告知用户；不得因耗时擅自更换依赖或运行模式
- 调试构建步骤：`docker compose --progress=plain build`
- **不要给构建输出加会缓冲的管道**：`| tail -N`、`| grep <pattern>` 在构建跑完前不输出任何内容，看起来像卡死。要看实时进度就用 `--progress=plain` 配 `tee`（`tee` 本身不缓冲）。
- 长时间构建使用可持续读取退出状态的前台会话；日志停止刷新或达到显示上限，不等于构建失败
- 代理只作为临时 build args 传入，不写入镜像 `ENV` 或项目配置。构建后检查容器运行环境无代理残留：仅检查代理变量是否存在，输出布尔状态；不打印环境变量值
- 先诊断再换源 — 安装失败时先以无凭据请求的状态码、退出状态和耗时确认实际目标是否可达，不输出认证头或带凭据的重定向地址，不要直接切换源或改版本号

## 构建上下文与临时产物

- 保留日志和临时产物在构建上下文外，例如小日志放 `/tmp`，大文件放已核对容量的数据盘。
- `/tmp` 可能是 tmpfs；先检查挂载类型和空间，再决定是否写入。清理前遵守删除确认规则。
- 第三方 Dockerfile 的 `COPY . .` 需要对应仓库作为构建上下文；Compose 文件可通过 `build.context` 指向该仓库，不必把 Compose 文件搬进仓库。
- 日志使用实时前台会话或 `tee`，记录实际退出状态。不要因管道的退出码或显示截断误判构建结果。

## 缓存的适用条件

`COPY` 输入发生变化时，该层及其后续层可能失效；`git pull` 本身不是缓存失效条件。源码变化是否导致依赖重新下载，取决于 Dockerfile 顺序。将稳定依赖放在频繁变化的源码之前，按构建日志确认命中，不无条件使用 `--no-cache`。

依据：[Docker 缓存失效](https://docs.docker.com/build/cache/invalidation/)。


### 构建验证
- `docker compose ps` 显示 running
- 检查相关错误日志，并结合退出状态和真实工作流判断；日志中的 ERROR 字样不是唯一验收标准
- 验证必须覆盖项目的真实最小工作流，而不只是执行版本命令
- 按项目实际能力验证：容器健康、扩展后端或语言服务可加载、代表性输入能生成预期输出、硬件加速可被框架使用
