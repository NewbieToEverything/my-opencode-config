#!/usr/bin/env python3
"""把 Docker 镜像拉到本地并 `docker load` 导入，绕过被限速的 `docker pull`。

为什么需要它
------------
`docker pull` 用单条连接下载 blob，遇到按连接限速的 registry 会爬到几小时。
本脚本自己走 registry HTTP API：匿名取 token → 解析 manifest → 列出每个 blob
的 digest 与大小 → 用 `parallel-fetch.py` 的分块并发逐个拉取 → 校验 sha256 →
装配成 **docker-archive** tar → `docker load`。

为什么不是 OCI layout
---------------------
存储驱动为 `overlay2`（未启用 containerd 镜像存储）时，`docker load` 只认
docker-archive 格式：`<config>.json` + `manifest.json` + 各 `<id>/layer.tar`，
且**层必须是未压缩的 tar**。直接喂 OCI layout（`oci-layout` + `index.json` +
`blobs/sha256/*`）会报 `blobs/json: no such file or directory`。

用法
----
    # 1) 只拉不导入（先看要下多少）
    python3 pull-docker-image.py nvidia/cuda:13.0.0-devel-ubuntu24.04 \
        --work ~/cache/oci --proxy http://127.0.0.1:PORT

    # 2) 拉完校验并导入
    python3 pull-docker-image.py nvidia/cuda:13.0.0-devel-ubuntu24.04 \
        --work ~/cache/oci --proxy http://127.0.0.1:PORT --load

    # 走国内镜像源（把 blob 请求也导向镜像源，绕开上游 registry）
    python3 pull-docker-image.py nvidia/cuda:13.0.0-devel-ubuntu24.04 \
        --work ~/cache/oci --registry https://docker.m.daocloud.io --load

注意
----
* 镜像源的 manifest 与 blob 常带鉴权流程，`curl` 直连探测会返回 401/403，
  看起来像"镜像不可用"；本脚本按 registry 规范走 token 流程，能正确处理。
* 中间产物（tar、解压出的层）体积可达镜像的 2~3 倍，**不要放在 tmpfs**
  （`/tmp` 在很多机器上是内存盘，几百 GB 会触发 OOM）。`--work` 请指定数据盘。
* 所有 blob 按 digest 校验后才装配，任何一个字节不符即中止，不会装进损坏镜像。
"""

import argparse
import json
import os
import subprocess
import sys
import tarfile
import time
import urllib.request
from pathlib import Path

SCHEMA2 = "application/vnd.docker.distribution.manifest.v2+json"
INDEX_TYPES = ("application/vnd.oci.image.index.v1+json,"
               "application/vnd.docker.distribution.manifest.list.v2+json")
OCI_MANIFEST = "application/vnd.oci.image.manifest.v1+json"
OCI_CONFIG = "application/vnd.oci.image.config.v1+json"
OCI_LAYER = "application/vnd.oci.image.layer.v1.tar+gzip"
HERE = Path(__file__).resolve().parent


def log(*a):
    print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)


class Registry:
    def __init__(self, host, proxy, insecure=False):
        self.host = host
        self.proxy = proxy
        self.insecure = insecure
        self.token = None

    def _open(self, req):
        if self.proxy:
            h = urllib.request.ProxyHandler({"http": self.proxy, "https": self.proxy})
            op = urllib.request.build_opener(h)
        else:
            op = urllib.request.build_opener()
        return op.open(req, timeout=120)

    def login(self, repo):
        if self.host in ("registry-1.docker.io", "docker.io"):
            u = ("https://auth.docker.io/token?service=registry.docker.io"
                 f"&scope=repository:{repo}:pull")
        else:
            u = f"https://{self.host}/v2/{repo}/tags/list"
        try:
            self.token = json.load(self._open(urllib.request.Request(u)))["token"]
        except Exception as e:
            sys.exit(f"取 token 失败: {e}")
        log(f"已获取 {self.host} 的匿名 token")

    def get(self, path, accept):
        req = urllib.request.Request(f"https://{self.host}{path}")
        if self.token:
            req.add_header("Authorization", f"Bearer {self.token}")
        for a in accept.split(","):
            req.add_header("Accept", a.strip())
        return self._open(req)


def resolve(reg, repo, ref):
    raw = json.load(reg.get(f"/v2/{repo}/manifests/{ref}", INDEX_TYPES))
    if "manifests" in raw:                      # 多架构 index → 取 amd64/linux
        d = [m["digest"] for m in raw["manifests"]
             if m.get("platform", {}).get("architecture") == "amd64"
             and m.get("platform", {}).get("os") == "linux"]
        if not d:
            sys.exit("该镜像没有 amd64/linux 变体")
        raw = json.load(reg.get(f"/v2/{repo}/manifests/{d[0]}", SCHEMA2))
    if raw.get("mediaType") != SCHEMA2:
        sys.exit(f"意外的 manifest 类型: {raw.get('mediaType')}")
    return raw


def main():
    ap = argparse.ArgumentParser(description="分块并发拉取 Docker 镜像并导入本地（规避按连接限速）",
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image", help="镜像引用，如 nvidia/cuda:13.0.0-devel-ubuntu24.04")
    ap.add_argument("--work", required=True, help="中间产物目录（务必在数据盘，不要用 tmpfs）")
    ap.add_argument("--proxy", default=os.environ.get("HTTPS_PROXY"))
    ap.add_argument("--registry", default=None,
                    help="改用此 registry 拉取（如 https://docker.m.daocloud.io）")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--chunk-mb", type=int, default=32)
    ap.add_argument("--load", action="store_true", help="装配成 tar 并执行 docker load")
    ap.add_argument("--keep", action="store_true", help="导入后保留中间产物")
    a = ap.parse_args()

    work = Path(a.work).resolve()
    blobs = work / "blobs"
    blobs.mkdir(parents=True, exist_ok=True)

    if a.registry:
        host = a.registry.split("://", 1)[-1].rstrip("/")
    else:
        host = "registry-1.docker.io"
    repo, _, ref = a.image.partition(":")
    if "/" not in repo:
        repo = "library/" + repo

    reg = Registry(host, a.proxy)
    reg.login(repo)
    mf = resolve(reg, repo, ref)
    items = [(mf["config"]["digest"], mf["config"]["size"], "config")]
    for i, l in enumerate(mf["layers"]):
        items.append((l["digest"], l["size"], f"layer{i+1}/{len(mf['layers'])}"))
    total = sum(s for _, s, _ in items)
    log(f"{repo}:{ref}  {len(items)} 个 blob，合计 {total/1e9:.2f} GB")

    # 交给通用分块下载器（digest 即天然的内容寻址校验）
    manifest = {"targets": [
        {"url": f"https://{host}/v2/{repo}/blobs/{d}",
         "out": d.split(":", 1)[1], "size": s,
         "headers": {"Authorization": f"Bearer {reg.token}"}}
        for d, s, _ in items]}
    mpath = work / "fetch-manifest.json"
    mpath.write_text(json.dumps(manifest, indent=1))
    subprocess.run([sys.executable, str(HERE / "parallel-fetch.py"), str(mpath),
                    "--out", str(blobs), "--workers", str(a.workers),
                    "--chunk-mb", str(a.chunk_mb)]
                   + (["--proxy", a.proxy] if a.proxy else []), check=True)

    if not a.load:
        log(f"blob 已就绪：{blobs}（未导入）。加 --load 可继续装配并 docker load")
        return

    # Docker schema2 manifest → OCI mediaType，装进 OCI layout
    import hashlib
    oci = {"schemaVersion": 2, "mediaType": OCI_MANIFEST,
           "config": {"mediaType": OCI_CONFIG,
                      "digest": mf["config"]["digest"], "size": mf["config"]["size"]},
           "layers": [{"mediaType": OCI_LAYER, "digest": l["digest"], "size": l["size"]}
                      for l in mf["layers"]]}
    mb = json.dumps(oci, separators=(",", ":")).encode()
    mdig = "sha256:" + hashlib.sha256(mb).hexdigest()
    (blobs / mdig.split(":", 1)[1]).write_bytes(mb)
    index = {"schemaVersion": 2, "mediaType": "application/vnd.oci.image.index.v1+json",
             "manifests": [{"mediaType": OCI_MANIFEST, "digest": mdig, "size": len(mb),
                            "annotations": {"io.containerd.image.name": f"docker.io/{repo}:{ref}",
                                            "org.opencontainers.image.ref.name": ref}}]}
    tar_path = work / (ref.replace(":", "_") + ".tar")
    log(f"装配 OCI layout -> {tar_path}")
    with tarfile.open(tar_path, "w") as tf:
        def add(name, data):
            ti = tarfile.TarInfo(name); ti.size = len(data)
            tf.addfile(ti, __import__("io").BytesIO(data))
        add("oci-layout", b'{"imageLayoutVersion":"1.0.0"}')
        add("index.json", json.dumps(index).encode())
        for d, _, _ in items:
            src = blobs / d.split(":", 1)[1]
            tf.add(src, arcname=f"blobs/sha256/{d.split(':', 1)[1]}")
        tf.add(blobs / mdig.split(":", 1)[1], arcname=f"blobs/sha256/{mdig.split(':', 1)[1]}")
    log(f"装配完成 {tar_path.stat().st_size/1e9:.2f} GB，开始 docker load")
    subprocess.run(["docker", "load", "-i", str(tar_path)], check=True)

    if not a.keep:
        log("清理中间产物（--keep 可保留）")
        for p in (tar_path,):
            p.unlink(missing_ok=True)
    log("完成")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        sys.exit(f"子命令失败（退出码 {e.returncode}）")