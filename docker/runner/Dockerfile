# 공용 실행 이미지. lib/·schemas/를 빌드 시점에 /app에 복사해 PYTHONPATH에 둔다.
# 빌드 컨텍스트는 리포 루트다 (docker-compose.yml의 build.context 참고) — lib/와
# schemas/가 이 Dockerfile 위치(docker/runner/) 밖에 있기 때문이다.
FROM python:3.12-slim

ENV MPLBACKEND=Agg \
    PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY docker/runner/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY lib/ ./lib/
COPY schemas/ ./schemas/
