#!/bin/bash
# 网络吞吐探针：判断瓶颈是「按连接限速」还是「总带宽上限」。
#
# 用法：
#   ./net-probe.sh                          # 只测当前总吞吐
#   ./net-probe.sh <url>                    # 测该 URL 的短请求与长连接速率
#   ./net-probe.sh <url> <start>-<end>      # 指定字节区间（中段更真实，避开 CDN 缓存）
#
# 判读（详见 references/download-speed-diagnosis.md）：
#   长连接持续速率 << 短请求速率  → 按连接限速，加并发有效
#   两者相当                        → 总带宽上限，只能等
set -u
RX() { awk '/:/{s+=$2} END{print s+0}' /proc/net/dev; }

rate() {  # rate <秒数>：输出 KB/s
  local d=$1 a b
  a=$(RX); sleep "$d"; b=$(RX)
  echo $(( (b - a) / 1024 / d ))
}

echo "=== 1. 当前总吞吐（10 秒）==="
echo "  $(rate 10) KB/s"

[ $# -lt 1 ] && exit 0

URL="$1"
RANGE="${2:-0-20971519}"
PROXY_ARG=""
[ -n "${HTTPS_PROXY:-}" ] && PROXY_ARG="-x ${HTTPS_PROXY}"

echo
echo "=== 2. 单个短 range 请求（${RANGE}）==="
curl -sL -o /dev/null -m 60 $PROXY_ARG -r "$RANGE" \
  -w "  HTTP %{http_code}  %{size_download}B  %{speed_download} B/s\n" "$URL"

echo
echo "=== 3. 长连接持续吞吐（一条连接连拉 3 次同样大小的段，每 8 秒采样）==="
prev=$(RX); t0=$(date +%s)
for i in 1 2 3; do
  curl -sL -o /dev/null -m 30 $PROXY_ARG -r "$RANGE" "$URL" &
  sleep 8
  cur=$(RX); el=$(( $(date +%s) - t0 ))
  echo "  第 $((i*8))秒累计: $(( (cur - prev) / 1024 / el )) KB/s（平均）"
  prev=$cur
done
wait 2>/dev/null

echo
echo "=== 4. 4 条并发连接的总吞吐（对比第 1 步的基线）==="
prev=$(RX); t0=$(date +%s)
for i in 0 1 2 3; do
  S=$(( 900000000 + i * 30000000 ))
  curl -sL -o /dev/null -m 30 $PROXY_ARG -r "${S}-$((S+20971519))" "$URL" &
done
sleep 20
cur=$(RX); el=$(( $(date +%s) - t0 ))
echo "  $(( (cur - prev) / 1024 / el )) KB/s"
wait 2>/dev/null

cat <<'EOF'

判读：
  · 第 4 步显著高于第 1 步  → 上游按连接限速，用 scripts/parallel-fetch.py 加并发
  · 第 4 步与第 1 步相当    → 总带宽上限，并行无用
  · 第 3 步明显低于第 2 步  → 同上结论的另一个证据（长连接被压）
EOF