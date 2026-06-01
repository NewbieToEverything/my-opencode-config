# Docker 容器中编译 R 包的策略

## 方案一：RSPM 二进制安装（推荐，首选）
- **速度**：几分钟（依赖可获取二进制包时）
- **不需要**系统 dev 包
- 若系统匹配，RSPM 会提供预编译的二进制包，速度远快于源码编译
## 方案二：CRAN 源码编译
- **速度**：15 分钟以上（100+ 包）
- 每个包都需要对应的 `-dev` 系统库
- `nloptr` 等包若找不到系统库，会触发 cmake 下载源码编译，更加耗时
- **失败代价高**：编译失败后重来需要重新编译所有 R 包（~15分钟），所以必须提前装好所有 dev 包

### 必备系统 dev 库

```dockerfile
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    libssl-dev \
    libxml2-dev \
    libcurl4-openssl-dev \
    libuv1-dev \
    libfontconfig1-dev \
    libharfbuzz-dev \
    libfribidi-dev \
    libfreetype6-dev \
    libpng-dev \
    libtiff-dev \
    libjpeg-dev \
    libcairo2-dev \
    zlib1g-dev \
    libglpk40 \
    libgmp10 \
    libxml2 \
    libnlopt-dev
```

`libnlopt-dev` 尤其重要：`nloptr` 找不到系统 NLopt 时会尝试用 cmake 下载编译源码，更加耗时且容易失败。

### 注意事项
- **RSPM 仅支持 LTS 版 Ubuntu** — 如 `noble`（24.04）和 `jammy`（22.04），不匹配时会自动回退到源码编译且不报错
- **RSPM SSL 错误** — 不要直接换源，先 `curl -v` 到 RSPM 地址确认问题
- **GitHub 安装的包不能走 RSPM** — 如 `remotes::install_github(...)` 必须源码编译，这些包隔离开，避免和 CRAN 包混在一起反复编译
- **中断代价高** — 某一步报错后重来（`--no-cache`），所有 R 包重新编译一遍。先在小范围验证依赖版本，确认无误后再跑全部编译
- **CRAN 镜像配置** — 在 `Rprofile.site` 中写入 `options(repos=...)`，让所有 `install.packages()` 使用国内镜像：
  ```dockerfile
  RUN echo "options(repos=c(CRAN='$CRAN_MIRROR'))" > $R_HOME/etc/Rprofile.site
  ```
- **安装选项优化** — 用 `depends=FALSE` 和 `INSTALL_opts` 减少体积、跳过无用数据；安装后用 `library(pkg, character.only=TRUE)` 验证可加载：
  ```r
  install.packages(pkg, depends=FALSE, lib='$R_HOME/library',
      INSTALL_opts='--no-data --no-help --no-demo --no-html --no-docs --no-multiarch --clean')
  library(pkg, character.only=TRUE)
  ```
