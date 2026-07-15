# implement.md — ds_labs 최종 구현 설계 문서

> 이 문서는 `AGENDA.md`가 상세 설계 모델에게 위임한 미결 항목(디렉토리 구조, 3대 공통 계약의 정확한 스키마, 차트 도구, Claude 스킬 인터페이스, Jekyll 설정, CONTRIBUTING, 신규 템플릿 검증 프로세스, 크로스플랫폼 실행 방식, 첫 파일럿) 전부에 대한 답을 담은 착수 가능한 구현 명세다.

## 0. 이 문서가 종합된 방식 (설계 근거)

세 초안(미니멀리즘 우선 / 기여자 경험 우선 / 자동화 우선)을 3가지 관점(재현성·기여편의성 / 크로스플랫폼 견고성 / 자동화 신뢰성)에서 심사한 결과, **"자동화 우선"** 초안이 세 심사 모두에서 최고점 또는 공동 최고점(52·52·51)을 받아 기본 골격으로 채택한다. 핵심 이유는 세 심사가 공통으로 지적한 것과 같다 — 호스트에 남기는 실행 표면을 `docker compose run ...` 한 줄로 완전히 좁히고, bash/Python 등 언어 의존성 자체를 컨테이너 안으로 격리해 "무엇을 설치해야 재현되는가"라는 질문에 가장 단순하고 흔들림 없는 답을 준다는 점이다.

다만 세 심사 모두 "근소한 차이"라고 명시했고, 다른 두 초안이 가진 구체적 강점을 지적했다. 이 문서는 그 강점들을 실제로 접목한다.

- **미니멀리즘 우선**에서 가져온 것: ① Phase 게이팅 로드맵(증명되기 전까지 도구를 늘리지 않는 원칙, 세 심사 모두 "유지보수 부담 최저"로 평가), ② `results.json`의 `data[]`를 `metric/x_label/x/y/unit/note` 완전 고정 키의 롱포맷 하나로 통일(자동화 우선 원안의 `points[].x_field` 동적 키보다 파싱이 단순하다는 지적을 반영), ③ `.gitattributes`를 통한 LF 강제.
- **기여자 경험 우선**에서 가져온 것: ① `docs/` 서브디렉토리 + GitHub Pages "Deploy from branch: main /docs" 방식(자동화 우선 원안의 루트-레벨 Jekyll + `exclude:` 목록 관리 방식보다 드리프트에 안전 — 새 디렉토리를 추가할 때마다 exclude 목록을 갱신해야 하는 부담이 없다), ② 5분 퀵스타트 표, PR 체크리스트, `VALIDATION_CHECKLIST.md`(온보딩 문서 밀도가 세 안 중 최고로 평가됨), ③ 스킬을 "실행 루프"와 "신규 템플릿 스캐폴딩"으로 2분리(하나의 SKILL.md에 서로 다른 트리거를 욱여넣지 않음).
- **자동화 우선**에서 유지한 것: 호스트 유일 의존성 = Docker(+git), 쉘 확장 문법을 호스트 명령에 절대 쓰지 않는 원칙, WSL2를 "설치 마법사의 구현 세부사항"으로 정확히 위치시키는 설명, CRLF/아키텍처(arm64) 함정에 대한 구체적 대응, README-데이터 자동 정합성 검사 아이디어(로드맵 후반부 항목으로 채택).
- **기여자 경험 우선**의 Task(go-task) 편의 계층은 채택하지 않는다 — 세 심사 모두 이 계층이 크로스플랫폼 검증 대상 바이너리를 하나 늘리고 `automationFit`/`maintainability`를 끌어내리는 요인으로 지적했다. "호스트 의존성은 Docker 하나"라는 원칙을 끝까지 지킨다.
- **기여자 경험 우선**의 "템플릿별 자유 CSV 컬럼" 정책도 채택하지 않는다 — 심사에서 "자동 파싱 신뢰성과 정면으로 충돌한다"고 명시적으로 지적된 부분이다. CSV는 JSON에서 파생되는 고정 컬럼만 허용한다(4장 참조).

또한 이 문서는 `AGENDA.md` 원문을 직접 확인해 두 가지를 바로잡았다. (1) AGENDA.md는 "레디스 블로킹 임계치"를 **확정된 파일럿이 아니라 개념 설명용 예시**라고 명시하고 "템플릿/구조부터 먼저 완성"하기로 결정했다고 적혀 있다 — 세 초안 모두 이를 "이미 확정된 파일럿"처럼 서술했으나, 이 문서는 10장에서 "추천"으로 톤을 바로잡는다. (2) 별도 워크플로우 산출물인 `TOPICS.md`(연구 안건 후보 46건)에 AGENDA 예시와 정확히 대응하는 항목(#1, 캐시 카테고리, 초급)이 이미 존재하므로, 이를 근거로 더 구체적인 파일럿 스펙을 제시한다.

## 1. 개요

`AGENDA.md`가 정의하는 ds_labs는 "안건(연구 질문) → 템플릿 기반 환경 구성 → 테스트 진행 → 문서화(이미지 포함) → 결론 정리 → 다음 연구 과제 제안"이라는 실험 루프를 반복하며, 컴퓨터/인프라 전반(Redis, Kubernetes, ClickHouse, Spring Boot 등)의 실험을 재현 가능한 형태로 수행하고 GitHub Pages에 공개하는 포트폴리오 성격의 실험 랩이다. 실행 모델은 하이브리드가 필수다 — Claude Code가 안건을 받아 파이프라인을 보조 수행할 수도, 사람이 Claude 없이 클론 후 직접 재현할 수도 있어야 한다. 아키텍처는 이미 "A안: Docker 공통 기판 + Jekyll 네이티브 발행"으로 확정됐고, 모든 템플릿이 지켜야 할 3대 공통 계약(실행 진입점 / `results.json`·`.csv` / `README.template.md`)만 강제하며 오케스트레이션 도구 자체는 실험 성격에 맞게 자유다. 유일하게 미해결로 남은 문제는 원래 계약이던 `run.sh`(bash)가 Windows 네이티브에서 실행되지 않는다는 점이며, AGENDA.md는 이 실행 방식의 재검토를 상세 설계 모델(이 문서)에 명시적으로 위임했다.

이 문서의 목적은 AGENDA.md가 다음 모델에게 위임한 9가지 미결 항목(디렉토리 구조, `results.json/.csv` 스키마, 차트 도구, Claude 스킬 인터페이스, Jekyll 세부 설정, CONTRIBUTING 상세, 신규 템플릿 검증 프로세스, 첫 파일럿 선정, 크로스플랫폼 실행 방식)에 대해 실제 파일 경로·필드명·명령어 수준까지 구체화된 답을 제시하고, 구현 착수 순서(로드맵)까지 확정하는 것이다.

## 2. 디렉토리 구조

```
ds_labs/
├── AGENDA.md                        # 기존 요구사항 문서 (수정 대상 아님)
├── TOPICS.md                        # 연구 안건 후보 리스트 (별도 워크플로우 산출물, 참조만)
├── README.md                        # 프로젝트 소개 + 5분 퀵스타트 (Mac/Windows/Linux 병기)
├── CONTRACT.md                      # 3대 공통 계약의 단일 명세서 (엔트리포인트/스키마/README 토큰)
├── CONTRIBUTING.md                  # 기여 가이드
├── VALIDATION_CHECKLIST.md          # 신규 템플릿 머지 전 수동 크로스-OS 검증 로그
├── LICENSE
├── .gitattributes                   # *.sh/*.py는 LF 강제 (Windows 체크아웃 CRLF 손상 방지)
├── .gitignore                       # templates/**/results/(실행 임시 산출물), experiments/**/results/raw/, docs/_site/ 등
├── .github/
│   └── workflows/
│       ├── contract-check.yml       # ubuntu-latest: 실제 컨테이너 스모크 실행 (CI 스모크런은 Linux만 가능, 9장 참고)
│       └── static-check.yml         # windows-latest: 정적 계약 검증만 (아래 9장 참고)
│
├── docker/
│   ├── runner/
│   │   ├── Dockerfile               # 공용 실행 이미지: python:3.12-slim + 검증/차트 도구
│   │   ├── requirements.txt         # matplotlib==3.9.2, jsonschema==4.23.0, PyYAML==6.0.2 (버전 고정)
│   │   └── docker-compose.yml       # runner 서비스 정의. 리포 루트를 상대경로(../..)로 /workspace에
│   │                                 #   마운트 + working_dir=/workspace 고정 → 호스트 명령에 $PWD 불필요
│   └── jekyll/                      # (선택) 로컬 미리보기 전용, ruby:3.3-slim + github-pages gem (7장 참고)
│       └── docker-compose.yml
│
├── schemas/
│   └── results.schema.json          # results.json의 단일 정본 JSON Schema (draft 2020-12)
│
├── lib/                              # 공용 파이썬 모듈. 항상 runner 컨테이너 "내부"에서만 실행됨
│   ├── validate_results.py          # python -m lib.validate_results <path>
│   ├── to_csv.py                    # python -m lib.to_csv <results.json> <out.csv>
│   ├── chart.py                     # python -m lib.chart --results <path> --out <dir>
│   ├── publish_post.py              # python -m lib.publish_post <experiments/<slug>/> → Jekyll 포스트+이미지 생성
│   ├── scaffold.py                  # python -m lib.scaffold <new-slug> → _skeleton 복사+토큰 치환 (cp -r 대체, 크로스플랫폼)
│   └── style.mplstyle               # 차트 스타일 정본 (팔레트/dpi/폰트 고정)
│
├── templates/                       # 재사용 가능한 "기술 스택별" 실험 스캐폴드 (날짜 없음)
│   ├── _skeleton/                   # 신규 템플릿 시작점
│   │   ├── docker-compose.yml       # runner 서비스 + 대상 인프라 서비스 정의
│   │   ├── Dockerfile               # (선택) ds-labs/runner:<ver> 확장, 도메인 도구 설치용 TODO
│   │   ├── experiment.sh            # 컨테이너 내부 전용 실행 스크립트 (TODO 포함)
│   │   ├── params.yml               # 실험 파라미터 + smoke 오버라이드 골격
│   │   ├── README.template.md       # ${TOKEN} 치환식 문서 스켈레톤
│   │   └── TEMPLATE.md              # 이 템플릿이 다루는 기술/전제조건 설명 (스킬이 템플릿 선택 시 참조)
│   │
│   └── redis-blocking-threshold/    # 첫 파일럿 구현체 (10장 참고)
│       ├── docker-compose.yml
│       ├── Dockerfile               # ds-labs/runner:1.0.0 확장 + redis-tools 설치
│       ├── experiment.sh
│       ├── params.yml
│       ├── README.template.md
│       └── TEMPLATE.md
│
├── experiments/                     # 실제로 수행된 실험의 기록 (append-only, 날짜 있음)
│   └── 2026-07-20-redis-blocking-threshold/
│       ├── agenda.md                # 이 실험의 안건/가설 원문
│       ├── params.yml               # 실행에 실제로 사용된 파라미터 사본
│       ├── results/
│       │   ├── results.json         # 정식 커밋 대상 (정본)
│       │   ├── results.csv          # results.json에서 파생 (정식 커밋, 스프레드시트 편의용)
│       │   └── charts/
│       │       ├── throughput_ops_sec.png
│       │       └── p99_latency_ms.png
│       └── README.md                # 완성된 문서 (Jekyll 포스트 발행의 원본)
│
├── docs/                            # Jekyll 사이트 루트. GitHub Pages Settings에서
│   │                                 # "Deploy from branch: main / docs" 로 지정 — Actions 불필요
│   ├── _config.yml
│   ├── Gemfile                      # 로컬 미리보기 전용 (선택, 배포 경로 아님)
│   ├── index.md
│   ├── _posts/
│   │   └── 2026-07-20-redis-blocking-threshold.md
│   └── assets/
│       └── images/
│           └── 2026-07-20-redis-blocking-threshold/   # <date>-<experiment_id> — experiments/·_posts/와 동일 슬러그
│               ├── throughput_ops_sec.png
│               └── p99_latency_ms.png
│
└── .claude/
    └── skills/
        ├── ds-lab-run-experiment/
        │   └── SKILL.md             # 안건→실행→검증→차트→문서화→발행 메인 루프
        └── ds-lab-new-template/
            └── SKILL.md             # 신규 기술 스택 템플릿 스캐폴딩
```

### 분리 원칙

- **`templates/`(재사용 가능한 뼈대, 날짜 없음) vs `experiments/`(실제 실행 결과, 날짜 있음)**: 같은 템플릿을 다른 파라미터로 여러 번 실행해 여러 `experiments/`를 만들 수 있다.
- **`docker/runner/`(공용 실행 이미지)와 템플릿별 `Dockerfile`(도메인 도구 확장) 분리**: 공용 이미지는 파이썬/matplotlib/스키마 검증기만 담아 최대한 얇게 유지하고(Rule 2 단순성), `redis-tools`처럼 특정 실험에만 필요한 CLI는 그 템플릿의 `Dockerfile`이 `FROM ds-labs/runner:1.0.0`으로 확장해 설치한다. 공통 계약(3대 계약)에 도메인 특화 도구가 섞여 들어가지 않는다.
- **`docs/`를 리포 루트가 아닌 하위 디렉토리로 분리**: GitHub Pages의 "Deploy from branch: main / docs" 옵션을 그대로 쓰면 `templates/`, `experiments/`, `lib/` 등 비-Jekyll 콘텐츠가 사이트 빌드에 섞여 들어갈 위험이 구조적으로 없다. 루트를 Pages 소스로 쓰고 `_config.yml`의 `exclude:` 목록으로 걸러내는 방식은, 새 최상위 디렉토리가 추가될 때마다 그 목록을 사람이 기억해서 갱신해야 하는 드리프트 위험이 있어 채택하지 않는다.
- **`lib/`은 항상 `docker/runner` 이미지 내부에서만 실행**: 호스트에 Python이 없어도 검증·차트·CSV 변환이 100% 동일하게 재현된다(3장 참고).

## 3. 크로스플랫폼 재현 전략

### 3.1 문제의 정확한 지점

AGENDA.md가 지적한 문제는 정확하다 — 원래 계약이던 `run.sh`(bash 스크립트)를 **호스트 셸에서 직접** 실행하면, bash 인터프리터가 기본 탑재되지 않은 Windows 네이티브(PowerShell/cmd, WSL 없이)에서 그대로 실패한다. 이 문서는 "Windows 사용자는 WSL2 셸을 열어서 쓰라"는 방식을 채택하지 않는다 — 그것은 WSL2라는 별도 환경 설정을 사용자에게 떠넘기는 것이지 "Windows 네이티브에서 동일하게 재현"이 아니다.

### 3.2 채택한 해법 — 무거운 로직을 호스트 셸에서 아예 실행하지 않는다

이미 확정된 아키텍처 A(Docker 공통 기판)를 끝까지 밀어붙인다. 표준 실행 계약을 `run.sh` 대신 다음 한 줄로 정의한다.

```
docker compose -f templates/<slug>/docker-compose.yml run --rm runner ./experiment.sh --params params.yml --out results [--smoke]
```

`experiment.sh`(bash)는 **호스트에서 절대 실행되지 않는다.** `runner` 서비스가 만드는 컨테이너(항상 Linux) 내부에서만 실행된다. 호스트가 하는 일은 `docker`라는 단일 정적 바이너리를 호출하는 것뿐이다. 이 명령이 macOS Terminal, Windows PowerShell/cmd, Linux bash/zsh에서 **글자 하나 다르지 않게 동일하게 동작하는** 이유를 구체적으로 짚는다.

1. **이 명령 문자열에는 쉘 전용 문법이 전혀 없다.** `$()`, 백틱, 파이프(`|`), 와일드카드 글로빙, `&&` 연결을 host 명령에서 절대 쓰지 않는다 — "프로그램명 + 플래그" 나열만 사용한다. PowerShell, cmd.exe, bash, zsh는 각자의 파서로 토큰화하더라도 이런 형태의 명령은 결과적으로 `docker`에 전달되는 argv 배열이 동일하다. (반례: `rm results/*.png` 같은 쉘 글로빙 의존 명령은 host에서 절대 쓰지 않는다 — 여러 파일을 다뤄야 하면 `lib/chart.py` 내부에서 Python의 `glob`으로 처리하고, host 명령은 항상 단일 호출로 유지한다.)
2. **`experiment.sh`는 항상 Linux 컨테이너 내부에서 실행된다.** 컨테이너 OS는 호스트 OS와 무관하게 항상 Linux이므로 "Windows에 bash가 없다"는 문제 자체가 발생하지 않는다. Windows 사용자는 bash를 설치할 필요가 전혀 없다.
3. **`docker`/`docker compose` CLI 자체가 3개 OS 모두에서 공식 배포되는 동일 버전의 네이티브 바이너리다.** Docker Desktop(Mac/Windows) 또는 Docker Engine + Compose v2 플러그인(Linux) 설치가 이 프로젝트 전체에서 유일한 필수 사전 요구사항이다. Python, Ruby, bash, matplotlib, Task 등 무엇도 호스트에 설치할 필요가 없다 — 검증(`lib/validate_results.py`)·CSV 변환(`lib/to_csv.py`)·차트 생성(`lib/chart.py`)·심지어 Jekyll 로컬 미리보기까지 전부 같은 원칙(호스트에는 `docker` 호출만)을 따른다.
4. **`docker compose` V2 플러그인 표기만 쓴다.** 하이픈이 있는 레거시 `docker-compose`(V1, 폐지됨)는 최신 Windows Docker Desktop에 기본 포함되지 않아 명령어 불일치를 만들 수 있다. README·CONTRIBUTING·CI 전부 공백 포함 `docker compose` 표기로 통일하고, 사전 요구사항에 `docker compose version`(v2.20 이상) 확인 절차를 명시한다.

### 3.3 WSL2에 대한 명시적 입장

WSL2를 "사용자가 열어서 명령을 치는 별도 환경"으로 요구하지 않는다. Windows에서 Docker Desktop은 WSL2를 백엔드로 쓰지만 사용자가 WSL2 셸 안에서 작업할 필요는 없다 — 설치 후 PowerShell에서 위 `docker compose run ...` 한 줄만 치면 된다.

다만 "설치 마법사가 전부 자동으로 처리한다"고 과장하지 않는다. Docker Desktop의 Windows 요구사항(WSL 기능 활성화, BIOS 가상화 활성화, WSL 커널 버전)은 깨끗한 머신에서 별도 조치가 필요할 수 있다. 그래서 README의 Windows 설치 절차는 `winget install Docker.DockerDesktop` 한 줄이 아니라 **preflight 확인 절차**를 함께 싣는다:

1. `wsl --status` — WSL2가 활성인지 확인 (없으면 관리자 PowerShell에서 `wsl --install` 후 재부팅)
2. Docker Desktop 설치 (`winget install Docker.DockerDesktop`) 후 실행, "WSL 2 based engine"(기본값) 유지
3. `docker compose version` — v2.20 이상인지 확인 (3개 OS 공통 preflight)
4. `docker run --rm hello-world` — 데몬이 실제로 컨테이너를 돌릴 수 있는지 확인 (3개 OS 공통 preflight)

WSL2 백엔드(Hyper-V 백엔드 아님)를 기본 전제로 두는 이유: WSL2가 신규 설치의 기본값이고, 향후 Kubernetes 실험(`kind`/`k3d`)처럼 컨테이너 안에서 다시 Docker를 제어하는 Docker-outside-of-Docker(DooD) 패턴이 `/var/run/docker.sock` 마운트로 동작하려면 WSL2 백엔드가 필요하기 때문이다(Hyper-V 백엔드에서는 이 소켓 경로 매핑이 신뢰할 수 없다). Hyper-V 백엔드 자체는 Docker가 여전히 지원하지만, 이 프로젝트의 검증 매트릭스(9장)는 WSL2 백엔드만 커버한다.

### 3.4 사전 설치 도구 (3개 OS 공통, 이것만 있으면 됨)

| OS | 필수: Docker | 필수: git |
|---|---|---|
| macOS | `brew install --cask docker` | `brew install git` (또는 Xcode CLT) |
| Windows | `winget install Docker.DockerDesktop` (WSL2 backend 기본값 유지) | `winget install Git.Git` |
| Linux | `curl -fsSL https://get.docker.com \| sh` + `sudo usermod -aG docker $USER` | `sudo apt install git` (배포판별) |

버전 하한: Docker Engine ≥ 24.x, Compose V2(`docker compose`, 최소 v2.20). 이 외 어떤 언어/도구도 호스트 필수 요구사항으로 두지 않는다 — Task(go-task) 같은 편의 바이너리조차 의도적으로 도입하지 않는다(0장 참고, 심사에서 지적된 크로스플랫폼 검증 표면 증가를 피하기 위함).

### 3.5 남은 크로스플랫폼 함정과 구체적 해결책

- **CRLF로 인한 셸 스크립트 손상**: Windows에서 `git clone` 시 `core.autocrlf`가 `experiment.sh`를 CRLF로 변환하면 Linux 컨테이너 안에서 `bash: $'\r': command not found` 오류가 난다. 저장소 루트 `.gitattributes`로 강제한다.
  ```
  * text=auto eol=lf
  *.sh text eol=lf
  *.py text eol=lf
  *.yml text eol=lf
  *.png binary
  *.jpg binary
  ```
- **호스트 볼륨 경로**: `docker-compose.yml`의 `volumes:`는 항상 상대 경로(`./:/workspace`)만 사용한다. 호스트 절대경로 문자열을 조립하지 않으므로 Windows의 `C:\Users\...` 표기 문제 자체가 발생하지 않고, Mac/Windows Docker Desktop의 파일 공유 설정에도 의존하지 않는다.
- **CPU 아키텍처(Apple Silicon arm64 vs amd64)**: `docker/runner`와 Redis/ClickHouse 등 공식 이미지는 멀티아치를 지원하지만, 신규 템플릿이 amd64 전용 이미지를 쓰면 M-시리즈 Mac에서 QEMU 에뮬레이션으로 느려지거나 실패할 수 있다. 9장 검증 프로세스에 `docker manifest inspect <image>` 확인을 체크리스트 항목으로 명시한다.
- **헤드리스 차트 렌더링**: `docker/runner/Dockerfile`에서 `ENV MPLBACKEND=Agg`를 설정하고 `lib/chart.py` 코드에서도 `matplotlib.use("Agg")`를 최상단에 강제한다(이중 안전장치). 컨테이너에는 애초에 디스플레이가 없으므로 Windows의 Tcl/Tk 부재, Linux 헤드리스 환경의 디스플레이 부재 문제가 원천적으로 개입할 여지가 없다.
- **Claude Code 자체의 쉘 차이**: Claude Code가 네이티브 Windows에서 Bash 도구를 실행할 때 내부적으로 어떤 쉘을 쓰든, 3.2절의 원칙(쉘 확장 문법 미사용)을 지키는 한 결과는 동일하다. `run.sh`를 유일한 진입점으로 두지 않은 근본적인 이유가 바로 이것이다 — bash 문법이 명령 문자열 안에 전혀 없으므로 "어떤 쉘이 해석하는가"가 결과에 영향을 주지 않는다.

## 4. 공통 계약 상세

`CONTRACT.md`(리포 루트)가 아래 3개 계약의 단일 정본이다. 계약을 변경하는 PR은 기존 템플릿 전부에 대한 하위 호환 영향을 PR 설명에 명시해야 한다.

### 4.1 실행 진입점 인터페이스

**호스트에서 사람과 Claude Code가 동일하게 입력하는 유일한 명령 (실제로 한 줄):**

```
docker compose -f templates/<slug>/docker-compose.yml run --rm runner ./experiment.sh --params params.yml --out results [--smoke]
```

> **표기 규약**: 이 문서의 다른 코드 블록에서 쓰는 `\` 줄연장은 지면 가독성을 위한 것일 뿐이다. `\` 줄연장은 POSIX 쉘 전용 문법이라(PowerShell은 백틱, cmd는 `^`) 그대로 복사하면 Windows에서 깨진다 — **사용자에게 노출되는 모든 문서(README/CONTRIBUTING)의 명령은 반드시 한 줄로 표기한다.** 이것도 3.2절 "호스트 명령에 쉘 문법 금지" 원칙의 일부다.

| 요소 | 역할 |
|---|---|
| `templates/<slug>/docker-compose.yml` | "Docker 위에서 동작한다"는 아키텍처 A 원칙의 실체. `runner` 서비스(공용 이미지 확장) + 실험 대상 인프라 서비스(자유 구성) |
| `templates/<slug>/experiment.sh` | 컨테이너 **내부**에서만 실행되는 실제 측정 로직. `#!/usr/bin/env bash` + `set -euo pipefail` 헤더 필수 |
| `--params <path>` | 실험 파라미터 YAML (기본 `params.yml`). 도메인별 파라미터는 여기 담고, CLI 플래그 표준 집합에는 넣지 않는다(계약을 최소로 유지) |
| `--out <dir>` | 산출물 디렉토리 (기본 `results`). `results.json`/`results.csv`/`charts/`가 이 아래 생성됨 |
| `--smoke` | 축소 실행 모드. `params.yml`의 `smoke:` 블록으로 스윕 범위를 오버라이드해 1분 내외로 종료. CI 스모크 테스트와 사람의 온보딩 확인에 동일하게 쓰임 |
| exit code | 0이 아니면 파이프라인은 그 지점에서 즉시 중단하고 stderr 전체를 보고한다(무음 실패 금지) |

**검증/차트/발행도 같은 원칙**(호스트에는 `docker compose` 호출만 남긴다):

```
docker compose -f docker/runner/docker-compose.yml run --rm runner \
  python -m lib.validate_results experiments/<slug>/results/results.json

docker compose -f docker/runner/docker-compose.yml run --rm runner \
  python -m lib.to_csv experiments/<slug>/results/results.json experiments/<slug>/results/results.csv

docker compose -f docker/runner/docker-compose.yml run --rm runner \
  python -m lib.chart --results experiments/<slug>/results/results.json --out experiments/<slug>/results/charts/
```

여기서 `-v "$PWD:/workspace"` 같은 볼륨 플래그를 호스트 명령에 쓰지 않는 이유는 3.2절의 원칙 그 자체다 — `$PWD`는 쉘 변수 확장이라 cmd.exe에서 리터럴 문자열로 전달돼 깨진다. 대신 `docker/runner/docker-compose.yml`이 리포 루트를 상대 경로로 마운트한다(Compose의 상대 경로는 **compose 파일의 위치 기준**으로 해석되므로, 사용자가 어느 디렉토리에서 명령을 치든 결과가 동일하다):

```yaml
# docker/runner/docker-compose.yml
services:
  runner:
    build: .
    image: ds-labs/runner:1.0.0
    volumes:
      - ../..:/workspace        # 리포 루트 (compose 파일 기준 상대 경로)
    working_dir: /workspace
```

**정리(teardown)**: `docker compose -f templates/<slug>/docker-compose.yml down -v` — 잔여 컨테이너/볼륨이 없어야 한다(9장 참고).

**공용 이미지 빌드(최초 1회, 또는 `lib/`·`schemas/` 변경 시)**:
```
docker compose -f docker/runner/docker-compose.yml build
```
`ds-labs/runner:1.0.0`은 레지스트리에 배포되지 않는 **로컬 태그**이므로, 이를 `FROM`으로 확장하는 템플릿(`templates/<slug>/Dockerfile`)을 실행하기 전에 이 빌드가 반드시 선행되어야 한다 — 퀵스타트와 CI 모두 이 순서를 고정한다. `docker/runner/Dockerfile`은 `lib/`와 `schemas/`를 이미지 빌드 시점에 `/app`에 복사하고 `PYTHONPATH=/app`으로 설정한다. 이미지 태그(`ds-labs/runner:1.0.0`)는 `template_version`과 별개로 관리되며, 각 템플릿의 `docker-compose.yml`/`Dockerfile`은 자신이 작성될 당시의 태그를 고정 참조한다 — 계약(스키마)이 나중에 바뀌어도 과거 템플릿이 조용히 깨지지 않는다.

### 4.2 `results.json` / `results.csv` 스키마

**원칙: `results.json`이 유일한 진실 원천(source of truth), `results.csv`는 `lib/to_csv.py`가 자동 파생시키는 산출물이다.** 두 포맷 모두 **롱 포맷(long format)** — 한 행이 하나의 측정점 — 을 쓴다. 동시성 스윕이든, K8s 파드 수 스윕이든, 어떤 실험이든 동일한 파서·차트 코드로 처리하기 위함이다.

두 필드는 표현력을 위해 존재한다(둘 다 롱포맷 원칙을 깨지 않는 최소 확장이다):
- **`series`**: 같은 metric 안의 하위 계열 구분. 예: `redis-benchmark -t set,get`은 동시성마다 SET/GET 두 결과를 내므로, `metric: "p99_latency_ms"` + `series: "SET"`/`series: "GET"`으로 구분한다(없으면 `null`). `lib/chart.py`는 (metric)별로 1개 PNG를 만들되, series가 여럿이면 한 차트에 여러 선을 그리고 범례를 붙인다.
- **`x`의 `number | string` 유니온**: 동시성처럼 수치 스윕이면 숫자, GC 종류(G1/Parallel/ZGC)·파일시스템(ext4/xfs/btrfs)처럼 범주형 비교면 문자열. `lib/chart.py`는 한 metric의 `x`가 전부 숫자면 선 그래프, 하나라도 문자열이면 막대 그래프를 그린다(혼용은 검증 단계에서 거부). `TOPICS.md`의 46개 안건 중 범주형 비교 실험이 다수라 이 유니온이 없으면 스키마가 첫 확장에서 바로 깨진다.

`schemas/results.schema.json` (JSON Schema draft 2020-12):

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://ds-labs.local/schemas/results.schema.json",
  "title": "ds_labs results.json",
  "type": "object",
  "required": ["schema_version", "experiment", "run", "parameters", "data", "status"],
  "properties": {
    "schema_version": { "const": "1.0" },
    "experiment": {
      "type": "object",
      "required": ["id", "agenda", "template", "template_version"],
      "properties": {
        "id": { "type": "string", "pattern": "^[a-z0-9-]+$" },
        "agenda": { "type": "string" },
        "template": { "type": "string" },
        "template_version": { "type": "string" }
      }
    },
    "run": {
      "type": "object",
      "required": ["run_id", "started_at", "finished_at", "smoke"],
      "properties": {
        "run_id": { "type": "string" },
        "started_at": { "type": "string", "format": "date-time" },
        "finished_at": { "type": "string", "format": "date-time" },
        "duration_sec": { "type": "number" },
        "smoke": { "type": "boolean" },
        "environment": {
          "type": "object",
          "properties": {
            "arch": { "type": "string" },
            "cpu_cores": { "type": "integer" },
            "memory_gb": { "type": "number" }
          }
        }
      }
    },
    "parameters": { "type": "object" },
    "data": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["metric", "series", "x_label", "x", "y", "unit"],
        "properties": {
          "metric":  { "type": "string" },
          "series":  { "type": ["string", "null"] },
          "x_label": { "type": "string" },
          "x":       { "type": ["number", "string"] },
          "y":       { "type": "number" },
          "unit":    { "type": "string" },
          "note":    { "type": ["string", "null"] }
        }
      }
    },
    "summary": { "type": "object" },
    "status": { "enum": ["success", "failed", "partial"] },
    "notes": { "type": "array", "items": { "type": "string" } }
  }
}
```

**예시 `results.json`** (레디스 파일럿, 10장 참고):

```json
{
  "schema_version": "1.0",
  "experiment": {
    "id": "redis-blocking-threshold",
    "agenda": "Redis 단일 인스턴스는 초당 몇 건의 SET/GET 요청부터 P99 레이턴시가 급격히 튀며 이벤트 루프가 포화 상태에 진입하는가?",
    "template": "redis-blocking-threshold",
    "template_version": "1.0.0"
  },
  "run": {
    "run_id": "2026-07-20T10-00-00Z-a1b2c3",
    "started_at": "2026-07-20T10:00:00Z",
    "finished_at": "2026-07-20T10:04:12Z",
    "duration_sec": 252,
    "smoke": false,
    "environment": { "arch": "arm64", "cpu_cores": 8, "memory_gb": 7.8 }
  },
  "parameters": {
    "concurrency_sweep": [1, 10, 50, 100, 250, 500, 1000, 2000, 4000],
    "requests_per_step": 100000,
    "sla_multiplier": 10
  },
  "data": [
    { "metric": "throughput_ops_sec", "series": "SET", "x_label": "concurrency", "x": 10,   "y": 9800,  "unit": "ops/sec", "note": null },
    { "metric": "throughput_ops_sec", "series": "SET", "x_label": "concurrency", "x": 2000, "y": 41200, "unit": "ops/sec", "note": "처리량 정체 관찰" },
    { "metric": "p99_latency_ms",     "series": "SET", "x_label": "concurrency", "x": 10,   "y": 1.2,   "unit": "ms",      "note": null },
    { "metric": "p99_latency_ms",     "series": "SET", "x_label": "concurrency", "x": 2000, "y": 24.6,  "unit": "ms",      "note": "baseline 대비 10배 초과" },
    { "metric": "p99_latency_ms",     "series": "GET", "x_label": "concurrency", "x": 2000, "y": 18.1,  "unit": "ms",      "note": null }
  ],
  "summary": { "blocking_threshold_concurrency": 2000, "baseline_p99_ms": 1.2 },
  "status": "success",
  "notes": []
}
```

**파생 `results.csv`** (컬럼은 `data[]` 필드와 1:1 고정 — 템플릿별 자유 컬럼을 허용하지 않는다. 파서가 어떤 실험이든 같은 컬럼셋을 기대할 수 있어야 자동 파싱이 신뢰성을 갖는다):

```csv
metric,series,x_label,x,y,unit,note
throughput_ops_sec,SET,concurrency,10,9800,ops/sec,
throughput_ops_sec,SET,concurrency,2000,41200,ops/sec,처리량 정체 관찰
p99_latency_ms,SET,concurrency,10,1.2,ms,
p99_latency_ms,SET,concurrency,2000,24.6,ms,baseline 대비 10배 초과
p99_latency_ms,GET,concurrency,2000,18.1,ms,
```

**`run.environment`의 의미**: `experiment.sh`가 실행되는 곳은 항상 Linux 컨테이너이므로, 컨테이너 안에서 관측 가능한 값만 담는다 — `arch`(`uname -m`, 호스트 CPU와 동일), `cpu_cores`(`nproc`, cgroup 제한 반영), `memory_gb`(cgroup 한도 또는 `/proc/meminfo`, Docker Desktop에서는 VM 크기). 물리 호스트의 OS(macOS/Windows/Linux)나 Docker Desktop 버전은 컨테이너 안에서 신뢰성 있게 알 수 없으므로 `results.json`에 넣지 않는다 — 그 정보는 크로스 OS 검증 기록(`VALIDATION_CHECKLIST.md`, 9장 4단계)이 담당한다.

**검증**: `python -m lib.validate_results <path>` (컨테이너 내부, `jsonschema` 라이브러리로 `schemas/results.schema.json` 대비 검증). 실패 시 exit 1 + 어떤 필드가 왜 틀렸는지 구체적 메시지를 표준에러에 출력한다(fail loud). 검증을 통과해야만 다음 단계(차트 생성)로 진행한다 — 스킬도 사람도 검증 실패를 우회하지 않는다.

### 4.3 `README.template.md` 구조

`templates/<slug>/README.template.md`는 `${TOKEN}` 치환식이며, 다음 순서를 고정한다(AGENDA.md가 지정한 순서와 동일):

```markdown
# ${TITLE}

- 날짜: ${DATE}
- 템플릿: ${TEMPLATE_NAME}
- 태그: ${TAGS}

## 안건
${QUESTION}

## 가설
${HYPOTHESIS}

## 구성
${SETUP}

## 방법
${METHOD}

## 결과
${RESULTS}

## 결론
${CONCLUSION}

## 다음 연구 과제
${NEXT_QUESTIONS}
```

토큰 집합(`TITLE DATE TEMPLATE_NAME TAGS QUESTION HYPOTHESIS SETUP METHOD RESULTS CONCLUSION NEXT_QUESTIONS`)은 `CONTRACT.md`에 정의된 표준이며, 임의로 새 토큰을 추가하지 않는다(스킬이 파싱 가능해야 하므로, 확장이 필요하면 `CONTRACT.md`를 먼저 개정한다). `RESULTS`/`CONCLUSION` 섹션에 등장하는 모든 수치는 반드시 `results.json`의 `data[]` 또는 `summary`에서 인용해야 하며, 문서에 없는 수치를 추측·생성하지 않는다(6장 스킬 절차에서 강제).

## 5. 차트/이미지 생성 방식

### 도구: Python + matplotlib 하나만, 항상 `runner` 컨테이너 내부에서 실행

새 차트 라이브러리(Plotly, D3, Vega 등)를 추가하지 않는다. 호스트에는 Python도 matplotlib도 설치하지 않는다 — `docker/runner/requirements.txt`에 버전이 고정된 이미지 안에서만 실행되므로, 컨트리뷰터마다 다른 로컬 환경(폰트, matplotlib 버전, OS별 렌더러)에 따라 차트가 미묘하게 달라지는 문제가 원천적으로 없다.

```
# docker/runner/requirements.txt
matplotlib==3.9.2
jsonschema==4.23.0
PyYAML==6.0.2
```

산출물은 항상 **정적 PNG**로 고정한다 — 마크다운 `![]()`에 바로 삽입 가능하고, Jekyll 빌드 시 JS 번들러/브라우저 렌더링이 전혀 필요 없다(7장 "별도 빌드 파이프라인 없음" 요건과 정확히 합치). 색상은 다크모드에 반응할 수 없으므로 라이트 배경으로 통일해 인쇄/블로그 양쪽에 안전하게 한다.

`lib/chart.py`:
```python
import matplotlib
matplotlib.use("Agg")          # 헤드리스 강제 (Dockerfile의 MPLBACKEND=Agg와 이중 안전장치)
import matplotlib.pyplot as plt

plt.style.use("/app/lib/style.mplstyle")   # 팔레트/dpi(150)/figsize(8x5) 정본 1개, 개별 커스터마이징 금지

def line_chart(rows, metric, out_path):
    """rows: results.json의 data[] 중 metric이 일치하는 항목들."""
    xs = [r["x"] for r in rows]
    ys = [r["y"] for r in rows]
    fig, ax = plt.subplots()
    ax.plot(xs, ys, marker="o")
    ax.set_xlabel(rows[0]["x_label"])
    ax.set_ylabel(f'{metric} ({rows[0]["unit"]})')
    ax.set_title(metric)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)
```

실행:
```
docker compose -f docker/runner/docker-compose.yml run --rm runner \
  python -m lib.chart --results experiments/<slug>/results/results.json --out experiments/<slug>/results/charts/
```

`lib/chart.py`의 `__main__`은 `data[]`를 `metric`별로 그룹화해 `line_chart()`를 반복 호출하고, 생성된 PNG 개수가 고유 `metric` 개수와 일치하는지 스스로 확인한 뒤 종료 코드로 성공/실패를 알린다(0개 생성이나 일부 누락은 실패로 간주 — 무음 실패 금지). 파일명 규칙: `charts/<metric>.png`(metric 필드명 그대로 슬러그화, 결정적이므로 발행 단계가 "이 metric에는 이 이미지"를 항상 예측 가능하게 매칭한다).

MVP에서는 차트 타입을 `line_chart` 하나만 둔다(YAGNI — 히트맵 등은 실제로 필요한 실험이 나왔을 때 추가). 더 정교한 색상/레이아웃이 필요해지면 `dataviz` 스킬을 참고해 `lib/style.mplstyle`을 확장한다.

## 6. Claude Code 스킬 설계

두 개의 스킬로 분리한다 — "안건 실행"과 "새 기술 스택 추가"는 트리거와 절차가 서로 달라, 하나로 합치면 프롬프트가 비대해지고 판단 경계가 흐려진다(Rule 2).

### 6.1 `.claude/skills/ds-lab-run-experiment/SKILL.md`

```yaml
---
name: ds-lab-run-experiment
description: >
  안건(연구 질문)을 받아 templates/ 아래 기존/신규 템플릿으로 실험을 실행하고,
  results.json/csv를 검증하고, 차트를 만들고, README를 채워 Jekyll에 발행한다.
  트리거: "실험 시작", "안건 실행해줘", "~는 얼마부터 ~할까?" 같은 연구 질문 형태의 요청,
  기존 experiments/<slug>/ 재실행 요청.
---
```

**절차** (스킬 안에만 존재하는 숨은 로직을 두지 않는다 — 모든 기계적 단계는 사람도 Claude 없이 동일한 명령을 그대로 타이핑해 재현할 수 있어야 한다):

1. **안건 명확화 (judgment, Rule 5)** — 사용자의 연구 질문을 성공 기준이 있는 형태로 재진술한다. 모호하면 코드를 건드리기 전에 반드시 되묻는다: 어떤 기술 스택인가? 기존 `templates/*/TEMPLATE.md` 중 재사용 가능한 것이 있는가? 안건을 kebab-case `experiment_id`로 확정한다(이후 Jekyll 슬러그와 1:1 대응하므로 이 시점에 고정).
2. **템플릿 선정 또는 위임** — `templates/` 하위 `TEMPLATE.md`를 훑어 일치하는 템플릿이 있는지 판단한다(model judgment). 없으면 사용자에게 확인 후 `ds-lab-new-template` 스킬로 위임한다.
3. **파라미터 설정 (judgment)** — `templates/<slug>/params.yml`을 안건에 맞게 조정한다. 이 단계만 모델 판단이 필요하다(Rule 5 — 결정적 변환이 아닌 곳에만 모델을 쓴다).
4. **실행 (결정적, 모델이 값을 임의로 바꾸지 않음)**
   ```
   docker compose -f templates/<slug>/docker-compose.yml run --rm runner \
     ./experiment.sh --params params.yml --out results --smoke
   ```
   먼저 `--smoke`로 파이프라인이 살아있는지 확인한 뒤, `--smoke` 없이 본 실행. exit code가 0이 아니면 즉시 중단하고 stderr 전체를 그대로 보고한다(Rule 12 — 실패를 숨기지 않는다). "완료"라고 보고하기 전에 반드시 `results/results.json` 존재 여부를 확인한다.
5. **검증**
   ```
   docker compose -f docker/runner/docker-compose.yml run --rm runner \
     python -m lib.validate_results templates/<slug>/results/results.json
   ```
   실패 시 결과를 폐기하고 원인(스키마 위반 필드)을 사용자에게 보고한다. 검증을 건너뛰고 다음 단계로 넘어가지 않는다.
6. **실험 디렉토리 확정** — `experiments/<YYYY-MM-DD>-<experiment_id>/`를 만들고 `results/`, `params.yml`, `agenda.md`(안건+가설 원문)를 옮긴다. **이 디렉토리가 이미 존재하면 조용히 덮어쓰지 않고 즉시 중단해 사용자에게 알린다**(append-only 원칙, fail loud). 같은 날 의도적 재실행이면 사용자 확인 후 `-run2`, `-run3` 서수 접미사를 붙인 새 디렉토리를 만든다 — 접미사가 붙으면 Jekyll 포스트 슬러그와 이미지 경로에도 동일하게 반영되어 기존 발행물을 덮어쓰지 않는다(7장).
7. **CSV 파생 + 차트 생성** — `results.csv`는 3대 계약의 일부이므로 이 단계에서 반드시 함께 생성한다(누락은 계약 위반).
   ```
   docker compose -f docker/runner/docker-compose.yml run --rm runner \
     python -m lib.to_csv experiments/<slug>/results/results.json experiments/<slug>/results/results.csv
   docker compose -f docker/runner/docker-compose.yml run --rm runner \
     python -m lib.chart --results experiments/<slug>/results/results.json --out experiments/<slug>/results/charts/
   ```
8. **README 작성 (judgment, 유일한 프로즈 작성 단계)** — `templates/<slug>/README.template.md`를 복사해 `experiments/<slug>/README.md`로 만들고 4.3절의 토큰을 채운다. **`결과`/`결론` 섹션의 모든 수치는 반드시 `results.json`의 `data[]` 또는 `summary`에서 직접 인용한다 — 추측 금지, 데이터 기반 서술 강제.** `다음 연구 과제`는 이번 결과에서 자연스럽게 파생되는 후속 질문 1~3개를 구체적으로 제안한다(`TOPICS.md`에 관련 항목이 있으면 참조).
9. **발행**
   ```
   docker compose -f docker/runner/docker-compose.yml run --rm runner \
     python -m lib.publish_post experiments/<slug>/
   ```
   → `docs/_posts/<date>-<slug>.md` + `docs/assets/images/<slug>/*.png` 생성(7장 참고).
10. **사람 확인 요청** — `git add / commit / push`는 스킬이 자동 실행하지 않는다. `git diff --stat`을 보여주고 사람이 직접 커밋/푸시하도록 안내한다(오배포 사고 방지). 스킵된 단계가 있으면(예: 검증 실패 후 강행) 반드시 명시한다 — "완료" 남용 금지(Rule 12).

**금지 사항**: `results.json`을 스키마에 맞추기 위해 손으로 값을 지어내지 않는다. 검증 실패를 무시하고 발행 단계로 넘어가지 않는다.

### 6.2 `.claude/skills/ds-lab-new-template/SKILL.md`

```yaml
---
name: ds-lab-new-template
description: >
  새 기술 스택(예: ClickHouse, Kubernetes, Kafka)을 위한 실험 템플릿을 templates/_skeleton에서
  스캐폴딩한다. 트리거: "새 템플릿 만들어줘", "~에 대한 실험 템플릿 추가해줘".
---
```

**절차**:
1. 스캐폴딩 — 역시 호스트 쉘 명령(`cp -r`은 cmd.exe에 없음)이 아니라 runner 컨테이너의 Python으로 수행한다(3.2절 원칙을 기여 경로에도 동일 적용):
   ```
   docker compose -f docker/runner/docker-compose.yml run --rm runner python -m lib.scaffold <new-slug>
   ```
   `lib/scaffold.py`가 `templates/_skeleton`을 `templates/<new-slug>`로 복사하고 `__TEMPLATE_NAME__` 토큰을 치환한다(대상이 이미 존재하면 실패 — fail loud).
2. `docker-compose.yml`에 대상 인프라 서비스를 정의한다 — "Docker 위에서 동작한다"는 원칙만 지키면 오케스트레이션 도구(단일 컨테이너/`docker-compose`/`kind`/`k3d` 등)는 자유. 볼륨은 항상 상대 경로만 사용한다(3.5절).
3. 도메인 전용 CLI가 필요하면 `Dockerfile`을 `FROM ds-labs/runner:1.0.0`으로 작성해 확장한다(공용 이미지에는 넣지 않는다).
4. `experiment.sh`의 `up/test/teardown` 로직을 구현한다 — 반드시 `schemas/results.schema.json`을 만족하는 `results.json`을 출력해야 하고, `--smoke` 모드로 1분 내외에 끝나야 한다.
5. `TEMPLATE.md`에 이 템플릿이 다루는 기술/전제조건/사용 예시를 적는다(`ds-lab-run-experiment` 스킬의 2단계가 이 파일을 읽고 템플릿을 선택한다).
6. 로컬 스모크 통과를 확인한 뒤(9장 검증 프로세스 1~3단계) **사람에게 diff 검토를 요청**한다 — 인프라 코드를 스킬이 임의로 실행 전 자동 커밋하지 않는다.

## 7. Jekyll/GitHub Pages 설정

### 배포 방식

GitHub 리포 Settings → Pages → **Build and deployment: Deploy from a branch → main / `docs`**. 이 설정 하나로 push 즉시 GitHub 서버 측 Jekyll이 자동 빌드한다. (내부적으로는 GitHub이 관리하는 Pages 워크플로우가 돌지만, 우리가 작성·유지보수하는 배포 파이프라인은 0줄이다 — AGENDA.md 4번 요건 "별도 빌드 파이프라인 없이 markdown push만으로 배포"의 실질을 만족한다.) 사용자 정의 GitHub Actions 워크플로우로 사이트를 빌드/배포하지 않는다. `.github/workflows/*.yml`은 코드 검증(9장)용이며 Pages 배포와는 무관하다.

`.nojekyll` 파일은 **절대 추가하지 않는다** — Jekyll 처리를 끄는 용도이며 이 요건과 정반대이므로 흔한 실수로 명시해둔다.

### `docs/_config.yml`

```yaml
title: ds_labs
description: "컴퓨터/인프라 실험을 재현 가능한 형태로 기록하는 실험 랩"
baseurl: /ds_labs        # 프로젝트 페이지(<user>.github.io/ds_labs) 필수 — 없으면 relative_url이 도메인 루트를 가리켜 이미지 404
url: https://<user>.github.io
repo_url: https://github.com/<org>/ds_labs   # publish_post.py가 experiment_url 생성에 사용
theme: minima
plugins:
  - jekyll-feed
  - jekyll-seo-tag
  - jekyll-sitemap
permalink: /:year/:month/:day/:title/
markdown: kramdown
```

`minima`를 채택하는 이유: `github-pages` gem의 공식 화이트리스트에 항상 포함되어 있어 GitHub Pages 원격 빌드가 "지원하지 않는 테마/플러그인" 오류로 실패할 위험이 없고, `_posts` 컬렉션·반응형 레이아웃이 이미 내장돼 있어 가장 빠르게 완성할 수 있다. `jekyll-feed`/`jekyll-seo-tag`/`jekyll-sitemap`도 모두 화이트리스트 플러그인이라 추가 빌드 설정이 필요 없다. 콘텐츠가 늘어 태그/검색 탐색이 필요해지면 그때 다른 테마 교체를 검토한다(지금 미리 도입하지 않음 — YAGNI, 11장 로드맵 참고).

`docs/`가 별도 하위 디렉토리이므로 `exclude:` 목록을 유지보수할 필요가 없다(2장 참고) — 이 점이 루트-레벨 Jekyll 대비 이 설계가 가진 구체적 이점이다.

### `docs/Gemfile` (로컬 미리보기 전용, 배포 경로 아님)

```ruby
source "https://rubygems.org"
gem "github-pages", group: :jekyll_plugins
```

로컬 미리보기가 필요한 사람은 호스트에 Ruby를 설치하는 대신 Docker로 실행할 수 있다(호스트 의존성 원칙과 일관). 단, 널리 알려진 `jekyll/jekyll` 이미지는 채택하지 않는다 — 수년간 갱신이 멈췄고 arm64 이미지가 없어 Apple Silicon에서 에뮬레이션으로 돌며, GitHub Pages의 실제 빌드 환경(`github-pages` gem이 고정하는 Jekyll 3.x — 정확한 버전은 pages.github.com/versions 참고)과 버전도 다르다. 대신 `docker/runner`와 같은 패턴으로 `docker/jekyll/docker-compose.yml`에 `ruby:3.3-slim` 기반 서비스를 정의하고(`docs/Gemfile`의 `github-pages` gem을 컨테이너 안에서 `bundle install`), 호스트 명령은 역시 쉘 변수 없는 한 줄로 유지한다:
```
docker compose -f docker/jekyll/docker-compose.yml up
```
이렇게 하면 미리보기가 실서버와 동일한 `github-pages` gem 버전으로 렌더링된다. 어디까지나 선택 사항이다 — Ruby도 이 컨테이너도 없이 실험 실행·발행 파이프라인 전체를 문제없이 수행할 수 있고, 최종 확인은 push 후 실제 GitHub Pages URL에서 하면 된다.

### 포스트 네이밍 규칙 및 Front matter

`docs/_posts/YYYY-MM-DD-<experiment_id>.md` — `<experiment_id>`는 `experiments/<date>-<experiment_id>/` 디렉토리명과 **문자 그대로 동일**해야 한다(발행물에서 원본 재현 코드로 역추적 가능하게 하는 유일한 규약). `lib/publish_post.py`가 자동 생성하므로 사람이 수동으로 파일명을 짓지 않는다(오타/형식오류로 Jekyll이 날짜를 못 읽는 사고 방지).

```yaml
---
layout: post
title: "Redis 단일 인스턴스는 초당 몇 건의 SET/GET 요청부터 P99 레이턴시가 급격히 튀는가?"
date: 2026-07-20 10:00:00 +0900
categories: [redis, performance]
tags: [redis, docker, load-test]
experiment_id: redis-blocking-threshold
experiment_url: https://github.com/<org>/ds_labs/tree/main/experiments/2026-07-20-redis-blocking-threshold
run_id: 2026-07-20T10-00-00Z-a1b2c3
---
```

`experiment_url`은 GitHub 리포의 실제 디렉토리 URL이다 — `experiments/`는 Pages 발행 소스(`docs/`) 바깥이라 사이트 상대 경로로 링크하면 404가 나므로, 발행물에서 재현 코드로의 역추적 링크는 반드시 리포 URL로 건다(`lib/publish_post.py`가 `_config.yml`의 `repo_url` 값으로 생성).

### baseurl 처리

`ds_labs`는 프로젝트 페이지(`https://<user>.github.io/ds_labs/`)이므로 이미지 경로는 반드시 Liquid `relative_url` 필터로 baseurl을 반영한다:
```
![Throughput vs concurrency]({{ '/assets/images/2026-07-20-redis-blocking-threshold/throughput_ops_sec.png' | relative_url }})
```
`lib/publish_post.py`는 `README.md`의 상대 이미지 경로(`results/charts/xxx.png`)를 이 Liquid 표현식으로 자동 치환하고, `results/charts/*.png`를 `docs/assets/images/<date>-<experiment_id>/`로 복사한다. 이미지 디렉토리명은 `experiments/` 디렉토리명·포스트 파일명과 동일한 `<date>-<experiment_id>` 슬러그를 쓴다 — `<experiment_id>`만 쓰면 같은 실험을 다른 날짜에 재실행했을 때 이전 발행물의 이미지를 덮어써 append-only 원칙이 깨진다.

## 8. CONTRIBUTING 가이드 핵심

`CONTRIBUTING.md`의 목차와 핵심 내용:

### 1. 5분 퀵스타트 (Mac/Windows/Linux 병기)
3.4절의 설치 표 + 아래 명령 시퀀스를 그대로 싣는다.
```
git clone https://github.com/<org>/ds_labs.git
cd ds_labs
docker compose -f docker/runner/docker-compose.yml build   # 최초 1회, 캐시됨
docker compose -f templates/redis-blocking-threshold/docker-compose.yml run --rm runner \
  ./experiment.sh --params params.yml --out results --smoke
```

### 2. 실험 루프 이해하기
안건 → 템플릿 선택/생성 → 실행 → 검증 → 차트 → README → 발행 다이어그램과, Claude를 쓰는 경로/사람이 직접 쓰는 경로가 **완전히 동일한 `docker compose` 명령**으로 수렴한다는 점을 명시(AGENDA.md 2번 하이브리드 실행 모델의 핵심 증거).

### 3. 새 템플릿 추가 절차 (체크리스트)
```
docker compose -f docker/runner/docker-compose.yml run --rm runner python -m lib.scaffold <new-slug>
# 이후 docker-compose.yml, (선택)Dockerfile, experiment.sh, params.yml, TEMPLATE.md 작성
```
- [ ] `docker-compose.yml`의 볼륨이 상대 경로만 쓰는가
- [ ] `experiment.sh`가 `--params --out --smoke`를 지원하는가
- [ ] `--smoke` 모드가 60초 내외로 끝나며 유효한 `results.json`을 만드는가
- [ ] `python -m lib.validate_results`가 통과하는가
- [ ] `python -m lib.chart`가 `data[]`의 고유 metric 수만큼 PNG를 생성하는가
- [ ] `docker compose ... down -v` 이후 `docker ps -a`에 잔여 컨테이너가 없는가
- [ ] `TEMPLATE.md`에 기술/전제조건/사용 예시가 있는가
- [ ] base image가 `docker manifest inspect`로 linux/amd64·linux/arm64 모두 확인되는가

### 4. 크로스플랫폼 검증 방법 (9장과 연동)
- PR 작성자는 최소 자신의 OS 1곳에서 성공 실행 로그를 PR에 첨부한다.
- CI(`contract-check.yml`, ubuntu-latest)가 실제 컨테이너 실행으로 자동 검증한다 — GitHub 호스팅 러너 중 Linux 컨테이너를 실제로 돌릴 수 있는 것은 ubuntu뿐이다(macOS 러너는 Docker 미탑재 + Apple Silicon 중첩 가상화 미지원, Windows 러너는 Linux 컨테이너 미지원).
- CI(`static-check.yml`, windows-latest)는 `docker compose config -q`, 스키마 자체 유효성, CRLF 손상 여부 등 **정적 계약만** 검사한다.
- 신규 템플릿은 병합 전 macOS/Windows 환경을 가진 사람이 `VALIDATION_CHECKLIST.md`에 따라 실제 Docker Desktop에서 수동 스모크런을 각 1회 수행하고 체크를 남긴다 — CI가 못 미치는 부분을 사람이 명시적으로 메꾸며, "해당 OS CI가 없으니 검증 없이 통과"는 허용하지 않는다(Rule 12).

### 5. 코드 스타일
- 외부 의존성 추가 전 "정말 stdlib/이미 있는 라이브러리로 안 되는가"를 자문한다. `docker/runner/requirements.txt`에 항목을 늘리는 PR은 사유를 명시한다.
- `experiment.sh`는 `set -euo pipefail` 헤더 필수, 표준 플래그(`--params --out --smoke`)를 벗어나지 않는다.
- 검증·차트·발행 로직은 항상 `runner` 컨테이너 안에서만 실행한다 — 호스트 언어 의존성을 늘리지 않는다.
- `CONTRACT.md`(계약 자체) 변경 PR은 기존 템플릿 전부에 대한 하위 호환 영향을 설명에 명시한다.

### 6. 문서 신뢰성 규칙
README/포스트에 적는 모든 수치는 `results.json`에서 인용한다. PR에는 안건 원문, `results.json`의 headline 수치, 다음 연구 과제 제안 1개 이상을 포함한다.

## 9. 새 템플릿 검증 프로세스 (여러 OS 검증 포함)

### 1단계 — 로컬 자기검증 (기여자, 자신의 OS)
```
docker compose -f templates/<slug>/docker-compose.yml run --rm runner \
  ./experiment.sh --params params.yml --out results --smoke
docker compose -f docker/runner/docker-compose.yml run --rm runner \
  python -m lib.validate_results templates/<slug>/results/results.json
docker compose -f docker/runner/docker-compose.yml run --rm runner \
  python -m lib.to_csv templates/<slug>/results/results.json templates/<slug>/results/results.csv
docker compose -f docker/runner/docker-compose.yml run --rm runner \
  python -m lib.chart --results templates/<slug>/results/results.json --out templates/<slug>/results/charts/
```
다섯 단계(실행/검증/CSV/차트/아래 정리 확인)가 모두 exit 0이어야 PR을 올린다.

### 2단계 — 정리(teardown) 확인
```
docker compose -f templates/<slug>/docker-compose.yml down -v
docker ps -a --filter "label=com.docker.compose.project=<slug>"
```
잔여 컨테이너/볼륨이 없어야 한다. 리소스 누수는 "재현 가능성"을 해치는 가장 흔한 사고이므로 명시적으로 확인한다.

### 3단계 — CI 자동 검증

CI에서 실제 컨테이너 스모크런이 가능한 러너는 **ubuntu-latest뿐이다.** GitHub 호스팅 `macos-latest` 러너에는 Docker가 설치되어 있지 않고, Apple Silicon 기반 러너는 중첩 가상화(nested virtualization)를 지원하지 않아 colima 같은 우회로도 Linux 컨테이너를 돌릴 수 없다. `windows-latest` 러너 역시 Linux 컨테이너 실행을 지원하지 않는다. 따라서 CI 스모크런은 Linux만 자동이고, **macOS와 Windows는 4단계 수동 검증으로 커버한다** — 이 한계를 문서에서 숨기지 않는다.

변경된 템플릿 슬러그는 base 브랜치와의 diff에서 결정적으로 추출한다(`${{ env.SLUG }}` 같은 미정의 변수에 의존하지 않는다). CI 스텝 내부는 항상 Linux bash이므로 쉘 문법 사용이 무방하다 — 3.2절의 "쉘 문법 금지"는 사람이 손으로 치는 호스트 명령에 대한 원칙이다.

`.github/workflows/contract-check.yml` (ubuntu-latest, **실제 컨테이너 실행**):
```yaml
name: contract-check
on:
  pull_request:
    paths: ["templates/**", "lib/**", "schemas/**", "docker/**", ".gitattributes"]
jobs:
  detect:
    runs-on: ubuntu-latest
    outputs:
      slugs: ${{ steps.diff.outputs.slugs }}
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - id: diff
        run: |
          # 변경된 templates/<slug>/ 목록을 JSON 배열로 추출 (_skeleton 제외).
          # lib/·schemas/ 변경 시에는 전체 템플릿을 순회해 계약 파손을 감지한다.
          if git diff --name-only origin/${{ github.base_ref }}...HEAD | grep -qE '^(lib|schemas)/'; then
            slugs=$(ls -d templates/*/ | cut -d/ -f2 | grep -v '^_skeleton$' | jq -R . | jq -sc .)
          else
            slugs=$(git diff --name-only origin/${{ github.base_ref }}...HEAD -- templates/ \
              | cut -d/ -f2 | sort -u | grep -v '^_skeleton$' | jq -R . | jq -sc .)
          fi
          echo "slugs=$slugs" >> "$GITHUB_OUTPUT"
  smoke:
    needs: detect
    if: needs.detect.outputs.slugs != '[]'
    runs-on: ubuntu-latest
    strategy:
      matrix:
        slug: ${{ fromJson(needs.detect.outputs.slugs) }}
    steps:
      - uses: actions/checkout@v4
      - run: docker compose -f docker/runner/docker-compose.yml build
      - run: |
          docker compose -f templates/${{ matrix.slug }}/docker-compose.yml run --rm runner \
            ./experiment.sh --params params.yml --out results --smoke
      - run: |
          docker compose -f docker/runner/docker-compose.yml run --rm runner \
            python -m lib.validate_results templates/${{ matrix.slug }}/results/results.json
      - run: |
          docker compose -f docker/runner/docker-compose.yml run --rm runner \
            python -m lib.to_csv templates/${{ matrix.slug }}/results/results.json templates/${{ matrix.slug }}/results/results.csv
      - run: |
          docker compose -f docker/runner/docker-compose.yml run --rm runner \
            python -m lib.chart --results templates/${{ matrix.slug }}/results/results.json --out templates/${{ matrix.slug }}/results/charts/
      - run: docker compose -f templates/${{ matrix.slug }}/docker-compose.yml down -v
```
CI 스모크런은 로컬 자기검증(1단계)과 동일한 다섯 단계(실행/검증/CSV/차트/정리)를 그대로 수행한다 — CI와 사람의 검증 경로가 갈라지지 않게 한다.
`.github/workflows/static-check.yml` (windows-latest, **정적 검증만**):
```yaml
name: static-check
on:
  pull_request:
    paths: ["templates/**", "lib/**", "schemas/**", "docker/**", ".gitattributes"]
jobs:
  static:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - shell: pwsh
        run: |
          # Windows 기본 설정(core.autocrlf 영향권)으로 체크아웃한 *.sh/*.py에 CR이 섞였는지 명시 검사
          $bad = Get-ChildItem -Recurse -Include *.sh,*.py | Where-Object {
            (Get-Content $_ -Raw) -match "`r"
          }
          if ($bad) { $bad | ForEach-Object { Write-Error "CRLF detected: $_" }; exit 1 }
      - shell: pwsh
        run: |
          Get-ChildItem templates -Directory | Where-Object Name -ne '_skeleton' | ForEach-Object {
            docker compose -f "templates/$($_.Name)/docker-compose.yml" config -q
            if ($LASTEXITCODE -ne 0) { exit 1 }
          }
      - shell: pwsh
        run: python -m json.tool schemas/results.schema.json | Out-Null
      # 주의: 이 job은 Linux 컨테이너 스모크런을 수행하지 않는다 — 4단계에서 사람이 메꾼다.
```
`static-check`가 Windows 러너에서 검증하는 것은 셋이다 — Windows 체크아웃에서 스크립트가 CRLF로 손상되지 않는가(첫 스텝이 명시적으로 검사, `.gitattributes` 오류가 여기서 드러난다), compose 파일이 문법적으로 유효한가, 스키마 파일이 유효한 JSON인가. 스키마의 **의미** 검증(JSON Schema로서 올바른가)은 Linux 스모크런의 `lib.validate_results` 실행이 커버한다.

### 4단계 — macOS/Windows 수동 검증 (필수, CI로 대체하지 않음)

3단계에서 설명했듯 CI 스모크런은 Linux만 가능하므로, macOS와 Windows는 사람이 실제 Docker Desktop에서 1회 수행하고 `VALIDATION_CHECKLIST.md`에 기록한다:
```markdown
## <slug> 템플릿 검증
- [ ] Linux: `--smoke` 통과 (CI 자동, 실행: contract-check #___)
- [ ] macOS: `--smoke` 통과 (수동, 실행자: ___, 날짜: ___, Docker Desktop 버전: ___, arch: arm64/amd64)
- [ ] Windows: `--smoke` 통과 (수동, 실행자: ___, 날짜: ___, Docker Desktop 버전: ___)
- [ ] 3개 OS의 results.json이 동일한 headline 수치(±허용오차)를 냈는가
```
이 체크가 채워져야 머지한다. (주 개발 환경이 macOS라면 macOS 항목은 1단계 로컬 자기검증 기록으로 갈음할 수 있다 — 별도 실행을 중복 요구하지 않는다.)

### 5단계 — 이미지 아키텍처 확인
```
docker manifest inspect <base-image>
```
linux/amd64·linux/arm64 둘 다 없으면 템플릿 `TEMPLATE.md`에 "Apple Silicon에서 QEMU 에뮬레이션으로 느릴 수 있음"을 명시하거나 대체 이미지를 찾는다.

### 6단계 — 문서 완결성 확인
`TEMPLATE.md`에 기술/전제조건이 있는지, `README.template.md`의 `${TOKEN}`이 `CONTRACT.md`의 표준 토큰 집합과 일치하는지 확인한다(임의 토큰 추가 금지).

### 머지 기준
`contract-check`(ubuntu, 실제 스모크런) 통과, `static-check`(windows, 정적) 통과, `VALIDATION_CHECKLIST.md`의 macOS·Windows 수동 검증 체크 완료, 6단계 문서 완결성 확인 — 넷 다 충족해야 머지한다.

## 10. 첫 파일럿 실험 추천

> **주의**: `AGENDA.md`는 "레디스 블로킹 임계치"를 확정된 파일럿이 아니라 **개념 설명용 예시**로만 언급했고, "첫 파일럿은 아직 미정 — 템플릿/구조부터 먼저 완성"하기로 명시적으로 결정했다. 아래는 그 결정을 존중해 **11장 로드맵 Phase 0~1에서 구조를 먼저 증명한 뒤 사용할 추천 후보**이며, 팀이 최종 확정해야 한다.

### 선정 기준
1. 단일/이중 컨테이너로 충분해 오케스트레이션 복잡도가 낮을 것(K8s처럼 `kind`/`k3d` 부트스트랩이 필요한 실험은 제외 — 3대 계약 자체를 검증하기 전에 인프라 복잡도까지 떠안지 않는다).
2. 측정 지표가 1~2개 숫자로 명확히 떨어져 4.2절의 롱포맷 스키마를 검증하기 쉬울 것.
3. `--smoke` 모드로 1분 내외 축소 가능해 CI 예산에 맞을 것.
4. 안건이 명확한 가설/결론 구조로 떨어질 것.

### 추천: `TOPICS.md` #1 — "Redis 단일 인스턴스는 초당 몇 건의 SET/GET 요청부터 P99 레이턴시가 급격히(10배 이상) 튀며 이벤트 루프가 포화 상태에 진입하는가?"

이 안건을 추천하는 이유는 AGENDA.md의 예시("레디스는 얼마의 요청이 들어올 때 블로킹이 걸릴까?")와 개념적으로 정확히 대응하면서도, 별도로 진행된 `TOPICS.md` 워크플로우에서 이미 캐시 카테고리 **#1(초급)**으로 구체화돼 있어 추가 브레인스토밍 없이 바로 스펙을 확정할 수 있기 때문이다. 위 4가지 기준도 모두 만족한다.

`TOPICS.md`가 명시한 필요 스택은 `Docker(redis:7-alpine, cpuset/cpus 제한)`, `memtier_benchmark/redis-benchmark`, `redis_exporter + Prometheus + Grafana`다. 다만 **이 문서는 첫 파일럿의 v1 범위를 의도적으로 축소한다** — Prometheus/Grafana 관측 스택은 3대 계약 자체를 증명하는 walking skeleton 단계에서는 불필요한 복잡도이므로(YAGNI, 0장의 Phase 게이팅 원칙), `redis-benchmark`의 `--csv` 출력과 `INFO` 명령 폴링만으로 `results.json`을 채우는 v1을 먼저 완성하고, `redis_exporter+Prometheus+Grafana` 기반의 시계열 관측은 이 파일럿이 계약을 증명한 뒤 별도 후속 실험(`TOPICS.md`의 다른 캐시 카테고리 항목, 예: fork/BGSAVE 레이턴시 스파이크)에서 도입을 검토한다.

### 구체적 구현 (v1)

- **템플릿**: `templates/redis-blocking-threshold/`
- **인프라**: `docker-compose.yml`에 `redis`(`redis:7-alpine`, `--maxmemory-policy noeviction`, `cpus: 2` 제한) + `runner`(공용 이미지를 확장한 `Dockerfile`이 `redis-tools` 설치) 2개 서비스.
- **부하 도구**: 별도 커스텀 클라이언트를 작성하지 않고 Debian `redis-tools` 패키지에 포함된 **`redis-benchmark`**를 `runner` 컨테이너에서 실행한다(추가 의존성 최소화):
  ```
  redis-benchmark -h redis -t set,get -n 100000 -c <concurrency> --csv
  ```
  **`--csv` 모드를 쓰는 이유**: `-q`(quiet) 출력에는 rps와 p50만 표시되고 p99가 없다. `--csv` 출력은 `"test","rps","avg_latency_ms","min_latency_ms","p50_latency_ms","p95_latency_ms","p99_latency_ms","max_latency_ms"` 고정 헤더의 CSV라서 p99를 포함하고, 정규식이 아닌 표준 CSV 파싱으로 처리할 수 있어 파싱 신뢰성도 더 높다. `experiment.sh`는 `params.yml`의 `concurrency_sweep`(`[1, 10, 50, 100, 250, 500, 1000, 2000, 4000]`)을 순회하며 위 명령을 반복 호출하고, CSV의 `rps`/`p99_latency_ms` 컬럼을 `results.json`의 `data[]`에 `throughput_ops_sec`/`p99_latency_ms` 항목으로 적재한다. `concurrency=1`(baseline)의 p99 대비 `sla_multiplier`(기본 10배)를 최초로 넘는 concurrency를 `summary.blocking_threshold_concurrency`로 기록한다.
- **experiment_id**: `redis-blocking-threshold`
- **예상 산출물**: `experiments/<date>-redis-blocking-threshold/results/charts/throughput_ops_sec.png`, `p99_latency_ms.png` 2개.
- **가설 예시**: "Redis는 단일 스레드 이벤트 루프이므로 concurrency가 baseline 대비 p99 10배 임계값을 넘는 지점부터 이벤트 루프가 포화되어 처리량은 정체되고 지연시간이 급증한다."
- **결론 서술의 한계 명시**: 컨테이너/VM 환경에서 p99 급증은 Redis 이벤트 루프 외에도 benchmark 클라이언트 자체, Docker Desktop VM, CPU 스케줄링의 영향일 수 있다. README의 결론은 "이 환경에서 관측된 지연 임계치"로 한정해 서술하고, "이벤트 루프 포화가 원인"이라고 단정하려면 `INFO commandstats`·서버 CPU 사용률 같은 보조 증거를 함께 제시한다(문서 신뢰성 규칙과 동일 맥락 — 데이터가 말해주는 것 이상을 주장하지 않는다).

이 파일럿의 진짜 목적은 "Redis 자체에 대한 결론"이 아니라 **3대 계약(실행 진입점 / `results.json` / `README.template.md`)과 Jekyll 발행 체인 전체가 실제로 끝까지 동작하는지 검증하는 것**이다. 여기서 스키마나 SKILL.md 절차에 문제가 발견되면, 다음 템플릿을 만들기 전에 `CONTRACT.md`를 먼저 고친다.

## 11. 구현 로드맵

각 Phase는 "이전 Phase가 실제로 동작함을 확인한 뒤에만" 다음으로 넘어간다 — 계약을 먼저 완벽하게 설계하고 나중에 채우는 방식이 아니라, 가장 얇은 경로(더미 데이터로 발행까지)를 먼저 끝까지 뚫은 뒤 실전 데이터로 채워나간다.

### Phase 0 — 발행 파이프라인 뼈대 검증 (실험 이전)
- [ ] 리포 루트 파일: `README.md`, `CONTRACT.md`, `CONTRIBUTING.md`(초안), `VALIDATION_CHECKLIST.md`(초안), `.gitignore`, `.gitattributes`
- [ ] `docker/runner/Dockerfile`, `requirements.txt`, `docker-compose.yml` 작성 후 `docker compose -f docker/runner/docker-compose.yml build` 성공 확인
- [ ] `schemas/results.schema.json`, `lib/validate_results.py`, `lib/to_csv.py`, `lib/chart.py`, `lib/style.mplstyle`, `lib/publish_post.py` 작성
- [ ] `templates/_skeleton/`에 더미 `experiment.sh`(실제 인프라 없이 하드코딩된 `results.json` 출력) + `docker-compose.yml` + `params.yml` + `README.template.md` + `TEMPLATE.md` 작성
- [ ] `docs/`에 `minima` 테마 + 더미 포스트 1개 작성
- [ ] GitHub Pages Settings를 `main`/`docs`로 설정하고 push → **실제 URL에서 더미 포스트가 뜨는지 확인**. 이 확인이 끝나기 전에는 Phase 1로 넘어가지 않는다(발행 경로부터 증명 — AGENDA.md 4번 요건 최우선 검증).

### Phase 1 — 3대 계약 동결
- [ ] `schemas/results.schema.json`을 `schema_version: "1.0"`으로 동결
- [ ] `CONTRACT.md`에 실행 진입점/`results.json`/`README.template.md` 토큰 표준을 확정 기술
- [ ] `.github/workflows/contract-check.yml`, `static-check.yml` 작성(Phase 3까지는 브랜치 보호 규칙으로 강제하지 않고 관찰만 — 템플릿이 하나도 없는 상태에서 CI를 강제하지 않는다)

### Phase 2 — 첫 실전 파일럿 (10장, 팀 확정 후)
- [ ] `templates/redis-blocking-threshold/` 실장(`docker-compose.yml`, `Dockerfile`, `experiment.sh`의 `redis-benchmark` 파싱 로직, `params.yml`)
- [ ] **사람이 Claude 없이** 전체 루프를 수동으로 1회 완주: 실행 → 검증 → 차트 → `README.template.md` 수동 작성 → 발행 → `git push` → 실 사이트 확인. 여기서 AGENDA.md 2번(하이브리드 실행 모델)의 "사람 단독 실행 가능" 축을 증명한다.
- [ ] 발견된 스키마/토큰/인터페이스 문제를 `CONTRACT.md`에 반영(실전 데이터 이전에 과설계하지 않는다는 원칙의 실행)

### Phase 3 — Claude Code 스킬화
- [ ] `.claude/skills/ds-lab-run-experiment/SKILL.md` 작성 — Phase 2에서 사람이 손으로 검증한 동일한 명령 순서를 그대로 자동화(검증되지 않은 절차를 먼저 자동화하지 않는다)
- [ ] 동일한 안건으로 스킬을 재실행해 사람이 만든 `results.json`/포스트와 동등한 결과가 나오는지 대조 검증

### Phase 4 — 크로스플랫폼 실제 검증
- [ ] 동일 파일럿을 Windows(Docker Desktop, WSL2 backend)와 Linux에서 각각 실행해 `docker compose run ...` 명령이 문자 그대로 동일하게 성공하는지, `results.json`이 동등한 headline 수치를 내는지 확인
- [ ] `VALIDATION_CHECKLIST.md`에 실제 검증 기록을 남기고, 이 단계에서 `.gitattributes`/경로 문제 등을 실제로 드러내고 수정
- [ ] `.github/workflows/*.yml`을 브랜치 보호 규칙에 연결(이때부터 CI가 실제 게이트로 작동)

### Phase 5 — 기여 인프라 완성 및 도그푸딩
- [ ] `CONTRIBUTING.md`, `VALIDATION_CHECKLIST.md` 상세화(Phase 2~4에서 겪은 실제 마찰점 반영)
- [ ] `lib/scaffold.py` 작성(크로스플랫폼 템플릿 스캐폴딩 — 6.2절)
- [ ] `.claude/skills/ds-lab-new-template/SKILL.md` 작성
- [ ] 두 번째 템플릿 추가(예: `TOPICS.md` OLAP 카테고리의 ClickHouse 단일 컨테이너 적재 실험, 또는 오케스트레이션 카테고리의 `kind` 기반 실험) — "CONTRIBUTING.md만 보고 새 스택을 추가할 수 있는가"를 실제 사례로 검증하고, 계약이 Redis 케이스에 과적합되지 않았는지 확인. 이 작업을 `docker/runner`, `lib/`, `schemas/` 수정 없이 `templates/` 아래 추가만으로 완료할 수 있어야 한다 — 못 하면 계약 설계에 결함이 있다는 신호다.

### Phase 6 — 성숙기 (필요해질 때만 도입, YAGNI)
- [ ] 템플릿이 4개 이상으로 늘어나 수동 크로스-OS 검증 비용이 커지면, 자체 호스팅 러너(Windows 네이티브 Docker) 도입으로 `static-check.yml`을 실제 스모크런으로 승격하는 것을 검토
- [ ] 재현성 강화가 필요해지면 베이스 이미지(`python:3.12-slim`, `redis:7-alpine` 등)를 digest(`@sha256:...`)로 고정하는 것을 검토 — 태그는 가리키는 대상이 바뀔 수 있어 "과거 실험의 환경 동결"까지 보장하려면 digest가 필요하다. 그 전까지는 마이너 버전 태그 고정(`redis:7.4-alpine` 수준)으로 운영한다
- [ ] README/발행 포스트의 인용 수치를 `results.json`과 자동 대조하는 `lib/check_readme_numbers.py` 도입 검토(정규식으로 수치를 추출해 `summary`/`data[]` 값과 비교) — 자동화 신뢰성을 한 단계 더 끌어올리는 선택적 강화
- [ ] 콘텐츠 볼륨이 늘어나면 Jekyll 테마를 태그/검색이 있는 것으로 교체 검토
- [ ] `lib/chart.py`에 `line_chart` 외 차트 타입(heatmap 등) 필요 시 추가
