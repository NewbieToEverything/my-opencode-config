# 构建网络与下载
#### 代理
Docker 的代理分两层：
| 阶段 | 走不走代理 | 配置方式 |
|------|-----------|---------|
| `docker pull` 拉取镜像 | 走 daemon 代理 | 由 Docker daemon 的已批准代理设置决定；不直接读取隐藏配置 |
| `apt`/`pip`/`curl` 等 build 时网络请求 | 不走 daemon 代理 | 按构建网络可达性临时传入 build args `HTTP_PROXY`/`HTTPS_PROXY`；host 网络不是通用前提|

- 国内镜像与代理解决的问题不同：CRAN、PyPI、APT 国内镜像只加速各自仓库；R-universe、GitHub Release、rustup 等非镜像来源仍应在需要时走代理。
- 使用 `build.network: host` 时，Linux 构建阶段可通过 `127.0.0.1:<宿主机代理端口>` 访问宿主机代理；未使用 host 网络时才考虑 `host.docker.internal`，并在 Linux 上显式映射 `host-gateway`。
- 代理只能在单次构建命令中通过 `--build-arg HTTP_PROXY=... --build-arg HTTPS_PROXY=...`（必要时同时传入小写变量）临时注入。禁止把代理写入 Dockerfile `ENV`、镜像层或项目的持久配置（build 阶段的验证方式见第三步）
- **Linux host 网络示例**：仅在已选择 host 网络且需访问宿主机回环代理时使用。上下列两套变量是本机历史兼容写法；Docker 预定义代理参数不区分大小写，是否需要两套应由下载工具行为验证，不能称为通用必填。
  ```bash
  docker build --network host \
    --build-arg HTTP_PROXY=http://127.0.0.1:<代理端口> --build-arg HTTPS_PROXY=http://127.0.0.1:<代理端口> \
    --build-arg http_proxy=http://127.0.0.1:<代理端口> --build-arg https_proxy=http://127.0.0.1:<代理端口> \
    -t <名字>:latest .
  ```
- **超时与进度回退只是症状**：候选原因包括构建代理不可达、直连慢、服务端限流、DNS/TLS 错误或工具重试。先核对实际失败地址、请求退出状态与构建网络，再比较已批准的直连/代理路径，不能仅凭网卡流量低排除上游故障。
- **本机历史案例**：同一个 37.7 MB 包曾缺代理卡约 40 分钟，传入代理后约 17 秒完成；对应构建曾命中 7/7 缓存步骤，单架构 CUDA 编译约 3.5 分钟。这些是旧环境观测，不是保证。缓存规则见 [构建材料](compose-build.md)。
- 正式构建前，使用与构建阶段相同的网络模式和基础镜像，通过代理访问实际失败的下载地址；确认目标源返回成功状态后再重建，不能只测试普通网站。仅在出现网络失败、下载目标变化或网络配置调整时做此验证；普通缓存重建不重复无关网络检查。

#### docker 国内镜像源
- **Docker镜像源配置**：需要镜像加速且已经获得配置变更授权时才配置镜像源，不把修改 daemon 当拉取前提。以下域名只保留为历史候选，未验证当前可用性，不直接批量套用；先核对目标 registry 和用户选定的可信来源：
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
- **`registry-mirrors` 的适用边界**：Docker Hub pull-through cache 可以缓存镜像内容，不是只拦截 manifest。未命中会回源；不能从速度或层进度断言每次请求路径，也不能用该设置透明加速任意 registry。显式拉取镜像源并改标签前，验证来源及镜像 digest，遵守方案变更确认。
- **显式从镜像源拉取时不能用裸 `curl` 探测可用性**：Registry 请求可能需要标准鉴权流程，`curl` 直连常返回 401/403，看起来像"镜像不可用"，而 `docker pull <mirror>/<repo>:<tag>` 实际是通的。要判断镜像源是否可用，用 `docker pull` 拉一个小镜像验证。
- 超时后最多重试 3 次，每次间隔 5 秒。
- 若多次重试仍卡在同一层，按下方「下载速率诊断」确认瓶颈；若确认不是按连接限速且重试无改善，将“替换基础镜像并自行安装框架”作为候选方案，说明证据与代价，用户确认后才执行
- 如需使用 GPU，基础镜像下载完毕后需临时用 `docker run --rm --gpus all <基础镜像> ls /dev/nvidia*` 验证 GPU 可透传到容器

#### 下载速率诊断（按需）

下载卡住、或速率稳定低于 50 kb/s 时，先读 [吞吐诊断](download-speed-diagnosis.md)（如何区分"按连接限速"与"总带宽上限"、并发改造、预先放好文件、断点续传），再决定换源或放弃镜像。低速阈值只是诊断提示；只有对比实验支持按连接限速时才增加并发。

别重新发明轮子，本 skill 已备好工具：

| 场景 | 用 |
|------|-----|
| 不确定是不是按连接限速 | `../scripts/net-probe.sh <url> [start-end]` 直接给判据 |
| 拉单个/多个大文件（HF 权重、模型分片、任意 URL） | `../scripts/parallel-fetch.py <清单.json> --out <目录> --workers 8` |
| 拉 Docker 镜像并 `docker load` 导入 | `../scripts/pull-docker-image.py <镜像:标签> --work <数据盘目录> --load` |
| 已有现成下载器但只有单连接 | 按 [吞吐诊断](download-speed-diagnosis.md) 的「预先放好文件」或「用过滤参数拆并行」改造 |

## 依据

- [Docker 代理参数](https://docs.docker.com/build/building/variables/#proxy-arguments)
- [Docker Hub 镜像缓存](https://docs.docker.com/docker-hub/image-library/mirror/)

诊断命令不得打印代理凭据、认证头或整个容器环境；修改 daemon 或重启前确认受影响任务并取得授权。
