# CONTRIBUTING

## 1. 5분 퀵스타트

리포 루트 [`README.md`](README.md#5분-퀵스타트)의 설치 표와 명령 시퀀스를 그대로
따르세요. 요약:

```
git clone https://github.com/dja1369/ds_labs.git
cd ds_labs
docker compose -f docker/runner/docker-compose.yml build
docker compose -f templates/redis-blocking-threshold/docker-compose.yml run --rm runner ./experiment.sh --params params.yml --out results --smoke
```

(`redis-blocking-threshold`는 예시입니다. 실제로 존재하는 템플릿 슬러그로 바꿔서
실행하세요. 현재는 `templates/_skeleton/`만 존재하는 더미 템플릿입니다.)

## 2. 브랜치 워크플로우

- `main`은 보호 브랜치입니다 — 직접 push가 차단되어 있고, 모든 변경은 PR을 통해서만
  들어갑니다.
- 브랜치 이름은 목적에 맞는 접두사를 붙입니다: `feature/*`는 신규 실험(새 템플릿
  추가, 새 `experiments/` 기록) 브랜치입니다.
- PR을 올리기 전 [4절](#4-새-템플릿-추가-절차) 체크리스트와 로컬 자기검증을
  완료하세요.

## 3. 실험 루프 이해하기

```
안건 → 템플릿 선택/생성 → 실행 → 검증 → 차트 → README → 발행
```

Claude Code를 쓰는 경로(`ds-lab-run-experiment` 스킬)와 사람이 손으로 직접 치는
경로는 **완전히 동일한 `docker compose` 명령**으로 수렴합니다. 이것이 이 프로젝트가
채택한 하이브리드 실행 모델의 핵심입니다 — 스킬 안에만 존재하는 숨은 로직은 없습니다.

## 4. 새 템플릿 추가 절차

```
docker compose -f docker/runner/docker-compose.yml run --rm runner python -m lib.scaffold <new-slug>
```
(스캐폴딩 도구는 로드맵 Phase 5에서 추가될 예정입니다. 그 전까지는
`templates/_skeleton/`을 직접 복사해서 시작하세요.)

이후 `docker-compose.yml`, (선택) `Dockerfile`, `experiment.sh`, `params.yml`,
`TEMPLATE.md`를 작성하고 아래를 확인합니다.

- [ ] `docker-compose.yml`의 볼륨이 상대 경로만 쓰는가
- [ ] `experiment.sh`가 `--params --out --smoke`를 지원하는가
- [ ] `--smoke` 모드가 60초 내외로 끝나며 유효한 `results.json`을 만드는가
- [ ] `python -m lib.validate_results`가 통과하는가
- [ ] `python -m lib.chart`가 `data[]`의 고유 metric 수만큼 PNG를 생성하는가
- [ ] `docker compose ... down -v` 이후 `docker ps -a`에 잔여 컨테이너가 없는가
- [ ] `TEMPLATE.md`에 기술/전제조건/사용 예시가 있는가
- [ ] base image가 `docker manifest inspect`로 linux/amd64·linux/arm64 모두 확인되는가

## 5. 크로스플랫폼 검증 방법

- PR 작성자는 최소 자신의 OS 1곳에서 성공 실행 로그를 PR에 첨부합니다.
- CI(`contract-check.yml`, ubuntu-latest)가 실제 컨테이너 실행으로 자동 검증합니다 —
  GitHub 호스팅 러너 중 Linux 컨테이너를 실제로 돌릴 수 있는 것은 ubuntu뿐입니다
  (macOS 러너는 Docker 미탑재 + Apple Silicon 중첩 가상화 미지원, Windows 러너는
  Linux 컨테이너 미지원).
- CI(`static-check.yml`, windows-latest)는 `docker compose config -q`, 스키마 자체
  유효성, CRLF 손상 여부 등 **정적 계약만** 검사합니다.
- 신규 템플릿은 병합 전 macOS/Windows 환경을 가진 사람이
  [`VALIDATION_CHECKLIST.md`](VALIDATION_CHECKLIST.md)에 따라 실제 Docker Desktop에서
  수동 스모크런을 각 1회 수행하고 체크를 남깁니다 — "해당 OS CI가 없으니 검증 없이
  통과"는 허용하지 않습니다.

## 6. 코드 스타일

- 외부 의존성 추가 전 "정말 stdlib/이미 있는 라이브러리로 안 되는가"를 자문하세요.
  `docker/runner/requirements.txt`에 항목을 늘리는 PR은 사유를 명시합니다.
- `experiment.sh`는 `set -euo pipefail` 헤더 필수, 표준 플래그(`--params --out --smoke`)를
  벗어나지 않습니다.
- 검증·차트·발행 로직은 항상 `runner` 컨테이너 안에서만 실행합니다 — 호스트 언어
  의존성을 늘리지 않습니다.
- [`CONTRACT.md`](CONTRACT.md)(계약 자체) 변경 PR은 기존 템플릿 전부에 대한 하위 호환
  영향을 설명에 명시합니다.

## 7. 문서 신뢰성 규칙

README/포스트에 적는 모든 수치는 `results.json`에서 인용합니다. PR에는 안건 원문,
`results.json`의 headline 수치, 다음 연구 과제 제안 1개 이상을 포함합니다.
