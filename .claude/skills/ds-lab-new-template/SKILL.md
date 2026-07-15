---
name: ds-lab-new-template
description: >
  새 기술 스택(예: ClickHouse, Kubernetes, Kafka)을 위한 실험 템플릿을
  templates/_skeleton에서 스캐폴딩한다. 트리거: "새 템플릿 만들어줘",
  "~에 대한 실험 템플릿 추가해줘".
---

# ds-lab-new-template

새 기술 스택을 위한 `templates/<slug>/`를 `templates/_skeleton/`에서
스캐폴딩하고, 3대 계약(`CONTRACT.md`)을 만족하는 최소 구현까지 완성한다.
이 스킬은 실험을 실행하지 않는다 — 실행은 `ds-lab-run-experiment` 스킬의 몫이다.

## 절차

1. **스캐폴딩** — 호스트 쉘 명령(`cp -r`은 cmd.exe에 없다)이 아니라 runner
   컨테이너의 Python으로 수행한다:
   ```
   docker compose -f docker/runner/docker-compose.yml run --rm runner python -m lib.scaffold <new-slug>
   ```
   `lib/scaffold.py`가 `templates/_skeleton`을 `templates/<new-slug>`로 복사하고
   `_skeleton` 문자열을 새 슬러그로 치환한다(대상이 이미 존재하면 실패 —
   fail loud). `<new-slug>`는 소문자·숫자·하이픈만 허용된다.

2. **인프라 서비스 정의** — `docker-compose.yml`에 대상 인프라 서비스를
   추가한다 — "Docker 위에서 동작한다"는 원칙만 지키면 오케스트레이션 도구(단일
   컨테이너/`docker-compose`/`kind`/`k3d` 등)는 자유. 볼륨은 항상 상대 경로만
   사용한다.

3. **도메인 CLI 확장** — 도메인 전용 CLI가 필요하면 `Dockerfile`을
   `FROM ds-labs/runner:1.0.0`으로 작성해 확장한다(공용 이미지에는 넣지 않는다).

4. **`experiment.sh` 구현** — `up`/`test`/`teardown` 로직을 구현한다. 반드시
   `schemas/results.schema.json`을 만족하는 `results.json`을 출력해야 하고,
   `--smoke` 모드로 1분 내외에 끝나야 한다. bash에는 YAML 파서가 없으므로
   `params.yml` 읽기와 JSON 조립은 `python3`(공용 이미지에 이미 포함된
   PyYAML)에 위임하는 패턴을 권장한다 — `templates/redis-blocking-threshold/experiment.sh`
   참고.

5. **`TEMPLATE.md` 작성** — 이 템플릿이 다루는 기술/전제조건/사용 예시를
   적는다(`ds-lab-run-experiment` 스킬의 2단계가 이 파일을 읽고 템플릿을
   선택한다).

6. **로컬 스모크 통과 확인** (`VALIDATION_CHECKLIST.md` 1~2단계):
   ```
   docker compose -f templates/<new-slug>/docker-compose.yml run --rm runner ./experiment.sh --params params.yml --out results --smoke
   docker compose -f docker/runner/docker-compose.yml run --rm runner python -m lib.validate_results templates/<new-slug>/results/results.json
   docker compose -f docker/runner/docker-compose.yml run --rm runner python -m lib.to_csv templates/<new-slug>/results/results.json templates/<new-slug>/results/results.csv
   docker compose -f docker/runner/docker-compose.yml run --rm runner python -m lib.chart --results templates/<new-slug>/results/results.json --out templates/<new-slug>/results/charts/
   docker compose -f templates/<new-slug>/docker-compose.yml down -v
   ```
   다섯 단계 모두 exit 0이어야 하고, `down -v` 이후 `docker ps -a`에 잔여
   컨테이너가 없어야 한다.

7. **사람에게 diff 검토 요청** — 인프라 코드를 스킬이 임의로 커밋하지 않는다.
   `git diff --stat`을 보여주고 사람이 검토·커밋하도록 안내한다.

## 금지 사항

- 로컬 스모크 통과 전에 CI/PR을 만들지 않는다.
- 공용 이미지(`docker/runner/`)에 도메인 전용 도구를 추가하지 않는다 — 항상
  템플릿별 `Dockerfile` 확장으로 처리한다.
- `CONTRACT.md`의 표준 토큰 집합에 임의로 새 토큰을 추가하지 않는다.
