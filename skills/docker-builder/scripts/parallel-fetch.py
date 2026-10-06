#!/usr/bin/env python3
"""并行分块下载器：用 N 条独立 HTTP 连接拉取大文件，规避上游的按连接限速。

为什么需要它
------------
实测 Docker Hub 与 hf-mirror.com 都对**单条连接**限速：开头约 30 秒 9 MB/s，
之后掉到 180 KB/s。`docker pull`、多数下载器都只用一条长连接，因此必然爬行
（实测 85 GB 的 ETA 从 1.2 小时劣化到 34 小时）。同一时刻开 3~4 条连接，总吞吐
立刻从 2 MB/s 升到 13 MB/s。

本脚本把每个文件切成固定大小的块，**每块一次新的 range 请求**（= 独立连接），
边下边落到 parts 目录，支持断点续传，完成后按内容寻址校验。

用法
----
写一个 JSON 清单，然后：

    python3 parallel-fetch.py manifest.json --out /data/models --workers 8

清单格式（list，每项一个目标文件）：

    [
      {"url": "https://example.com/big.gguf",
       "out": "big.gguf",
       "size": 54817524224,
       "sha256": "4c1eb2ce...",       // 可选，但强烈建议
       "start": 0, "end": 54817524223, // 可选，只拉文件的一段（HF safetensors 等）
       "headers": {"Authorization": "Bearer ..."}  // 可选
      }
    ]

`start`/`end` 是**该目标在最终文件里的绝对字节区间**，不是 HTTP Range 头的值；
脚本会自动换算。只拉一段时，`size` 应填该段长度。

断点续传
--------
每块先写 `<out>.parts/<序号>`，成功后才改名。因此中断、重启、换并发都能接着走，
不会重下已完成的块。已存在且尺寸正确的块会被跳过。

安全边界
--------
只对**你有权访问**的地址使用。脚本不做任何认证绕过。
"""

import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_CHUNK = 32 << 20


def log(*a):
    print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)


def build_cmd(url, s, e, dst, proxy, headers):
    cmd = ["curl", "-sL", "--max-time", "600", "-r", f"{s}-{e}",
           "-o", str(dst), "-w", "%{http_code}"]
    for k, v in (headers or {}).items():
        cmd[1:1] = ["-H", f"{k}: {v}"]
    if proxy:
        cmd[1:1] = ["-x", proxy]
    cmd.append(url)
    return cmd


def fetch_one(job):
    """下载单个块；job = (i, url, start, end, want, dst, proxy, headers, state)"""
    i, url, start, end, want, dst, proxy, headers, state = job
    tmp = Path(str(dst) + ".tmp")
    for attempt in range(6):
        r = subprocess.run(build_cmd(url, start, end, tmp, proxy, headers),
                           capture_output=True, text=True)
        code = r.stdout.strip()[-3:]
        if code == "206" and tmp.exists() and tmp.stat().st_size == want:
            tmp.rename(dst)
            with state["lock"]:
                state["done"] += 1
            return
        tmp.unlink(missing_ok=True)
        log(f"    块{i} 重试 {attempt+1} (HTTP {code}) {r.stderr[:100]}")
        time.sleep(2 + attempt * 3)
    raise RuntimeError(f"块 {i} ({start}-{end}) 最终失败")


def sha256_of(path, bufsize=16 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(bufsize)
            if not b:
                break
            h.update(b)
    return "sha256:" + h.hexdigest()


def fetch_file(t, outdir, chunk, workers, proxy):
    url = t["url"]
    name = t.get("out") or url.rsplit("/", 1)[-1]
    start = int(t.get("start", 0))
    end = int(t["end"]) if t.get("end") is not None else None

    # 拿总长度：优先用清单里的 size，否则问服务器
    if t.get("size"):
        total = int(t["size"])
        if end is None:
            end = start + total - 1
    else:
        probe = subprocess.run(
            build_cmd(url, 0, 0, os.devnull, proxy, t.get("headers")) + ["-o", "/dev/null"],
            capture_output=True, text=True)
        cr = subprocess.run(["curl", "-sIL", "--max-time", "60"] +
                            (["-x", proxy] if proxy else []) +
                            [url], capture_output=True, text=True)
        cl = 0
        for line in cr.stdout.splitlines():
            if line.lower().startswith("content-length:"):
                cl = int(line.split(":", 1)[1].strip())
        if not cl:
            sys.exit(f"{name}: 无法确定大小，请在校验清单里写明 size")
        total = cl - start if end is None else end - start + 1
        if end is None:
            end = start + total - 1

    out = Path(outdir) / name
    if out.exists() and t.get("sha256") == sha256_of(out):
        log(f"已存在且校验通过，跳过 {name}")
        return
    if out.exists() and not t.get("sha256") and out.stat().st_size == total:
        log(f"已存在且尺寸相同，跳过 {name}（无 sha256，未做内容校验）")
        return

    parts = Path(str(out) + ".parts")
    parts.mkdir(parents=True, exist_ok=True)
    # 清掉上次中断留下的 .tmp，避免占着磁盘又不被计入续传判断
    for stale in parts.glob("*.tmp"):
        stale.unlink(missing_ok=True)
    n = (total + chunk - 1) // chunk
    state = {"done": 0, "lock": __import__("threading").Lock()}
    jobs = []
    for i in range(n):
        s = start + i * chunk
        e = min(s + chunk, end + 1) - 1
        d = parts / f"{i:05d}"
        if d.exists() and d.stat().st_size == e - s + 1:
            with state["lock"]:
                state["done"] += 1
            continue
        jobs.append((i, url, s, e, e - s + 1, d, proxy, t.get("headers"), state))

    log(f"{name}: {len(jobs)}/{n} 块待下（共 {total/1e9:.2f}GB，{workers} 并发）")
    t0 = time.time()
    if jobs:
        with cf.ThreadPoolExecutor(max_workers=workers) as ex:
            list(ex.map(fetch_one, jobs))
        got = (n - len(jobs)) * chunk
        el = time.time() - t0
        log(f"  下载完成 {got/1e9:.2f}GB / {el:.0f}s = {got/1e6/el:.1f} MB/s")

    # 边拼边删，峰值磁盘约为 1x 文件大小
    h = hashlib.sha256()
    tmp = Path(str(out) + ".assembling")
    try:
        with open(tmp, "wb") as w:
            for i in range(n):
                f = parts / f"{i:05d}"
                if not f.exists() or f.stat().st_size != min(chunk, total - i * chunk):
                    sys.exit(f"{name}: 块 {i} 缺失或尺寸异常，无法拼装")
                with open(f, "rb") as r:
                    while True:
                        b = r.read(16 << 20)
                        if not b:
                            break
                        h.update(b)
                        w.write(b)
                f.unlink()
    finally:
        # 无论成败都别留下 parts 目录和半成品占用磁盘
        if tmp.exists() and tmp.stat().st_size != total:
            tmp.unlink(missing_ok=True)
        shutil.rmtree(parts, ignore_errors=True)

    if tmp.stat().st_size != total:
        sys.exit(f"{name}: 尺寸 {tmp.stat().st_size} != 期望 {total}")
    if t.get("sha256"):
        got_sha = "sha256:" + h.hexdigest()
        if got_sha != "sha256:" + t["sha256"]:
            tmp.rename(str(out) + ".BADHASH")
            sys.exit(f"{name}: sha256 校验失败\n  期望 sha256:{t['sha256']}\n  实际 {got_sha}")
        log(f"  ✓ {name} sha256 校验通过")
    else:
        log(f"  ! {name} 未提供 sha256，仅校验了尺寸")
    tmp.rename(out)


def main():
    ap = argparse.ArgumentParser(
        description="并行分块下载大文件（规避按连接限速），支持断点续传与 sha256 校验",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("manifest", help="JSON 清单路径")
    ap.add_argument("--out", required=True, help="输出目录")
    ap.add_argument("--workers", type=int, default=8, help="并发连接数（默认 8）")
    ap.add_argument("--chunk-mb", type=float, default=32,
help="每块大小 MB，可写小数（默认 32；调试小文件时可写 0.004）")
    ap.add_argument("--proxy", default=os.environ.get("HTTPS_PROXY"),
                    help="HTTP 代理，如 http://127.0.0.1:PORT（默认取环境变量）")
    a = ap.parse_args()

    targets = json.load(open(a.manifest, encoding="utf-8"))
    if isinstance(targets, dict):
        targets = targets.get("targets", [])
    Path(a.out).mkdir(parents=True, exist_ok=True)
    log(f"共 {len(targets)} 个目标，并发 {a.workers}，块 {a.chunk_mb}MB"
        + (f"，代理 {a.proxy}" if a.proxy else ""))
    for t in targets:
        fetch_file(t, a.out, max(1, int(a.chunk_mb * (1 << 20))), a.workers, a.proxy)
    log("全部目标完成")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("已中断，重跑同一命令即可续传")
        sys.exit(130)