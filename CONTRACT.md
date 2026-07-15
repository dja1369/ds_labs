# CONTRACT.md — 3대 공통 계약

이 문서는 모든 `templates/<slug>/`가 반드시 지켜야 하는 3가지 계약의 **단일 정본**이다.
계약을 변경하는 PR은 기존 템플릿 전부에 대한 하위 호환 영향을 PR 설명에 명시해야 한다.

## 1. 실행 진입점 인터페이스

호스트에서 사람과 Claude Code가 동일하게 입력하는 유일한 명령(한 줄):

```
docker compose -f templates/<slug>/docker-compose.yml run --rm runner ./experiment.sh --params params.yml --out results [--smoke]
```

| 요소 | 역할 |
|---|---|
| `templates/<slug>/docker-compose.yml` | `runner` 서비스(공용 이미지 확장) + 실험 대상 인프라 서비스(자유 구성) |
| `templates/<slug>/experiment.sh` | 컨테이너 **내부**에서만 실행되는 실제 측정 로직. `#!/usr/bin/env bash` + `set -euo pipefail` 헤더 필수 |
| `--params <path>` | 실험 파라미터 YAML (기본 `params.yml`) |
| `--out <dir>` | 산출물 디렉토리 (기본 `results`). `results.json`/`results.csv`/`charts/`가 이 아래 생성됨 |
| `--smoke` | 축소 실행 모드. `params.yml`의 `smoke:` 블록으로 스윕 범위를 오버라이드해 1분 내외로 종료 |
| exit code | 0이 아니면 파이프라인은 그 지점에서 즉시 중단하고 stderr 전체를 보고한다(무음 실패 금지) |

검증/CSV 변환/차트 생성도 항상 `docker compose -f docker/runner/docker-compose.yml run --rm runner <command>` 형태로만 호출한다(호스트에 Python을 설치하지 않는다). 자세한 크로스플랫폼 원칙은 리포 루트 `README.md`의 "왜 이 명령이 3개 OS에서 동일하게 동작하는가" 절을 참고.

**표기 규약**: 문서에서 `\` 줄연장은 지면 가독성을 위한 것일 뿐이다. 사용자에게 노출되는 모든 명령(README/CONTRIBUTING)은 반드시 한 줄로 표기한다 — `\`는 POSIX 쉘 전용 문법이라 Windows에서 그대로 복사하면 깨진다.

## 2. `results.json` / `results.csv` 스키마

`results.json`이 유일한 진실 원천(source of truth)이고, `results.csv`는 `lib/to_csv.py`가 자동 파생시키는 산출물이다. 정본 스키마는 [`schemas/results.schema.json`](schemas/results.schema.json)(JSON Schema draft 2020-12, `schema_version: "1.0"`으로 동결)이다.

두 필드는 표현력을 위한 최소 확장이다:
- **`series`**: 같은 `metric` 안의 하위 계열 구분(예: SET/GET). 없으면 `null`.
- **`x`의 `number | string` 유니온**: 수치 스윕(동시성 등)은 숫자, 범주형 비교(GC 종류, 파일시스템 등)는 문자열. 같은 metric 안에서 숫자/문자열을 혼용하면 `lib/validate_results.py`가 거부한다.

`results.csv`의 컬럼은 `data[]` 필드와 1:1 고정이다(`metric,series,x_label,x,y,unit,note`) — 템플릿별 자유 컬럼은 허용하지 않는다.

검증: `python -m lib.validate_results <path>` (컨테이너 내부). 실패 시 exit 1 + 어떤 필드가 왜 틀렸는지 stderr에 출력한다. 검증을 통과해야만 다음 단계(차트 생성)로 진행한다.

`run.environment`는 컨테이너 안에서 관측 가능한 값만 담는다(`arch`/`cpu_cores`/`memory_gb`) — 물리 호스트의 OS나 Docker Desktop 버전은 담지 않는다(그 정보는 `VALIDATION_CHECKLIST.md`가 담당).

## 3. `README.template.md` 구조

`templates/<slug>/README.template.md`는 `${TOKEN}` 치환식이며 다음 순서를 고정한다:

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

표준 토큰 집합: `TITLE DATE TEMPLATE_NAME TAGS QUESTION HYPOTHESIS SETUP METHOD RESULTS CONCLUSION NEXT_QUESTIONS`. 임의로 새 토큰을 추가하지 않는다 — 확장이 필요하면 이 문서를 먼저 개정한다(스킬이 파싱 가능해야 한다).

`RESULTS`/`CONCLUSION` 섹션에 등장하는 모든 수치는 반드시 `results.json`의 `data[]` 또는 `summary`에서 인용해야 한다. 문서에 없는 수치를 추측·생성하지 않는다.

## 이미지 정본 산출물

`lib/chart.py`가 생성하는 차트는 항상 정적 PNG이며, 파일명 규칙은 `charts/<metric 슬러그>.png`다(metric 필드명 그대로 소문자·공백을 언더스코어로 치환). 색상/DPI/폰트 등 스타일은 `lib/style.mplstyle` 하나로 고정한다(개별 커스터마이징 금지).
