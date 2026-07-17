# redis-blocking-threshold

Redis 단일 인스턴스(`redis:7-alpine`, `--maxmemory-policy noeviction`, `cpus: 2` 제한)에
`redis-benchmark -t set,get --csv`로 concurrency를 스윕하며 부하를 걸어, P99
레이턴시가 baseline 대비 `sla_multiplier`(기본 10배)를 넘는 지점을 찾는다.

## 기술 스택 / 전제조건
- `redis:7-alpine` (공식 멀티아치 이미지, linux/amd64·linux/arm64)
- Debian `redis-tools` 패키지의 `redis-benchmark`/`redis-cli` (옆의 `Dockerfile`이 설치)
- 별도 클라이언트 도구 없음 (memtier_benchmark 등은 도입하지 않음 — YAGNI)

## 파라미터 (`params.yml`)
- `concurrency_sweep`: 스윕할 동시 연결 수 목록
- `requests_per_step`: 각 concurrency에서 보낼 요청 수 (SET/GET 각각)
- `sla_multiplier`: baseline(최소 concurrency) P99 대비 몇 배를 임계값으로 볼지

각 concurrency 스텝은 스모크 1회 / 실전 3회(`REPEATS`, 스크립트에 고정) 반복해
중앙값을 쓴다 — 단일 샘플로는 노이즈와 실제 신호를 구분할 수 없다.

## 산출물
- `data[]`: metric `throughput_ops_sec`/`p99_latency_ms` × series `SET`/`GET` —
  값은 반복 실행의 중앙값. 반복 횟수가 1보다 크면 `note`에 범위(min~max)가 남는다.
- `data[]`: metric `redis_cpu_utilization_pct` (series 없음) — 각 concurrency 스텝
  동안 `INFO cpu`의 `used_cpu_user` 누적치 델타를 스텝 wall-clock 시간으로 나눈 값.
  redis-server 프로세스가 그 구간에서 실제로 CPU를 얼마나 썼는지를 나타낸다.
- `data[]`: metric `usec_per_call` × series `SET`/`GET` — `INFO commandstats`의
  `usec_per_call`(스텝마다 `CONFIG RESETSTAT`으로 초기화 후 측정). 서버가 명령 하나
  처리하는 데 실제로 걸린 시간 — 클라이언트가 관측하는 P99(대기 시간 포함)와 대조군.
- `data[]`: metric `runner_cpu_utilization_pct` (series 없음) — 부하를 쏘는 `runner`
  컨테이너 자체의 `/proc/stat` 집계 cpu 라인 델타로 구한 CPU 사용률. "느려진 게
  redis-server가 아니라 클라이언트(부하 생성 쪽)가 바빠서일 수도 있다"는 가능성을
  같은 실행에서 직접 확인하기 위한 대조군.
- `summary.blocking_threshold_concurrency`: SET P99가 baseline의 `sla_multiplier`배를
  처음 넘는 concurrency (없으면 `null`)
- `summary.baseline_p99_ms`: 최소 concurrency에서의 SET P99
- `summary.redis_cpu_utilization_pct_at_threshold`: 임계 concurrency에서의
  `redis_cpu_utilization_pct` — "이벤트 루프가 CPU 포화 상태였는가"에 대한 직접 증거
- `summary.runner_cpu_utilization_pct_at_threshold`: 임계 concurrency에서의
  `runner_cpu_utilization_pct` — 클라이언트 쪽이 병목이었는지에 대한 직접 증거

## 결론 서술의 한계
컨테이너/VM 환경에서 P99 급증은 Redis 이벤트 루프 외에도 benchmark 클라이언트 자체,
Docker Desktop VM, CPU 스케줄링의 영향일 수 있다. `redis_cpu_utilization_pct`·
`usec_per_call`·`runner_cpu_utilization_pct`가 모두 낮게 유지된다면(예: 첫 실행에서
실제로 그랬다 — 서버 CPU 10%대, usec_per_call 0.3~0.5 수준 고정), "이벤트 루프 CPU
포화"도 "클라이언트 과부하"도 원인이 아니라는 뜻이다 — 결론은 그 증거를 있는 그대로
반영해야 한다(CONTRACT.md 문서 신뢰성 규칙 참고). 단정하기 전에 항상 이 세 계측을
함께 인용한다.
