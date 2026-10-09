---
name: docker-builder
description: 创建或修改 Docker 镜像、Compose 部署及 VS Code Dev Container；用于相关 GPU 配置、模型下载或构建故障排查。
---

# Docker Builder

交付可复现的容器配置，并用项目的真实最小工作流验收。按用户要求选择工作流，普通镜像构建不自动扩成 Dev Container 配置或模型下载。

## 按任务读取

| 当前任务 | 读取材料 |
|---|---|
| 新建或修改 Dockerfile、Compose，选择基础镜像、权限和缓存策略 | [构建与 Compose](references/compose-build.md)；新配置可参考 [Compose 模板](assets/docker-compose-template.yaml) |
| 镜像拉取、构建网络、代理或下载失败 | [构建网络](references/network-build.md)；持续下载慢再读 [吞吐诊断](references/download-speed-diagnosis.md) |
| 配置或验证 GPU、窄化 CUDA 编译架构、导入本地镜像 | [GPU 与镜像导入](references/gpu-import.md) |
| 用户要求 VS Code Dev Container 或扩展自动安装 | [Dev Container](references/devcontainer.md)，涉及镜像或 Compose 改动时再读构建材料 |
| 中文报告字体或 R 包编译依赖 | 分别读 [字体配置](references/container-data-analysis-chinese-font.md)、[R 编译依赖](references/container-r-package-compilation.md) |
| 查找可复用镜像或记录已验证结果 | `references/created-images-containers.local.md`；不存在时用 [记录模板](references/created-images-containers.md) |

只加载当前任务所需材料；已有故障直接进入对应诊断，不重复跑完整部署流程。上述相对路径以本技能目录为基准。

## 保留的操作边界

- 最终部署使用 `docker compose`；调试和验证可临时用 `docker run`。
- 按已指定的版本和方案实施。安装软件、删除或覆盖现有内容、重启 Docker daemon、改变用户已确定的方案，按当前用户和项目规则取得确认。
- 不读取隐藏配置、私钥或凭据；不展示用户名、令牌、会话信息或带凭据的代理地址。仅提取任务所需的非敏感状态。
- 构建代理仅临时注入，不能写入镜像 ENV 或项目持久配置。Dev Container 的扩展下载网络按专门材料处理。
- 临时日志和下载产物不进入构建上下文；大文件先检查文件系统和容量，不把可能位于 tmpfs 的 `/tmp` 当数据盘。
- Linux / Docker + nvidia-container-toolkit / RTX 5070 Ti 16GB（sm_120）是原有实测环境；具体速率、编译耗时和框架支持情况不得泛化到其他机器。

## 完成标准

1. 请求涉及的声明式配置已落地且解析通过，版本、端口、权限和持久化设置有依据。
2. 在任务需要运行验证时，确认构建或下载的实际退出结果，服务状态和代表性输入输出符合要求；版本命令成功不能替代真实工作流。
3. GPU、Dev Container 和容器内 Git/SSH 只验收实际启用的能力，细则见相应材料。
4. 修复本次改动造成的问题并重验受影响部分；已通过的无关验证不重复运行。不因日志停止刷新就认定构建失败。
5. 汇报修改文件、关键结果和未完成项。仅配置编辑任务不擅自扩成构建或重启；未做运行验证时明确说明。

部署完成后按记录模板更新本机实况，记录版本、用途、已验证状态、故障原因与证据，不记录敏感数据。

## 已有工具

工具在技能目录的 `scripts/` 下。使用前核对输入和目标位置，下载校验及断点续传规则见对应材料。

- `net-probe.sh <url> [start-end]`：比较请求吞吐；结果用于诊断，不能单凭测速断言唯一根因。
- `parallel-fetch.py <清单.json> --out <目录> --workers 8`：并行分块下载、断点续传和 SHA-256 校验。
- `pull-docker-image.py <镜像:标签> --work <数据盘目录> --load`：拉取并装配 docker-archive；只在用户任务包含导入时使用 `--load`。
