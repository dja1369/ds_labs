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

## 산출물
- `data[]`: metric `throughput_ops_sec`/`p99_latency_ms` × series `SET`/`GET`
- `summary.blocking_threshold_concurrency`: SET P99가 baseline의 `sla_multiplier`배를
  처음 넘는 concurrency (없으면 `null`)
- `summary.baseline_p99_ms`: 최소 concurrency에서의 SET P99

## 결론 서술의 한계
컨테이너/VM 환경에서 P99 급증은 Redis 이벤트 루프 외에도 benchmark 클라이언트 자체,
Docker Desktop VM, CPU 스케줄링의 영향일 수 있다. 결론은 "이 환경에서 관측된 지연
임계치"로 한정해 서술한다 — "이벤트 루프 포화가 원인"이라고 단정하려면
`INFO commandstats` 등 보조 증거가 필요하다(CONTRACT.md 문서 신뢰성 규칙 참고).
