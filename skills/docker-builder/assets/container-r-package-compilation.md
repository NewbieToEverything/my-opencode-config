# Docker 容器中安装 R 包的策略

## 前置条件（所有路径共用）

以下配置必须在 `FROM` 之后、首个 `RUN` 之前设置，否则 `tzdata` 安装时会弹交互式地区选择框卡死构建：

```dockerfile
ENV DEBIAN_FRONTEND=noninteractive TZ=Asia/Shanghai
RUN ln -fs /usr/share/zoneinfo/Asia/Shanghai /etc/localtime
```

---

## 决策流程

从先到后尝试，第一个成功即止：

```
系统包管理器有预编译的 R 包？ ──是──→ 路径一
      否
RSPM 提供该包？ ───────────────是──→ 路径二
      否
CRAN 源码编译 ───────────────────→ 路径三
```

---

## 路径一：系统包管理器预编译包（首选，最快）

**原则**：优先使用基础镜像自带包管理器中的预编译 R 包，避免编译耗时。

以 **Ubuntu apt** 为例——22.04（jammy）和 24.04（noble）提供 `r-cran-mice`、`r-cran-lme4`、`r-cran-jsonlite` 等：

```dockerfile
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    r-base \
    r-cran-mice \
    r-cran-lme4 \
    r-cran-jsonlite \
    && rm -rf /var/lib/apt/lists/*
```

**注意**：若使用 Ubuntu + apt，不要混用 CRAN apt repo（`cloud.r-project.org/bin/linux/ubuntu`）和 universe 的 `r-cran-*` 包。两者版本不同会导致 apt 依赖解析冲突。

### 当预编译包不够用时

不在 `r-cran-*` 列表中的包（如 `miceadds`）需从 CRAN 安装。安装后立即用 `library()` 验证：

```dockerfile
RUN R -e "install.packages('miceadds', repos='https://mirrors.tuna.tsinghua.edu.cn/CRAN'); \
           stopifnot(require('miceadds', character.only=TRUE))"
```

`miceadds` 含 C++ 代码，需要编译，编译依赖见路径三。

---

## 路径二：RSPM 二进制（次选）

RSPM（RStudio Package Manager）是一个提供预编译 CRAN 包的服务，公共实例位于 `packagemanager.rstudio.com`。

**适用场景**：apt 没有 `r-cran-*` 包，但 RSPM 提供该包的预编译二进制。

**用法**：以 Ubuntu 22.04 为例，安装时临时将 RSPM 设为下载源：

```dockerfile
RUN R -e "install.packages('pkg', \
    repos='https://packagemanager.rstudio.com/all/__linux__/jammy/latest'); \
    stopifnot(require('pkg', character.only=TRUE))"
```

**速度**：几分钟（二进制下载），不需要系统 dev 包。

**限制**：
- 仅支持 **Ubuntu LTS**（noble 24.04、jammy 22.04），非 LTS 会静默回退到源码编译且不报错。URL 中的 `jammy`/`noble` 必须与基础镜像匹配
- GitHub 安装的包（`remotes::install_github(...)`）不能走 RSPM，必须隔离出来单独源码编译

**SSL 错误排查**：RSPM 连接失败时不要立刻换源，先确认网络可达性：

```bash
curl -v https://packagemanager.rstudio.com/all/__linux__/jammy/latest
```

---

## 路径三：CRAN 源码编译（最后手段）

**适用场景**：系统包管理器和 RSPM 都没有目标包。

**速度**：15 分钟以上（100+ 包）。**失败重来代价高**——`docker compose build --no-cache` 后所有包重新编译。先在小范围验证依赖版本无误，再跑完整 Dockerfile。

### 必备系统 dev 库

```dockerfile
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    build-essential \
    gfortran \
    liblapack-dev \
    libblas-dev \
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

即使运行时库（`liblapack3`、`libblas3`）已安装，链接阶段仍需要 `-dev` 包（`liblapack.so`、`libblas.so` 的未版本号软链接）。`gfortran` 是 Fortran 代码（如 BLAS/LAPACK 接口）编译必需。

`libnlopt-dev` 尤其重要：`nloptr` 找不到系统 NLopt 时会用 cmake 下载编译源码，耗时大增且易失败。

### CRAN 镜像配置

让所有 R 会话的 `install.packages()` 默认使用国内镜像：

```dockerfile
RUN echo 'options(repos=c(CRAN="https://mirrors.tuna.tsinghua.edu.cn/CRAN"))' \
    > $(Rscript -e "cat(R.home('etc'))")/Rprofile.site
```

### 安装选项优化

```dockerfile
RUN R -e "install.packages('pkg', repos='...', \
    dependencies=FALSE, \
    lib=file.path(Sys.getenv('R_HOME'), 'library'), \
    INSTALL_opts='--no-data --no-help --no-demo --no-html --no-docs --no-multiarch --clean'); \
    stopifnot(require('pkg', character.only=TRUE))"
```

`dependencies=FALSE` 只装直接依赖，`INSTALL_opts` 跳过文档和数据。

---

## 各路径通用验证

`install.packages()` 失败时仅打印 warning，`R -e` 仍返回 exit code 0。**必须主动验证**包可加载，否则构建不报错但最终镜像缺包。
