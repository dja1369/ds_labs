# ds_labs 연구 안건 최종 리스트

여러 도메인 전문가가 제안한 후보 49건을 검토해 의미가 사실상 동일한 3쌍(6건)을 각 1건으로 병합하고, 8개 카테고리로 그룹화한 뒤 카테고리 내에서 난이도(초급→중급→고급) 순으로 정렬했다.

## 요약

- **총 안건 수: 46개** (원 후보 49개 → 중복 3쌍 병합 → 46개)
- **카테고리: 8개**

| # | 카테고리 | 안건 수 | 난이도 분포 (초급/중급/고급) |
|---|---|---|---|
| 1 | 캐시/인메모리 스토어 (Redis, Memcached) | 7 | 3 / 3 / 1 |
| 2 | WAS/애플리케이션 서버 & JVM (Spring Boot, Tomcat, JVM GC) | 5 | 1 / 2 / 2 |
| 3 | 컨테이너 오케스트레이션 (Kubernetes, Docker) | 6 | 2 / 2 / 2 |
| 4 | OLAP/분석 데이터베이스 (ClickHouse) | 6 | 2 / 2 / 2 |
| 5 | RDBMS (PostgreSQL, MySQL) | 6 | 1 / 3 / 2 |
| 6 | 메시지 큐/스트리밍 (Kafka, RabbitMQ) | 6 | 1 / 3 / 2 |
| 7 | 네트워크/동시성 (HTTP, Nginx, TCP) | 4 | 2 / 0 / 2 |
| 8 | 스토리지/파일시스템 (디스크 I/O) | 6 | 2 / 2 / 2 |
| | **합계** | **46** | **14 / 17 / 15** |

### 병합 내역 (중복 제거)

동일한 실험을 서로 다른 문구로 제안한 것으로 판단해 병합한 3쌍:

1. **Tomcat 스레드풀 튜닝** — WAS/JVM의 "Tomcat 스레드 풀 튜닝"(순수 포화 시나리오)과 네트워크/동시성의 "애플리케이션 스레드풀(Tomcat)"(느린 백엔드 포함 시나리오)을 병합. 더 현실적인 후자의 시나리오(느린 백엔드 + 컨텍스트 스위칭 오버헤드)를 채택해 WAS/JVM 카테고리에 배치.
2. **HikariCP 커넥션 풀 포화** — WAS/JVM의 "DB 커넥션 풀(HikariCP) 포화"와 네트워크/동시성의 "DB 커넥션 풀(HikariCP)"을 병합. 두 질문("pool exhaustion 타임아웃 시점"과 "대기시간이 응답시간의 절반을 넘는 시점")을 하나로 통합해 WAS/JVM 카테고리에 배치.
3. **컨테이너 메모리 제한 vs JVM 힙/OOMKilled** — WAS/JVM의 "컨테이너 메모리 제한과 JVM 힙"과 오케스트레이션의 "메모리 제한과 OOM Kill"을 병합. cgroup 메모리 제한이 핵심 변수이므로 오케스트레이션 카테고리에 배치.

---

## 1. 캐시/인메모리 스토어 (Redis, Memcached)

- **[초급] Redis 단일 인스턴스는 초당 몇 건의 SET/GET 요청부터 P99 레이턴시가 급격히(예: 10배 이상) 튀며 이벤트 루프가 포화 상태에 진입하는가?** — Redis는 명령 처리가 단일 스레드라 진짜 병목이 CPU인지 네트워크 I/O인지 실무자들이 항상 헷갈려하는 지점이라 명확한 임계치 데이터가 용량 산정에 바로 쓰인다. (필요 스택: Docker(redis:7-alpine, cpuset/cpus 제한), memtier_benchmark/redis-benchmark, redis_exporter + Prometheus + Grafana)
- **[초급] AOF appendfsync 정책을 always/everysec/no로 바꿀 때 쓰기 처리량(ops/sec)은 몇 배 차이가 나며, 그 대가로 장애 시 유실 가능한 데이터 윈도우는 각각 얼마인가?** — 내구성과 처리량을 맞바꾸는 이 설정 하나가 장애 시 데이터 유실 범위를 결정하는데도 수치 근거 없이 기본값을 그대로 쓰는 경우가 많다. (필요 스택: Docker(redis:7, 볼륨 바인드), redis-benchmark(-t set), fio, docker stats)
- **[초급] 단일 Key의 Value 크기(1KB→10MB, Hash/List 원소 수 증가 포함)가 커질수록 DEL/EXPIRE 같은 O(N) 명령이 이벤트 루프를 얼마나 오래 블로킹시키는가?** — 빅키 문제는 Redis 장애의 단골 원인이지만 '몇 MB부터 위험한지'에 대한 감각적 답변만 있을 뿐 실측 곡선을 본 사람은 적다. (필요 스택: Docker(redis:7), Python(redis-py) 생성 스크립트, redis-cli --latency-history, UNLINK 비교)
- **[중급] BGSAVE 실행 시점의 메모리 사용량(1GB→8GB)이 커질수록 fork()의 Copy-on-Write로 인한 레이턴시 스파이크와 지속 시간은 얼마나 커지는가?** — fork 지연으로 인한 순간적 전체 요청 정지는 실제 장애 포스트모템에 자주 등장하는 원인인데도 메모리 크기별 정량 데이터를 직접 뽑아본 엔지니어는 드물다. (필요 스택: Docker(redis:7, mem_limit 단계별), redis-cli 더미 데이터 스크립트, redis-benchmark, LATENCY HISTORY fork + Grafana)
- **[중급] 동일한 CPU 코어 제한(1→8 core) 하에서 Redis(단일 스레드)와 Memcached(멀티 스레드)는 순수 GET/SET 워크로드의 처리량이 코어 수 증가에 따라 각각 어떻게 스케일링되는가?** — 코어를 늘려도 안 늘어나는 Redis vs 선형에 가깝게 늘어나는 Memcached라는 통념을 실제 컨테이너 환경에서 곡선으로 검증하면 캐시 스토어 선택 기준이 명확해진다. (필요 스택: Docker(redis:7, memcached:1.6, --cpus 조정), memtier_benchmark, docker stats)
- **[중급] maxmemory-policy를 allkeys-lru/allkeys-lfu/volatile-ttl로 바꿀 때, Zipfian(멱함수) 키 접근 분포 워크로드에서 캐시 히트율은 정책별로 얼마나 차이가 나는가?** — 실무 트래픽은 균등분포가 아니라 소수 핫키에 몰리는데, 이런 조건에서 LRU와 LFU의 히트율 차이를 직접 측정해본 자료는 의외로 드물다. (필요 스택: Docker(redis:7, maxmemory 고정), memtier_benchmark/Zipfian 로드제너레이터, INFO stats keyspace_hits/misses)
- **[고급] Redis Primary-Replica 구성에서 쓰기 처리량(ops/sec)이 증가할수록 복제 지연(master_repl_offset과 slave_repl_offset의 차이)은 어느 시점부터 선형이 아닌 급격한 증가로 전환되는가?** — 복제 지연은 Replica에서 읽기 시 read-after-write 일관성이 깨지는 직접적 원인인데, 어느 쓰기 부하부터 위험 구간에 들어가는지는 서비스 SLA 설계에 바로 반영되는 실용적 수치다. (필요 스택: Docker Compose(primary+replica 2개, REPLICAOF), redis-benchmark, INFO replication 폴링 + Grafana)

## 2. WAS/애플리케이션 서버 & JVM (Spring Boot, Tomcat, JVM GC)

- **[초급] JVM 기동 직후부터 몇 건의 요청을 처리해야 JIT 컴파일이 안정화되어 steady-state 처리량(RPS)의 95% 수준에 도달하는가?** — 오토스케일링/카나리 배포 시 신규 파드가 콜드 상태로 트래픽을 받으면 지연이 튀는데, 웜업 구간 길이를 정량화하면 트래픽 램프업 전략 설계에 바로 활용 가능하다. (필요 스택: Docker(Spring Boot 앱), k6 constant-arrival-rate, async-profiler/JFR)
- **[중급] 느린 백엔드 호출(예: 300ms 지연)이 섞인 워크로드에서 Spring Boot 내장 Tomcat의 server.tomcat.threads.max를 10~400까지 늘려갈 때, 처리량(RPS)이 포화되고 컨텍스트 스위칭 오버헤드로 오히려 P99 응답 지연이 급증하기 시작하는 스레드 수는 몇 개인가?** — 실무에서 가장 흔히 임의로 조정되는 파라미터임에도 thread-per-request 모델의 포화 임계치를 실측한 자료가 드물다. '스레드 풀은 클수록 좋다'는 통념이 언제부터 역효과를 내는지도 함께 검증한다. *(중복 병합)* (필요 스택: Docker Compose(Spring Boot 앱 + WireMock 느린 백엔드), k6/wrk2, Micrometer+Prometheus+Grafana)
- **[중급] HikariCP 최대 풀 크기가 DB 서버의 실제 동시 처리 능력을 초과할 때, 초당 요청 수가 얼마를 넘으면 커넥션 대기 시간이 전체 응답 시간의 절반을 넘고 결국 pool exhaustion 타임아웃까지 발생하기 시작하는가?** — '커넥션 풀 크기는 CPU 코어 수 x 2+1' 같은 통설로 정해지는 경우가 많아 실측으로 검증·반박할 가치가 크다. *(중복 병합)* (필요 스택: Docker Compose(Spring Boot 앱 + PostgreSQL), HikariCP 풀 크기 파라미터화, k6, Micrometer HikariCP 메트릭 + Grafana)
- **[고급] 동일한 -Xmx 힙 크기와 부하 조건에서 G1GC, Parallel GC, ZGC 중 어떤 GC가 P99 응답 지연을 가장 낮게 유지하며, 힙이 몇 GB 이상일 때 그 우위가 역전되는가?** — GC 선택은 서비스 SLA(P99/P999)에 직접 영향을 주지만 관행적으로 선택되는 경우가 많고 실측 기반 비교 자료가 부족하다. (필요 스택: Docker(GC 옵션별 앱 3개), JFR/gc log + GCEasy, k6, Grafana)
- **[고급] Spring Boot 3.2+ 환경에서 요청 처리 중 블로킹 I/O(DB 호출) 대기 비중이 몇 %를 넘어서야 가상 스레드가 플랫폼 스레드 대비 처리량 이점을 보이기 시작하는가?** — Virtual Threads는 'I/O 바운드에 유리하다'는 정성적 설명만 알려져 있고 실제 손익분기점을 실측한 자료가 거의 없다. (필요 스택: Docker(spring.threads.virtual.enabled on/off), PostgreSQL + Toxiproxy, k6)

## 3. 컨테이너 오케스트레이션 (Kubernetes, Docker)

- **[초급] Docker bridge 네트워크 모드와 host 네트워크 모드 간 P99 지연 차이는 초당 요청 수가 몇 건을 넘어서면서부터 5% 이상으로 벌어지는가?** — bridge 모드의 NAT/iptables/veth 오버헤드가 실제로 체감되기 시작하는 트래픽 규모를 알면 네트워크 모드 선택과 고성능 서비스의 배치 전략에 직접 활용할 수 있다. (필요 스택: Docker(--network bridge vs host), iperf3, wrk/k6, tcpdump/iptables 카운터)
- **[초급] 동일 애플리케이션을 alpine, slim, distroless, 풀 우분투 베이스 이미지로 각각 빌드했을 때, 이미지 크기 차이가 docker run부터 첫 정상 응답까지 걸리는 콜드 스타트 시간에 몇 ms의 차이를 만드는가?** — 오토스케일링·서버리스 환경에서 콜드 스타트는 사용자 체감 지연에 직결되므로, 이미지 경량화 노력이 실제로 얼마나 효과가 있는지를 정량화할 수 있다. (필요 스택: Docker multi-stage build, 여러 베이스 이미지, time/curl 측정 스크립트, matplotlib/plotly)
- **[중급] Docker 컨테이너에 --cpus 제한을 걸었을 때, 평균 CPU 사용률이 limit 이하인데도 CFS 스로틀링으로 인해 P99 응답 지연이 2배 이상 튀기 시작하는 초당 요청 수(RPS)는 얼마인가?** — CPU limit은 순간적 버스트를 cgroup CFS period 단위로 억제하기 때문에 평균 사용률만 보면 드러나지 않는 지연 스파이크를 유발하며, capacity planning에서 자주 오해되는 문제라 수치 검증의 가치가 크다. (필요 스택: Docker, cgroup v2(cpu.stat nr_throttled), Nginx/Node.js 에코 서버, k6/wrk, Python 시각화)
- **[중급] 컨테이너 memory limit 대비 JVM 힙(-Xmx 또는 -XX:MaxRAMPercentage) 비율을 얼마로 설정해야 OOMKilled(exit code 137) 없이 Full GC 빈도를 최소화할 수 있으며, 몇 %를 넘어서면 OOMKilled가 발생하기 시작하는가?** — 힙 외 메타스페이스·스레드 스택·네이티브 버퍼를 고려하지 않은 컨테이너 메모리 설정은 실무에서 매우 흔한 장애 원인이므로, 안전한 힙/limit 비율을 실측 데이터로 제시하면 바로 적용 가능한 가이드라인이 된다. *(중복 병합)* (필요 스택: Docker --memory 제한, Eclipse Temurin 이미지, cgroup v2 memory.max/memory.stat, 메모리 부하 스크립트, docker stats + GC 로그 분석)
- **[고급] Kubernetes readiness probe의 periodSeconds·failureThreshold 조합에 따라 롤링 업데이트 중 발생하는 5xx 에러 비율이 최대 몇 배까지 차이 나는가?** — probe 튜닝이 무중단 배포의 실제 가용성에 미치는 영향은 크지만, 현업에서는 관행적인 기본값을 그대로 쓰는 경우가 많아 수치로 검증된 사례가 드물다. (필요 스택: kind(Kubernetes in Docker), kubectl, Deployment rolling update, k6, 로그 기반 에러율 집계)
- **[고급] CPU limit이 없는 컨테이너가 동일 호스트에서 CPU를 점유할 때, limit이 설정된 옆 컨테이너의 P99 지연이 SLA 200ms를 넘기기 시작하는 시점의 '코어 수 대비 컨테이너 밀도'는 얼마인가?** — 멀티테넌트 클러스터에서 bin-packing·오버커밋 정책을 세울 때 실측된 임계 밀도가 있으면 감(感)이 아닌 근거 기반 리소스 쿼터 설계가 가능하다. (필요 스택: Docker(stress-ng 부하 컨테이너 + --cpus 제한 서비스 컨테이너), wrk, cgroup CPU 모니터링)

## 4. OLAP/분석 데이터베이스 (ClickHouse)

- **[초급] ClickHouse에 100건 미만의 소량 배치를 초당 몇 건 이상 INSERT하면 파츠(Parts) 개수가 임계치를 넘어 'Too many parts' 머지 지연이 발생하기 시작하는가?** — 소량·고빈도 INSERT는 실무에서 가장 흔한 ClickHouse 장애·성능 저하 원인 중 하나이기 때문이다. (필요 스택: ClickHouse 단일 컨테이너, Python(clickhouse-connect) 부하 스크립트, system.parts/system.merges 폴링)
- **[초급] 동일 컬럼에 LZ4 대신 ZSTD(레벨 3/9)를 적용했을 때, 저장 공간 절감분이 스캔 쿼리 지연 증가분을 상쇄하기 시작하는 테이블 크기는 어느 지점인가?** — 스토리지 비용 절감과 쿼리 속도 중 무엇을 우선할지는 코덱 선택 시 반복되는 실무 딜레마이기 때문이다. (필요 스택: ClickHouse 단일 컨테이너, 코덱만 다른 2~3개 테이블, Python Faker 합성 데이터)
- **[중급] async_insert를 활성화한 상태에서 초당 삽입 요청 수가 얼마를 넘어서면 응답 지연(latency)이 동기 INSERT보다 오히려 나빠지기 시작하는가?** — async_insert_busy_timeout_ms 등 파라미터의 튜닝 기준이 되는 처리량 임계값이 벤치마크 없이 결정되는 경우가 많기 때문이다. (필요 스택: ClickHouse 단일 컨테이너, k6/Python asyncio 부하 도구, system.query_log p50/p99)
- **[중급] ORDER BY 키에서 저카디널리티 컬럼과 고카디널리티 컬럼의 배치 순서를 바꿨을 때, 동일 WHERE 필터 쿼리가 읽는 row 수와 지연시간이 몇 배까지 벌어지는가?** — 테이블 생성 시점의 ORDER BY 설계 실수는 이후 재적재 없이는 되돌리기 어려운 대표적인 비가역적 설계 결정이기 때문이다. (필요 스택: ClickHouse 단일 컨테이너, ORDER BY가 다른 2개 테이블, EXPLAIN + system.query_log read_rows)
- **[고급] 컨테이너 메모리를 제한한 상태에서 동시 실행되는 집계 쿼리 수가 몇 개를 넘으면 'Memory limit exceeded'로 쿼리가 강제 종료되기 시작하는가?** — 멀티테넌트·다중 대시보드 환경에서 동시성 쿼터를 얼마로 잡아야 하는지에 대한 실측 기준이 되기 때문이다. (필요 스택: ClickHouse 단일 컨테이너(docker --memory + max_server_memory_usage), Python concurrent.futures)
- **[고급] 2개 샤드로 구성한 ClickHouse 클러스터의 분산 쿼리가 조율·네트워크 오버헤드를 극복하고 단일 노드보다 빨라지기 시작하는 최소 데이터 규모(row 수)는 얼마인가?** — 언제부터 샤딩 도입 비용이 정당화되는지는 ClickHouse 스케일링 의사결정에서 가장 자주 나오는 질문이기 때문이다. (필요 스택: ClickHouse 3개 컨테이너(2 shard + keeper), docker-compose, Distributed 엔진 테이블)

## 5. RDBMS (PostgreSQL, MySQL)

- **[초급] 같은 행(row)을 동시에 UPDATE하는 트랜잭션 수가 몇 개를 넘어설 때 PostgreSQL의 TPS가 선형 증가를 멈추고 급격히 꺾이는가?** — 재고 차감, 카운터 증가처럼 흔한 hot-row 패턴에서 실제 병목 임계점을 알아야 큐잉/샤딩 도입 시점을 판단할 수 있다. (필요 스택: PostgreSQL 16, pgbench 커스텀 스크립트(동일 row 타겟), Python/matplotlib)
- **[중급] idle-in-transaction 상태의 장기 트랜잭션이 유지되는 시간이 길어질수록 초당 UPDATE 처리량 대비 테이블 bloat 비율은 얼마나 증가하고, autovacuum은 정리를 얼마나 지연시키는가?** — 방치된 장기 트랜잭션으로 인한 bloat와 디스크 급증은 실무에서 반복되는 온콜 인시던트 유형이다. (필요 스택: PostgreSQL 16, pgstattuple 확장, pgbench 백그라운드 UPDATE, 장기 트랜잭션 유발 세션)
- **[중급] WHERE 조건의 선택도(selectivity)가 몇 %를 넘어설 때 PostgreSQL 플래너가 인덱스 스캔 대신 시퀀셜 스캔을 선택하며, 이 임계점은 테이블 크기(100만 vs 1000만 행)에 따라 어떻게 이동하는가?** — '인덱스를 만들었는데 안 탄다'는 흔한 트러블슈팅 상황의 정량적 근거를 제공한다. (필요 스택: PostgreSQL 16, 다양한 카디널리티 시드 데이터, EXPLAIN(ANALYZE, BUFFERS) 자동화)
- **[중급] MySQL InnoDB REPEATABLE READ에서 동시 INSERT 트랜잭션 수가 증가할수록 gap lock으로 인한 데드락 발생 빈도는 어떤 곡선으로 증가하며, READ COMMITTED로 전환하면 몇 % 감소하는가?** — 주문/예약 시스템처럼 동시 INSERT가 많은 MySQL 서비스에서 자주 겪는 데드락 원인을 정량적으로 규명한다. (필요 스택: MySQL 8.0, Python 멀티스레드 동시 INSERT 클라이언트, information_schema/데드락 로그 파싱)
- **[고급] 동시 트랜잭션 수가 늘어날 때 Read Committed 대비 Serializable 격리수준에서 처리량 손실과 serialization failure로 인한 재시도율은 각각 몇 %까지 커지는가?** — 정합성을 위해 Serializable을 쓰려는 팀이 감수해야 할 실제 처리량 비용을 사전에 알 수 있다. (필요 스택: PostgreSQL 16, pgbench 커스텀 트랜잭션 스크립트(두 격리수준), 재시도 로직 포함 부하 클라이언트)
- **[고급] PostgreSQL 스트리밍 복제에서 쓰기 부하(TPS)가 증가할 때 replica lag가 1초를 넘어서는 지점은 어디이며, synchronous_commit 설정(on/off/remote_write)에 따라 이 임계점이 어떻게 달라지는가?** — 읽기 복제본의 정합성과 장애 조치(failover) 안전성에 직결되는, 용량 산정 시 반드시 필요한 수치다. (필요 스택: PostgreSQL 16 primary+replica(streaming replication), pgbench, pg_stat_replication 모니터링)

## 6. 메시지 큐/스트리밍 (Kafka, RabbitMQ)

- **[초급] Kafka producer의 acks 값을 0/1/all로 바꿀 때 처리량(msg/s)과 p99 latency가 각각 어떻게 변하고, acks=all은 acks=1 대비 처리량을 몇 % 희생시키는가?** — acks=all을 습관적으로 켜는 경우가 많지만, 그 안정성이 실제로 처리량을 얼마나 깎아먹는지 수치로 확인해야 트레이드오프 판단이 가능하다. (필요 스택: Apache Kafka(KRaft 단일 브로커), kafka-producer-perf-test.sh, Python(pandas+matplotlib))
- **[중급] RabbitMQ에서 consumer 처리 속도가 producer보다 느릴 때, 큐 적재 메시지 수(또는 메모리 사용률)가 얼마에 도달해야 publisher 연결이 flow-control로 blocked 되는가?** — flow control은 프로듀서 측에 아무 에러 없이 조용히 발행을 멈추게 하는 현상이라, 사전에 임계치를 알아두지 않으면 장애 원인 파악이 매우 어렵다. (필요 스택: RabbitMQ 3.x(management plugin), Python(pika) 부하 스크립트, rabbitmq_exporter+Prometheus/Grafana)
- **[중급] Kafka 토픽의 파티션 수를 1→N으로 늘리며 컨슈머 그룹의 컨슈머 수도 함께 늘릴 때, 처리량이 선형으로 증가하다가 포화되는 지점(파티션 수)은 어디인가?** — 파티션만 늘리면 무조건 처리량이 는다는 오해가 흔한데, 실제 스케일링 한계와 유휴 컨슈머 구간을 데이터로 확인해야 파티션 설계를 과잉/과소하게 하지 않는다. (필요 스택: Apache Kafka(KRaft), kafka-consumer-perf-test.sh, 다중 consumer 프로세스)
- **[중급] RabbitMQ에서 durable 큐+publisher confirm을 켰을 때 처리량이 몇 % 감소하며, quorum queue는 동일 조건에서 classic queue 대비 손실 폭이 얼마나 더 큰가?** — quorum queue는 Raft 기반 복제로 안정성을 높이지만 그 대가로 지불하는 처리량 손실을 실무자들이 체감으로만 알고 있어, 수치화하면 큐 타입 선택 기준이 명확해진다. (필요 스택: RabbitMQ 3.x(quorum queue), rabbitmq-perf-test, 결과 CSV 파싱)
- **[고급] Kafka consumer group에 컨슈머가 추가/이탈해 리밸런싱이 발생할 때 메시지 처리가 몇 초간 정지되며, 컨슈머 수가 늘어날수록 이 정지 시간은 어떻게 증가하는가?** — 오토스케일링으로 컨슈머 수를 자주 조정하는 환경에서 리밸런싱이 유발하는 처리 중단이 실제 지연 SLA에 미치는 영향을 정량화할 수 있다. (필요 스택: Apache Kafka(KRaft), confluent-kafka-python(ConsumerRebalanceListener), 타임스탬프 로깅)
- **[고급] 3노드 Kafka 클러스터에서 파티션 leader 브로커를 강제 종료했을 때, 새 leader가 선출되어 producer 요청이 재개되기까지 몇 ms가 걸리고 그 사이 실패율은 얼마나 되는가?** — 브로커 장애는 프로덕션에서 반드시 발생하므로, 실제 복구 시간과 그 사이의 에러율을 미리 측정해두면 장애 대응 SLA를 현실적으로 설계할 수 있다. (필요 스택: Apache Kafka 3-node(KRaft combined mode), Docker Compose, kafka-producer-perf-test, docker stop 장애 주입)

## 7. 네트워크/동시성 (HTTP, Nginx, TCP)

- **[초급] Nginx의 worker_connections 값을 512/2048/8192로 바꿔가며 동시 커넥션을 늘릴 때, 커넥션 거부(에러율 급증)가 시작되는 지점은 worker_connections 설정값에 선형 비례하는가, 아니면 파일 디스크립터 한계 등 다른 병목이 먼저 나타나는가?** — C10K 튜닝은 자주 언급되지만 실제로 어느 설정이 진짜 병목인지 실험으로 확인하는 경우는 드물다. (필요 스택: Nginx, 경량 echo 백엔드(Go/Node), wrk2/k6, ulimit/net.core.somaxconn 조정)
- **[초급] Nginx가 백엔드(upstream)와의 연결에 keepalive 커넥션 풀을 사용하지 않을 때와 사용할 때, 초당 요청 수를 늘려가며 측정한 P99 지연시간 차이는 몇 배까지 벌어지는가?** — upstream keepalive 설정 하나로 TCP 핸드셰이크 비용을 얼마나 절감하는지는 바로 실무에 적용 가능한 값이다. (필요 스택: Nginx(upstream keepalive on/off), 백엔드 앱, k6/wrk2, tcpdump)
- **[고급] Keep-Alive 없이 매 요청마다 새 TCP 커넥션을 맺는 클라이언트가 초당 몇 커넥션을 생성하면 서버 컨테이너의 TIME_WAIT 소켓 수가 ephemeral 포트 범위에 근접해 커넥션 실패가 발생하는가?** — 단명 커넥션 폭주로 인한 포트 고갈은 실무에서 원인 파악이 까다로운 대표적 장애 유형이다. (필요 스택: 간단한 HTTP 서버, wrk(--connections 매번 재생성), ss/netstat, sysctl 파라미터 조정)
- **[고급] 클라이언트 측 동시 TCP 커넥션 수를 동일하게 제한했을 때(예: 1~4개), HTTP/1.1 REST와 gRPC(HTTP/2)가 처리할 수 있는 초당 요청 수는 몇 배까지 차이나는가?** — gRPC 도입 논의에서 '멀티플렉싱이 실제로 얼마나 이득인가'는 숫자 없이 회자되는 경우가 많다. (필요 스택: gRPC 서버(Go), 동등 기능 REST 서버(Go), ghz, wrk2)

## 8. 스토리지/파일시스템 (디스크 I/O)

- **[초급] ext4, xfs, btrfs 파일시스템에서 4KB 크기의 소파일 100만 개를 생성할 때 처리 완료 시간과 inode/메타데이터 오버헤드는 각각 얼마나 차이가 나는가?** — 컨테이너 이미지 레이어나 캐시처럼 소파일이 대량으로 생성되는 워크로드에서 파일시스템 선택이 실제 배포 성능에 미치는 영향을 정량화할 수 있다. (필요 스택: Docker, fio/fs_mark, 루프백 이미지 ext4/xfs/btrfs 포맷)
- **[초급] 동일한 fio 워크로드를 Docker overlay2 컨테이너 내부, bind mount, named volume, tmpfs에서 각각 실행했을 때 순차·랜덤 IOPS와 지연시간은 몇 % 차이가 나는가?** — 컨테이너 내부에 직접 쓸지 볼륨을 마운트할지 결정할 때 실무자가 바로 참고할 수 있는 실측 데이터를 제공한다. (필요 스택: Docker, fio, volume/bind mount/tmpfs 옵션 비교)
- **[중급] fsync()를 매 쓰기마다 호출하는 경우와 호출하지 않는(버퍼드) 경우 초당 트랜잭션 처리량(TPS)은 몇 배 차이가 나며, 그 격차는 direct I/O 여부에 따라 어떻게 달라지는가?** — DB나 메시지 큐의 WAL fsync 정책을 결정할 때 성능-내구성 트레이드오프를 수치로 제시해 튜닝 근거를 만들 수 있다. (필요 스택: Docker, fio(--fsync=1, --direct=1)/sysbench fileio)
- **[중급] 같은 디렉토리에 동시에 파일을 생성하는 프로세스 수를 1개에서 512개까지 늘려갈 때 초당 파일 생성 처리량은 몇 개 프로세스 지점에서 포화되거나 역전(감소)되는가?** — 로그 수집기나 캐시 서버처럼 다수 워커가 같은 디렉토리에 소파일을 쓰는 아키텍처에서 동시성 한계를 사전에 예측하는 데 직접 활용할 수 있다. (필요 스택: Docker, fs_mark/자체 워커 스크립트, GNU parallel)
- **[고급] Linux I/O 스케줄러를 none(noop), mq-deadline, bfq로 바꿨을 때 동일한 랜덤 읽기 부하에서 p99/p999 지연시간은 각각 얼마나 달라지는가?** — 컨테이너 호스트의 I/O 스케줄러 설정이 지연시간에 미치는 영향은 잘 알려지지 않았지만 프로덕션 튜닝에서 자주 등장하는 파라미터다. (필요 스택: Docker(privileged), fio, /sys/block/*/queue/scheduler 조작)
- **[고급] 컨테이너 간 NFS로 마운트한 볼륨과 로컬 overlay2 볼륨에서 소파일 랜덤 읽기/쓰기 지연시간은 몇 배 차이가 나며, 그 격차는 파일 크기에 따라 어떻게 변하는가?** — 쿠버네티스 환경에서 흔히 쓰이는 NFS 기반 PV의 실제 성능 페널티를 소규모 랩 환경에서 미리 가늠해볼 수 있다. (필요 스택: Docker(nfs-kernel-server + client), fio, NFS mount)
