---
layout: post
title: Redis에 요청을 얼마나 넣으면 터질까?
date: 2026-07-15 09:34:09 +0000
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
run_id: 2026-07-15T09-34-09Z-a26cef48
---

## 안건
Redis에 요청을 얼마나 넣으면 죽을까?

## 가설
Redis는 단일 스레드 이벤트 루프이므로, concurrency가 baseline(최소 concurrency)
대비 P99 10배 임계값을 넘는 지점부터 이벤트 루프가 포화되어 처리량은 정체되고
지연시간이 급증할 것이다.

## 요약
- 동시 연결 250개부터 심상치 않다.
- concurrency(동시 요청) 1일 때 SET P99(요청 99%가 처리되는 시간 — 사실상
  최악에 가까운 케이스)는 0.071ms인데, 250에서 1.599ms로 약 22.5배 뛴다.
- 근데 가설과 실제는 달랐다.
- redis-server CPU 사용률은 임계점(250)에서도 10.9%밖에 안 됐고, concurrency가
  늘수록 오히려 더 떨어졌다(4000에서 3.5%).
- 즉 서버는 안 바빴고, 진짜 병목은 따로 있었다는 것이다..!

## 구성
- `redis:7-alpine`, `--maxmemory-policy noeviction`, `cpus: 2` 제한 (docker compose)
- `runner`: 공용 이미지(`ds-labs/runner:1.0.0`)를 `redis-tools`로 확장
- 부하 도구: Debian `redis-tools` 패키지의 `redis-benchmark`
- 부하 조건: concurrency `[1, 10, 50, 100, 250, 500, 1000, 2000, 4000]` 9단계 스윕,
  스텝당 SET/GET 각 100,000 요청
- 실행 환경(컨테이너 내부 관측치): `aarch64`, 2 core, 3.8GB

## 방법

1. 스펙대로 Redis를 띄운다.
   ```
   docker compose -f templates/redis-blocking-threshold/docker-compose.yml up -d redis
   ```

2. concurrency를 1부터 4000까지 9단계로 올려가며 SET/GET을 순서대로 때린다.
   ```
   redis-benchmark -h redis -t set,get -n 100000 -c <concurrency> --csv
   ```

3. "느려진 게 진짜 서버가 바빠서인가?"를 직접 확인하려고, 각 스텝 전후로
   redis-server 자체 계측도 같이 찍는다.
   ```
   redis-cli -h redis CONFIG RESETSTAT
   redis-cli -h redis INFO cpu           # used_cpu_user 델타 → 그 스텝의 CPU 사용률
   redis-cli -h redis INFO commandstats  # usec_per_call → 명령 하나 처리 시간
   ```
   클라이언트가 보는 P99(대기 시간 포함)와 서버가 실제로 쓴 처리 시간을 나란히
   놓고 비교하는 게 핵심이다.

4. 스윕이 끝나면 raw CSV를 `results.json`으로 조립하고 스키마 검증 → 차트 생성까지
   한 번에 돌린다.
   ```
   docker compose -f templates/redis-blocking-threshold/docker-compose.yml run --rm runner \
     ./experiment.sh --params params.yml --out results
   ```

## 결과

| concurrency | SET P99 (ms) | GET P99 (ms) | SET 처리량 (ops/sec) | GET 처리량 (ops/sec) |
|---|---|---|---|---|
| 1    | 0.071  | 0.071  | 21,725  | 21,739  |
| 10   | 0.095  | 0.087  | 194,553 | 210,971 |
| 50   | 0.383  | 0.335  | 196,464 | 201,207 |
| 100  | 0.487  | 0.447  | 191,939 | 182,815 |
| **250**  | **1.599**  | 1.367  | 158,228 | 161,031 |
| 500  | 3.335  | 3.439  | 146,628 | 144,928 |
| 1000 | 5.151  | 7.807  | 132,626 | 130,548 |
| 2000 | 13.239 | 18.015 | 128,370 | 129,199 |
| 4000 | 47.103 | 20.047 | 125,000 | 131,926 |

(전체 원시 수치는 [`results/results.json`](results/results.json) 참고.)

## 발견 사항 및 분석

### 성능 및 일반적인 사례
baseline(기준값 — 여기선 `concurrency=1`일 때 수치)의 SET P99는 0.071ms.

`250`에서 1.599ms — 약 22.5배로 "baseline 10배" 선을 처음 넘는다
(`summary.blocking_threshold_concurrency = 250`).

여기까진 뻔한 그림이다: 처리량은 `10~50` 구간에서 정점(SET 196,464 ops/sec @50,
GET 210,971 ops/sec @10) 찍고 완만히 내려가고, P99는 `250`부터 계단 뛰듯
오른다(`500`→3.3ms, `1000`→5~8ms, `2000`→13~18ms).

![throughput_ops_sec]({{ '/assets/images/2026-07-15-redis-blocking-threshold/throughput_ops_sec.png' | relative_url }})
![p99_latency_ms]({{ '/assets/images/2026-07-15-redis-blocking-threshold/p99_latency_ms.png' | relative_url }})

근데 `4000`에서 갈라진다 — SET P99가 47.1ms인데 GET은 20.0ms, 2배 넘게 벌어진다.

`250`까지는 SET/GET이 거의 붙어 다녔는데 극단적으로 몰리니까 쓰기가 먼저
무너진다.

흔한 "요청 몰리면 터진다" 얘기로 끝날 스토리가 아니라는 신호다.

### 추가로 알면 좋을 사항
여기서부터가 진짜다 — redis-server 자체는 이 구간 내내 안 바빴다.

| concurrency | redis-server CPU 사용률 | SET usec_per_call | GET usec_per_call |
|---|---|---|---|
| 1    | 7.6%  | 0.75 | 0.53 |
| 10   | 19.4% | 0.31 | 0.25 |
| 50   | 16.7% | 0.30 | 0.27 |
| 100  | 14.5% | 0.33 | 0.28 |
| 250  | 10.9% | 0.38 | 0.32 |
| 500  | 8.6%  | 0.40 | 0.35 |
| 1000 | 6.7%  | 0.44 | 0.38 |
| 2000 | 5.6%  | 0.46 | 0.39 |
| 4000 | 3.5%  | 0.48 | 0.37 |

![redis_cpu_utilization_pct]({{ '/assets/images/2026-07-15-redis-blocking-threshold/redis_cpu_utilization_pct.png' | relative_url }})
![usec_per_call]({{ '/assets/images/2026-07-15-redis-blocking-threshold/usec_per_call.png' | relative_url }})

임계점(250)에서 CPU 사용률 10.9%.

그리고 concurrency를 더 올릴수록 CPU 사용률은 더 떨어진다(10에서 19.4% →
4000에서 3.5%) — 부하를 더 줬는데 서버는 더 한가해 보이는, 직관에 반하는
그래프다.

`usec_per_call`(명령 하나 처리하는 데 서버가 실제로 쓴 시간)도 P99가 47ms까지
튀는 동안 0.25~0.75usec 사이에서 꿈쩍 안 했다.

이벤트 루프(Redis가 요청을 한 번에 하나씩 순서대로 처리하는 구조)가 CPU 못
따라가서 밀린 거라면 이 숫자가 같이 튀어야 정상인데, 안 튀었다.

즉 병목은 redis-server의 명령 처리 경로 안이 아니라 그 바깥(연결을 맺고
큐에 쌓고 스케줄링하는 어딘가)에 있다는 뜻이다.

## 결론

- **가설 중 맞은 부분**: concurrency 250부터 P99가 baseline 10배를 넘고,
  그 뒤로도 계속 커질수록 더 크게 뛴다.
- **가설 중 틀린 부분**: "이벤트 루프가 CPU 포화돼서 그렇다"는 핵심 설명은
  데이터가 반박한다. redis-server CPU 사용률은 임계점에서도 10.9%, 명령 처리
  시간(usec_per_call)도 끝까지 0.25~0.75usec로 거의 고정이었다 — 서버는
  "바빠서" 못 받아준 게 아니다.
- **아직 모르는 것**: 그럼 P99는 왜 뛰었나. CPU가 아니라면 연결 수준 큐잉,
  `redis-benchmark` 클라이언트 자체 부하, Docker Desktop VM 네트워크 스택이
  후보로 남는다. 이번 실험 범위 밖이라 단정하지 않고 다음 연구 과제로 넘긴다.

## 연관 연구 주제 제안

- CPU가 원인이 아니라면 P99 급증의 진짜 원인은 뭘까? 연결할 때 큐잉이
  문제일까 — 서버는 안 바쁜데 요청/응답이 느려진다면 보내고 받는 쪽이 의심된다.
- `concurrency=4000`에서 SET이 GET보다 2배 넘게 느려지는 것도 이상하다 —
  쓰기 경로에만 있는 비용이 큐잉과 겹쳐 증폭되는 걸까?
- 코어를 1개에서 8개로 늘리면 단일 스레드 Redis와 멀티스레드 Memcached는
  얼마나 다르게 스케일링될까?
- 메모리가 커질수록 BGSAVE의 Copy-on-Write가 만드는 레이턴시 스파이크는
  얼마나 커질까?
