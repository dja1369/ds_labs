---
layout: post
title: Redis 단일 인스턴스는 초당 몇 건의 SET/GET 요청부터 P99 레이턴시가 급격히 튀는가?
date: 2026-07-15 08:53:31 +0000
categories:
- redis
- performance
- docker
tags:
- redis
- performance
- docker
experiment_id: redis-blocking-threshold
experiment_url: https://github.com/dja1369/ds_labs/tree/main/experiments/2026-07-15-redis-blocking-threshold
run_id: 2026-07-15T08-53-31Z-84a6e394
---

## 안건
Redis 단일 인스턴스는 초당 몇 건의 SET/GET 요청부터 P99 레이턴시가 급격히(10배
이상) 튀며 이벤트 루프가 포화 상태에 진입하는가?

## 가설
Redis는 단일 스레드 이벤트 루프이므로, concurrency가 baseline(최소 concurrency)
대비 P99 10배 임계값을 넘는 지점부터 이벤트 루프가 포화되어 처리량은 정체되고
지연시간이 급증할 것이다.

## 구성
- `redis:7-alpine`, `--maxmemory-policy noeviction`, `cpus: 2` 제한 (docker compose)
- `runner`: 공용 이미지(`ds-labs/runner:1.0.0`)를 `redis-tools`로 확장
- 부하 도구: Debian `redis-tools` 패키지의 `redis-benchmark`

## 방법
`redis-benchmark -h redis -t set,get -n 100000 -c <concurrency> --csv`를
`concurrency_sweep: [1, 10, 50, 100, 250, 500, 1000, 2000, 4000]` 각 값에 대해
순차 실행하고, `--csv` 출력의 `rps`/`p99_latency_ms` 컬럼을 수집했다.
`baseline_p99`(concurrency=1의 SET P99) 대비 `sla_multiplier`(10배)를 처음
넘는 concurrency를 임계값으로 정의했다.

## 결과

baseline(`concurrency=1`)의 SET P99는 **0.071ms**였고, `concurrency=250`에서
SET P99가 **1.439ms**로 baseline 대비 약 20배를 기록해 임계값(10배, 0.71ms)을
넘었다 — `summary.blocking_threshold_concurrency = 250`.

| concurrency | SET P99 (ms) | GET P99 (ms) | SET 처리량 (ops/sec) |
|---|---|---|---|
| 1    | 0.071 | 0.119 | 21,739  |
| 10   | 0.087 | 0.079 | 212,766 |
| 50   | 0.551 | 0.279 | 203,666 |
| 100  | 0.495 | 0.687 | 186,916 |
| 250  | 1.439 | 1.495 | 176,679 |
| 500  | 7.999 | 5.503 | 144,092 |
| 1000 | 8.879 | 8.031 | 134,771 |
| 2000 | 21.231 | 20.223 | 126,263 |
| 4000 | 29.599 | 22.751 | 128,370 |

(전체 원시 수치는 [`results/results.json`](results/results.json) 참고.)

![throughput_ops_sec]({{ '/assets/images/2026-07-15-redis-blocking-threshold/throughput_ops_sec.png' | relative_url }})
![p99_latency_ms]({{ '/assets/images/2026-07-15-redis-blocking-threshold/p99_latency_ms.png' | relative_url }})

처리량은 `concurrency=10~50` 구간에서 정점(약 203,000~213,000 ops/sec)을 찍은 뒤
`concurrency`가 커질수록 완만히 하락했다. P99 레이턴시는 `concurrency=250`
이전까지는 1ms 미만으로 유지되다가, `250` 이후 구간(`500`, `1000`, `2000`,
`4000`)에서 각각 8ms·9ms·21ms·30ms 수준으로 계단식으로 뛰었다. `concurrency=50`
→`100` 구간에서 SET P99가 0.551ms→0.495ms로 미세하게 감소하는 비단조 구간이
하나 있었다 — 벤치마크 클라이언트/스케줄링 노이즈로 보이며, 전체 추세(급격한
증가)에 영향을 주지 않는다.

## 결론

이 환경(`cpus: 2` 제한, Docker Desktop VM)에서 관측된 지연 임계치는
**concurrency 250 부근**이다. 이 지점부터 P99가 baseline의 10배를 넘고,
이후 concurrency가 2배씩 늘 때마다 P99도 함께 큰 폭으로 뛰는 패턴이 이어졌다.

다만 이 컨테이너/VM 환경에서의 P99 급증을 "Redis 이벤트 루프가 포화됐다"고
단정하지는 않는다 — `redis-benchmark` 클라이언트 자체의 부하, Docker Desktop
VM의 스케줄링, `cpus: 2` CPU 제한의 영향이 섞여 있을 수 있다. 이 결론은
"이 환경에서 관측된 지연 임계치"로 한정한다. 이벤트 루프 포화가 실제 원인인지
확인하려면 `INFO commandstats`나 서버 CPU 사용률 같은 보조 증거가 필요하다
(`TEMPLATE.md` 참고).

## 다음 연구 과제

- 동일한 CPU 코어 제한(1→8 core) 하에서 Redis(단일 스레드)와 Memcached(멀티
  스레드)의 처리량이 코어 수 증가에 따라 각각 어떻게 스케일링되는지 비교
  (`TOPICS.md` 캐시 카테고리 [중급])
- BGSAVE 실행 시점의 메모리 사용량이 커질수록 fork()의 Copy-on-Write로 인한
  레이턴시 스파이크가 얼마나 커지는지 측정 (`TOPICS.md` 캐시 카테고리 [중급])
- 이번 실험에서 단정을 피한 "이벤트 루프 포화" 가설을 `INFO commandstats` +
  서버 CPU 사용률 계측으로 직접 검증
