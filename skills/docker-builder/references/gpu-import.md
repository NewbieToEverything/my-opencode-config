# GPU 与镜像导入

这两项按需执行，普通 CPU 镜像构建不用加载本材料。

## GPU 前提

核对 NVIDIA Driver、Container Toolkit、基础镜像 CUDA、框架版本与 GPU compute capability。Linux / RTX 5070 Ti sm_120 是原有环境事实，框架支持情况需要当前版本证据。

#### GPU 配置
- 需要 GPU 的服务在 Compose 的对应 service 内声明设备；下面是示例，设备数量按任务选择：
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
        NVIDIA_VISIBLE_DEVICES: all
        NVIDIA_DRIVER_CAPABILITIES: compute,utility
  ```

## 编译架构

只服务指定硬件时可窄化 CUDA 架构，但先确认构建系统支持对应参数。`CUDA_ARCHITECTURES` 不是所有项目通用 build arg；从源码或官方说明核对参数和 GPU 型号，不把整个产品系列映射成一个值。缺少目标架构时检查是否有可用 PTX/JIT 路径，再判断兼容性。

### GPU 验证
如果需要使用 GPU,在容器启动后做如下验证：
- 根据容器用途选择验证命令来确认 GPU 设备存在：
  - 通用容器：`docker exec 容器名 nvidia-smi`
  - 使用了框架的容器：需采用框架特定的命令，如 PyTorch 容器采用 `docker exec 容器名 python3 -c "import torch; print(torch.cuda.is_available())"`
- 若验证失败，检查环境变量 `docker exec 容器名 env | grep NVIDIA`

## 本地镜像导入

- **导入本地镜像的格式**：在旧环境的经典镜像存储导入链路中，`docker load` 只认 **docker-archive** 格式（`manifest.json` + `<config>.json` + 各 `<id>/layer.tar`），传入 OCI layout（`oci-layout` + `index.json` + `blobs/sha256/*`）会报 `blobs/json: no such file or directory` 之类的错。转换要点：按实际 layer media type 判断压缩方式；旧链路的 gzip blob 需解压为 `layer.tar`，不能把所有 OCI layer 都当 gzip；解压后按镜像 config 里的 `rootfs.diff_ids` 逐层校验 sha256，任一不符即中止。这样转换是内容寻址的，装不出与上游不一致的镜像。

使用已有 `../scripts/pull-docker-image.py` 时，沿用其 docker-archive 路径与校验，不为整理文档改写脚本。镜像存储后端及导入格式按实际 Engine 版本核对；大 tar 和解压层放数据盘，导入后核对目标镜像身份。

依据：[Compose GPU 配置](https://docs.docker.com/compose/how-tos/gpu-support/)。
