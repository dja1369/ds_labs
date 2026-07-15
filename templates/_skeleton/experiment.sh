#!/usr/bin/env bash
set -euo pipefail

# templates/_skeleton의 더미 실행 로직. 실제 인프라를 구동하지 않고 하드코딩된
# results.json을 출력한다 — 3대 계약(실행 진입점/스키마/문서)이 끝까지 동작하는지
# 증명하는 walking skeleton 용도다. 새 템플릿을 만들 때는 이 파일 전체를 실제
# 측정 로직으로 교체한다 (TODO).

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

mkdir -p "$OUT"

STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
RUN_ID="$(date -u +%Y-%m-%dT%H-%M-%SZ)-$(head -c4 /dev/urandom | od -An -tx1 | tr -d ' \n')"
ARCH="$(uname -m)"
CPU_CORES="$(nproc)"
MEMORY_GB="$(awk '/MemTotal/ {printf "%.1f", $2/1024/1024}' /proc/meminfo)"
FINISHED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

cat > "$OUT/results.json" <<JSON
{
  "schema_version": "1.0",
  "experiment": {
    "id": "skeleton-dummy",
    "agenda": "이 템플릿(_skeleton)이 3대 계약을 만족하는 더미 결과를 만들 수 있는가?",
    "template": "_skeleton",
    "template_version": "0.1.0"
  },
  "run": {
    "run_id": "${RUN_ID}",
    "started_at": "${STARTED_AT}",
    "finished_at": "${FINISHED_AT}",
    "duration_sec": 0,
    "smoke": ${SMOKE},
    "environment": { "arch": "${ARCH}", "cpu_cores": ${CPU_CORES}, "memory_gb": ${MEMORY_GB} }
  },
  "parameters": {},
  "data": [
    { "metric": "dummy_metric", "series": null, "x_label": "step", "x": 1, "y": 1.0, "unit": "unit", "note": null },
    { "metric": "dummy_metric", "series": null, "x_label": "step", "x": 2, "y": 2.0, "unit": "unit", "note": null }
  ],
  "summary": {},
  "status": "success",
  "notes": ["templates/_skeleton의 더미 출력 — 실제 실험 로직으로 교체하세요 (TODO)"]
}
JSON

echo "wrote ${OUT}/results.json"
