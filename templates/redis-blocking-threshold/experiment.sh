#!/usr/bin/env bash
set -euo pipefail

# TOPICS.md #1 — Redis 단일 인스턴스는 초당 몇 건의 SET/GET 요청부터 P99
# 레이턴시가 급격히(기본 10배) 튀는가? redis-benchmark --csv로 concurrency를
# 스윕하며 측정한다. bash에는 YAML 파서가 없어 params.yml 읽기와 results.json
# 조립은 python3(+PyYAML, 공용 이미지에 이미 포함)에 위임한다.
#
# 보안 노트: 아래 모든 python3 호출은 <<'PYEOF'(작은따옴표) 헤레독을 쓴다 —
# bash가 헤레독 안의 $변수를 문자열로 치환하지 않는다는 뜻이다. params.yml에서
# 읽은 값(사람이 편집하거나 향후 PR로 들어올 수 있는 데이터)은 항상
# os.environ[...]을 통해 파이썬이 값으로만 읽고 int()/float()로 명시 변환한다 —
# bash 치환으로 파이썬 소스 텍스트에 직접 꽂아 넣지 않는다(그렇게 하면 값 안의
# 특수문자가 코드로 실행될 수 있다).
#
# 각 concurrency 스텝은 REPEATS회(스모크 1회 / 실전 3회) 반복해 중앙값을
# 쓰고, 범위(min~max)를 note에 남긴다 — 단일 샘플로는 노이즈와 실제 신호를
# 구분할 수 없다. 서버(redis) CPU/명령 처리시간뿐 아니라 부하를 쏘는 runner
# 컨테이너 자체의 CPU 사용률(/proc/stat 델타)도 같이 재서, "느려진 게 서버가
# 아니라 클라이언트 쪽이 바빠서일 수도 있다"는 가능성까지 같은 실행에서
# 확인한다.

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

export PARAMS SMOKE

mkdir -p "$OUT/raw"

read_param() {
  PARAM_KEY="$1" python3 <<'PYEOF'
import os
import yaml

with open(os.environ["PARAMS"]) as f:
    params = yaml.safe_load(f)

smoke = os.environ["SMOKE"] == "true"
key = os.environ["PARAM_KEY"]
if smoke and "smoke" in params and key in params["smoke"]:
    value = params["smoke"][key]
else:
    value = params[key]
print(" ".join(str(v) for v in value) if isinstance(value, list) else value)
PYEOF
}

CONCURRENCY_SWEEP=($(read_param concurrency_sweep))
REQUESTS_PER_STEP="$(read_param requests_per_step)"
SLA_MULTIPLIER="$(read_param sla_multiplier)"

if [[ "$SMOKE" == "true" ]]; then
  REPEATS=1
else
  REPEATS=3
fi

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
echo "concurrency,rep,test,rps,avg_latency_ms,min_latency_ms,p50_latency_ms,p95_latency_ms,p99_latency_ms,max_latency_ms" > "$RAW_CSV"

# INFO cpu(used_cpu_user 누적값)와 INFO commandstats(usec_per_call)를 스텝 전후로
# 찍어 "이벤트 루프가 실제로 포화됐는가"를 결과 수치 아닌 서버 자체 계측으로도
# 뒷받침한다. CONFIG RESETSTAT은 commandstats/keyspace 통계만 초기화하고
# used_cpu_user(getrusage 누적치)는 건드리지 않으므로, 전후 델타가 그 스텝
# 동안 redis-server가 실제로 소비한 CPU 시간이다. runner_cpu_before/after는
# /proc/stat의 집계 cpu 라인(공백 구분, 콤마 없음 — CSV 필드로 그대로 안전)을
# 그대로 담아 python 조립 단계에서 유휴시간 비율로 변환한다.
INSTR_CSV="$OUT/raw/instrumentation.csv"
echo "concurrency,rep,wall_start,wall_end,cpu_user_before,cpu_user_after,set_usec_per_call,get_usec_per_call,runner_cpu_before,runner_cpu_after" > "$INSTR_CSV"

read_proc_stat_cpu() {
  grep '^cpu ' /proc/stat
}

for concurrency in "${CONCURRENCY_SWEEP[@]}"; do
  for rep in $(seq 1 "$REPEATS"); do
    echo "concurrency=$concurrency rep=$rep/$REPEATS 실행 중..." >&2
    redis-cli -h redis CONFIG RESETSTAT >/dev/null

    cpu_before="$(redis-cli -h redis INFO cpu | tr -d '\r' | sed -n 's/^used_cpu_user:\(.*\)$/\1/p')"
    runner_cpu_before="$(read_proc_stat_cpu)"
    wall_start="$(date +%s.%N)"

    redis-benchmark -h redis -t set,get -n "$REQUESTS_PER_STEP" -c "$concurrency" --csv \
      | tail -n +2 \
      | sed "s/^/${concurrency},${rep},/" \
      >> "$RAW_CSV"

    wall_end="$(date +%s.%N)"
    cpu_after="$(redis-cli -h redis INFO cpu | tr -d '\r' | sed -n 's/^used_cpu_user:\(.*\)$/\1/p')"
    runner_cpu_after="$(read_proc_stat_cpu)"
    commandstats="$(redis-cli -h redis INFO commandstats | tr -d '\r')"
    set_usec="$(echo "$commandstats" | sed -n 's/^cmdstat_set:.*usec_per_call=\([0-9.]*\).*/\1/p')"
    get_usec="$(echo "$commandstats" | sed -n 's/^cmdstat_get:.*usec_per_call=\([0-9.]*\).*/\1/p')"

    echo "$concurrency,$rep,$wall_start,$wall_end,$cpu_before,$cpu_after,${set_usec:-0},${get_usec:-0},${runner_cpu_before},${runner_cpu_after}" >> "$INSTR_CSV"
  done
done

FINISHED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
ARCH="$(uname -m)"
CPU_CORES="$(nproc)"
MEMORY_GB="$(awk '/MemTotal/ {printf "%.1f", $2/1024/1024}' /proc/meminfo)"

export RAW_CSV INSTR_CSV OUT RUN_ID STARTED_AT FINISHED_AT ARCH CPU_CORES MEMORY_GB REQUESTS_PER_STEP SLA_MULTIPLIER REPEATS

python3 <<'PYEOF'
import csv
import json
import os
import statistics

raw_csv = os.environ["RAW_CSV"]
instr_csv = os.environ["INSTR_CSV"]
out_dir = os.environ["OUT"]

with open(raw_csv) as f:
    rows = list(csv.reader(f))
rows = rows[1:]  # 우리가 직접 쓴 헤더 한 줄 제외

# concurrency -> test(SET/GET) -> [(rps, p99), ...] (반복마다 하나씩)
samples: dict[int, dict[str, list[tuple[float, float]]]] = {}
for concurrency_str, rep, test, rps, avg, mn, p50, p95, p99, mx in rows:
    concurrency = int(concurrency_str)
    samples.setdefault(concurrency, {}).setdefault(test, []).append((float(rps), float(p99)))

data = []
set_p99_by_concurrency = {}
for concurrency in sorted(samples):
    for test in sorted(samples[concurrency]):
        pts = samples[concurrency][test]
        rps_vals = [p[0] for p in pts]
        p99_vals = [p[1] for p in pts]
        rps_median = statistics.median(rps_vals)
        p99_median = statistics.median(p99_vals)
        n = len(pts)
        note_rps = f"{n}회 반복 중앙값 (범위 {min(rps_vals):.1f}~{max(rps_vals):.1f} ops/sec)" if n > 1 else None
        note_p99 = f"{n}회 반복 중앙값 (범위 {min(p99_vals):.3f}~{max(p99_vals):.3f} ms)" if n > 1 else None
        data.append({
            "metric": "throughput_ops_sec", "series": test, "x_label": "concurrency",
            "x": concurrency, "y": round(rps_median, 1), "unit": "ops/sec", "note": note_rps,
        })
        data.append({
            "metric": "p99_latency_ms", "series": test, "x_label": "concurrency",
            "x": concurrency, "y": round(p99_median, 3), "unit": "ms", "note": note_p99,
        })
        if test == "SET":
            set_p99_by_concurrency[concurrency] = p99_median

concurrency_sweep = sorted(set_p99_by_concurrency)
baseline_p99 = set_p99_by_concurrency[concurrency_sweep[0]] if concurrency_sweep else None
sla_multiplier = float(os.environ["SLA_MULTIPLIER"])

threshold = None
if baseline_p99 is not None:
    for c in concurrency_sweep:
        if set_p99_by_concurrency[c] > baseline_p99 * sla_multiplier:
            threshold = c
            break

# redis-server 자체 계측(INFO cpu / INFO commandstats)으로 "이벤트 루프 포화" 가설을
# 클라이언트 관측 레이턴시가 아닌 서버 쪽 증거로도 뒷받침한다. runner_cpu는 같은
# 방식으로 부하를 쏘는 컨테이너 자체가 바빴는지를 본다 — /proc/stat 집계 cpu 라인의
# (user+nice+system+idle+iowait+irq+softirq+steal) 델타 대비 유휴(idle+iowait)
# 델타 비율로 사용률을 구한다(표준 top/vmstat 계산과 동일한 방식).
with open(instr_csv) as f:
    instr_rows = list(csv.reader(f))
instr_rows = instr_rows[1:]


def _proc_stat_fields(line: str) -> list[int]:
    # "cpu  <user> <nice> <system> <idle> <iowait> <irq> <softirq> <steal> ..."
    return [int(v) for v in line.split()[1:9]]


instr_samples: dict[int, list[dict[str, float]]] = {}
for concurrency_str, rep, wall_start, wall_end, cpu_before, cpu_after, set_usec, get_usec, runner_before, runner_after in instr_rows:
    concurrency = int(concurrency_str)
    wall = float(wall_end) - float(wall_start)
    cpu_delta = float(cpu_after) - float(cpu_before)
    redis_cpu_pct = round(100 * cpu_delta / wall, 1) if wall > 0 else 0.0

    before_fields = _proc_stat_fields(runner_before)
    after_fields = _proc_stat_fields(runner_after)
    before_idle = before_fields[3] + before_fields[4]
    after_idle = after_fields[3] + after_fields[4]
    total_delta = sum(after_fields) - sum(before_fields)
    idle_delta = after_idle - before_idle
    runner_cpu_pct = round(100 * (1 - idle_delta / total_delta), 1) if total_delta > 0 else 0.0

    instr_samples.setdefault(concurrency, []).append({
        "redis_cpu_pct": redis_cpu_pct,
        "set_usec": float(set_usec),
        "get_usec": float(get_usec),
        "runner_cpu_pct": runner_cpu_pct,
    })

cpu_pct_by_concurrency = {}
runner_cpu_pct_by_concurrency = {}
for concurrency in sorted(instr_samples):
    reps = instr_samples[concurrency]
    n = len(reps)
    redis_cpu_vals = [r["redis_cpu_pct"] for r in reps]
    set_usec_vals = [r["set_usec"] for r in reps]
    get_usec_vals = [r["get_usec"] for r in reps]
    runner_cpu_vals = [r["runner_cpu_pct"] for r in reps]

    redis_cpu_median = statistics.median(redis_cpu_vals)
    runner_cpu_median = statistics.median(runner_cpu_vals)
    cpu_pct_by_concurrency[concurrency] = redis_cpu_median
    runner_cpu_pct_by_concurrency[concurrency] = runner_cpu_median

    note = lambda vals, fmt: (f"{n}회 반복 중앙값 (범위 {min(vals):{fmt}}~{max(vals):{fmt}})" if n > 1 else None)

    data.append({
        "metric": "redis_cpu_utilization_pct", "series": None, "x_label": "concurrency",
        "x": concurrency, "y": round(redis_cpu_median, 1), "unit": "%",
        "note": note(redis_cpu_vals, ".1f"),
    })
    data.append({
        "metric": "usec_per_call", "series": "SET", "x_label": "concurrency",
        "x": concurrency, "y": round(statistics.median(set_usec_vals), 2), "unit": "usec",
        "note": note(set_usec_vals, ".2f"),
    })
    data.append({
        "metric": "usec_per_call", "series": "GET", "x_label": "concurrency",
        "x": concurrency, "y": round(statistics.median(get_usec_vals), 2), "unit": "usec",
        "note": note(get_usec_vals, ".2f"),
    })
    data.append({
        "metric": "runner_cpu_utilization_pct", "series": None, "x_label": "concurrency",
        "x": concurrency, "y": round(runner_cpu_median, 1), "unit": "%",
        "note": note(runner_cpu_vals, ".1f"),
    })

cpu_utilization_at_threshold = cpu_pct_by_concurrency.get(threshold) if threshold is not None else None
runner_cpu_utilization_at_threshold = runner_cpu_pct_by_concurrency.get(threshold) if threshold is not None else None

results = {
    "schema_version": "1.0",
    "experiment": {
        "id": "redis-blocking-threshold",
        "agenda": "Redis 단일 인스턴스는 초당 몇 건의 SET/GET 요청부터 P99 레이턴시가 급격히(10배 이상) 튀며 이벤트 루프가 포화 상태에 진입하는가?",
        "template": "redis-blocking-threshold",
        "template_version": "1.1.0",
    },
    "run": {
        "run_id": os.environ["RUN_ID"],
        "started_at": os.environ["STARTED_AT"],
        "finished_at": os.environ["FINISHED_AT"],
        "smoke": os.environ["SMOKE"] == "true",
        "environment": {
            "arch": os.environ["ARCH"],
            "cpu_cores": int(os.environ["CPU_CORES"]),
            "memory_gb": float(os.environ["MEMORY_GB"]),
        },
    },
    "parameters": {
        "concurrency_sweep": concurrency_sweep,
        "requests_per_step": int(os.environ["REQUESTS_PER_STEP"]),
        "sla_multiplier": sla_multiplier,
        "repeats": int(os.environ["REPEATS"]),
    },
    "data": data,
    "summary": {
        "blocking_threshold_concurrency": threshold,
        "baseline_p99_ms": round(baseline_p99, 3) if baseline_p99 is not None else None,
        "redis_cpu_utilization_pct_at_threshold": cpu_utilization_at_threshold,
        "runner_cpu_utilization_pct_at_threshold": runner_cpu_utilization_at_threshold,
    },
    "status": "success",
    "notes": [],
}

out_path = os.path.join(out_dir, "results.json")
with open(out_path, "w") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
    f.write("\n")

print(f"wrote {out_path}")
PYEOF
