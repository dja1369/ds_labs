# ds_labs

컴퓨터/인프라 실험(Redis, Kubernetes, ClickHouse, Spring Boot 등)을 재현 가능한
형태로 수행하고, 결과를 [GitHub Pages](https://dja1369.github.io/ds_labs/)에
공개하는 실험 랩입니다.

```
안건(연구 질문) → 템플릿 기반 환경 구성 → 테스트 진행 → 문서화(이미지 포함) → 결론 정리 → 다음 연구 과제 제안
```

Claude Code가 안건을 받아 이 루프를 보조 실행할 수도 있고, 사람이 Claude 없이
아래 명령을 그대로 타이핑해 동일한 결과를 재현할 수도 있습니다 — 두 경로는
**완전히 동일한 `docker compose` 명령**으로 수렴합니다.

## 5분 퀵스타트

호스트에 필요한 것은 **Docker와 git 뿐**입니다. Python, Ruby, bash 등 다른 언어/도구는
전혀 설치할 필요가 없습니다 — 실행/검증/차트 생성 전부 컨테이너 안에서만 일어납니다.

| OS | 필수: Docker | 필수: git |
|---|---|---|
| macOS | `brew install --cask docker` | `brew install git` (또는 Xcode CLT) |
| Windows | `winget install Docker.DockerDesktop` (WSL2 backend 기본값 유지) | `winget install Git.Git` |
| Linux | `curl -fsSL https://get.docker.com \| sh` 후 `sudo usermod -aG docker $USER` | `sudo apt install git` (배포판별) |

버전 하한: Docker Engine ≥ 24.x, Compose V2(`docker compose`, 최소 v2.20). 하이픈이 있는
레거시 `docker-compose`(V1)는 쓰지 않습니다.

### Windows 사용자를 위한 사전 확인 (preflight)

Docker Desktop 설치 전후로 아래를 순서대로 확인하세요. "설치 마법사가 전부 자동으로
처리한다"고 가정하지 않는 편이 안전합니다.

1. `wsl --status` — WSL2가 활성인지 확인 (없으면 관리자 PowerShell에서 `wsl --install` 후 재부팅)
2. Docker Desktop 설치 후 실행, "WSL 2 based engine"(기본값) 유지
3. `docker compose version` — v2.20 이상인지 확인
4. `docker run --rm hello-world` — 데몬이 실제로 컨테이너를 돌릴 수 있는지 확인

(3~4번은 macOS/Linux에서도 동일하게 최초 1회 확인하길 권장합니다.)

### 실행

```
git clone https://github.com/dja1369/ds_labs.git
cd ds_labs
docker compose -f docker/runner/docker-compose.yml build
docker compose -f templates/_skeleton/docker-compose.yml run --rm runner ./experiment.sh --params params.yml --out results --smoke
```

마지막 명령이 `wrote results/results.json`을 출력하면 파이프라인이 정상 동작하는
것입니다. 실전 템플릿(예: `templates/redis-blocking-threshold/`)이 추가되면 같은
패턴으로 `-f templates/<slug>/docker-compose.yml`만 바꿔서 실행합니다.

## 왜 이 명령이 macOS/Windows/Linux에서 글자 하나 다르지 않게 동일하게 동작하는가

1. **명령 문자열에 쉘 전용 문법이 전혀 없습니다.** `$()`, 백틱, 파이프, 와일드카드
   글로빙, `&&`을 호스트 명령에 절대 쓰지 않습니다 — "프로그램명 + 플래그" 나열만
   사용합니다. PowerShell, cmd.exe, bash, zsh 각자의 파서로 토큰화하더라도 결과적으로
   `docker`에 전달되는 인자는 동일합니다.
2. **`experiment.sh`는 항상 Linux 컨테이너 내부에서 실행됩니다.** 컨테이너 OS는
   호스트 OS와 무관하게 항상 Linux이므로 "Windows에 bash가 없다"는 문제 자체가
   발생하지 않습니다.
3. **`docker`/`docker compose` CLI 자체가 3개 OS 모두에서 공식 배포되는 동일 버전의
   네이티브 바이너리입니다.** 이 프로젝트 전체에서 호스트에 설치해야 하는 것은
   Docker와 git뿐입니다.
4. **볼륨은 항상 compose 파일 기준 상대 경로만 사용합니다.** 호스트 절대경로 문자열을
   조립하지 않으므로 `$PWD`나 Windows의 `C:\Users\...` 표기 문제 자체가 없습니다.

WSL2는 Docker Desktop의 내부 구현일 뿐, 사용자가 WSL2 셸을 열어 작업할 필요는
없습니다 — 설치 후 PowerShell에서 위 명령을 그대로 치면 됩니다.

## 문서

- [`CONTRACT.md`](CONTRACT.md) — 실행 진입점 / `results.json`·`.csv` 스키마 / `README.template.md` 토큰의 단일 정본
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — 새 실험 템플릿을 기여하는 방법
- [`VALIDATION_CHECKLIST.md`](VALIDATION_CHECKLIST.md) — 신규 템플릿 머지 전 크로스-OS 수동 검증 로그
- [`TOPICS.md`](TOPICS.md) — 연구 안건(실험 주제) 후보 리스트

## 디렉토리 구조 요약

```
templates/      재사용 가능한 기술 스택별 실험 스캐폴드 (날짜 없음)
experiments/    실제로 수행된 실험 기록 (append-only, 날짜 있음)
docker/runner/  공용 실행 이미지 (Python + matplotlib + 검증 도구)
lib/            검증/CSV 변환/차트/발행용 공용 파이썬 모듈 (항상 컨테이너 내부 실행)
schemas/        results.json의 정본 JSON Schema
docs/           Jekyll 사이트 루트 (GitHub Pages "Deploy from branch: main/docs")
.claude/skills/ Claude Code 스킬 (안건 실행 / 신규 템플릿 스캐폴딩)
```

## 라이선스

[MIT](LICENSE)
