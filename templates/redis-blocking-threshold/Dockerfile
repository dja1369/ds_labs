# 공용 러너 이미지를 redis-tools(redis-benchmark/redis-cli)로 확장한다. 계약
# 자체(CONTRACT.md)에는 도메인 특화 도구를 넣지 않는다 — docker/runner/Dockerfile
# 참고.
FROM ds-labs/runner:1.0.0

RUN apt-get update && apt-get install -y --no-install-recommends redis-tools \
    && rm -rf /var/lib/apt/lists/*
