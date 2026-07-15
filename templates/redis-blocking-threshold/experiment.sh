#!/usr/bin/env bash
set -euo pipefail

# TOPICS.md #1 / implement.md 10장 — Redis 단일 인스턴스는 초당 몇 건의 SET/GET
# 요청부터 P99 레이턴시가 급격히(기본 10배) 튀는가? redis-benchmark --csv로
# concurrency를 스윕하며 측정한다. bash에는 YAML 파서가 없어 params.yml 읽기와
# results.json 조립은 python3(+PyYAML, 공용 이미지에 이미 포함)에 위임한다.

PARAMS="params.yml"
OUT="results"
SMOKE=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --params) PARAMS="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    --smoke) SMOKE=true; shift ;;
    *) echo "unknown flag: $1" >&2; exit 2 ;;
  esac
done

if [[ ! -f "$PARAMS" ]]; then
  echo "params file not found: $PARAMS" >&2
  exit 1
fi

mkdir -p "$OUT/raw"

read_param() {
  python3 -c "
import yaml
with open('$PARAMS') as f:
    params = yaml.safe_load(f)
smoke = $([[ "$SMOKE" == true ]] && echo True || echo False)
key = '$1'
if smoke and 'smoke' in params and key in params['smoke']:
    value = params['smoke'][key]
else:
    value = params[key]
print(' '.join(str(v) for v in value) if isinstance(value, list) else value)
"
}

CONCURRENCY_SWEEP=($(read_param concurrency_sweep))
REQUESTS_PER_STEP="$(read_param requests_per_step)"
SLA_MULTIPLIER="$(read_param sla_multiplier)"

# redis 서비스가 연결을 받을 때까지 대기 (depends_on은 컨테이너 시작만 보장, 준비 완료는 보장하지 않음)
ready=false
for _ in $(seq 1 30); do
  if redis-cli -h redis ping 2>/dev/null | grep -q PONG; then
    ready=true
    break
  fi
  sleep 0.5
done
if [[ "$ready" != true ]]; then
  echo "redis가 응답하지 않습니다 (30회 재시도 실패)" >&2
  exit 1
fi

STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
RUN_ID="$(date -u +%Y-%m-%dT%H-%M-%SZ)-$(head -c4 /dev/urandom | od -An -tx1 | tr -d ' \n')"

RAW_CSV="$OUT/raw/redis_benchmark.csv"
echo "concurrency,test,rps,avg_latency_ms,min_latency_ms,p50_latency_ms,p95_latency_ms,p99_latency_ms,max_latency_ms" > "$RAW_CSV"

for concurrency in "${CONCURRENCY_SWEEP[@]}"; do
  echo "concurrency=$concurrency 실행 중..." >&2
  redis-benchmark -h redis -t set,get -n "$REQUESTS_PER_STEP" -c "$concurrency" --csv \
    | tail -n +2 \
    | sed "s/^/${concurrency},/" \
    >> "$RAW_CSV"
done

FINISHED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
ARCH="$(uname -m)"
CPU_CORES="$(nproc)"
MEMORY_GB="$(awk '/MemTotal/ {printf "%.1f", $2/1024/1024}' /proc/meminfo)"
SMOKE_JSON=$([[ "$SMOKE" == true ]] && echo True || echo False)

python3 <<PYEOF
import csv
import json

with open("$RAW_CSV") as f:
    rows = list(csv.reader(f))
rows = rows[1:]  # 우리가 직접 쓴 헤더 한 줄 제외

data = []
set_p99_by_concurrency = {}
for concurrency_str, test, rps, avg, mn, p50, p95, p99, mx in rows:
    concurrency = int(concurrency_str)
    data.append({
        "metric": "throughput_ops_sec", "series": test, "x_label": "concurrency",
        "x": concurrency, "y": round(float(rps), 1), "unit": "ops/sec", "note": None,
    })
    data.append({
        "metric": "p99_latency_ms", "series": test, "x_label": "concurrency",
        "x": concurrency, "y": round(float(p99), 3), "unit": "ms", "note": None,
    })
    if test == "SET":
        set_p99_by_concurrency[concurrency] = float(p99)

concurrency_sweep = sorted(set_p99_by_concurrency)
baseline_p99 = set_p99_by_concurrency[concurrency_sweep[0]] if concurrency_sweep else None
sla_multiplier = float("$SLA_MULTIPLIER")

threshold = None
if baseline_p99 is not None:
    for c in concurrency_sweep:
        if set_p99_by_concurrency[c] > baseline_p99 * sla_multiplier:
            threshold = c
            break

started_at = "$STARTED_AT"
finished_at = "$FINISHED_AT"

results = {
    "schema_version": "1.0",
    "experiment": {
        "id": "redis-blocking-threshold",
        "agenda": "Redis 단일 인스턴스는 초당 몇 건의 SET/GET 요청부터 P99 레이턴시가 급격히(10배 이상) 튀며 이벤트 루프가 포화 상태에 진입하는가?",
        "template": "redis-blocking-threshold",
        "template_version": "1.0.0",
    },
    "run": {
        "run_id": "$RUN_ID",
        "started_at": started_at,
        "finished_at": finished_at,
        "smoke": $SMOKE_JSON,
        "environment": {"arch": "$ARCH", "cpu_cores": $CPU_CORES, "memory_gb": $MEMORY_GB},
    },
    "parameters": {
        "concurrency_sweep": concurrency_sweep,
        "requests_per_step": $REQUESTS_PER_STEP,
        "sla_multiplier": sla_multiplier,
    },
    "data": data,
    "summary": {
        "blocking_threshold_concurrency": threshold,
        "baseline_p99_ms": round(baseline_p99, 3) if baseline_p99 is not None else None,
    },
    "status": "success",
    "notes": [],
}

with open("$OUT/results.json", "w") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
    f.write("\n")

print("wrote $OUT/results.json")
PYEOF
