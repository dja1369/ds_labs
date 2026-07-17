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

## 요약
${SUMMARY}

## 구성
${SETUP}

## 방법
${METHOD}

## 결과
${RESULTS}

## 발견 사항 및 분석
${FINDINGS}

## 결론
${CONCLUSION}

## 연관 연구 주제 제안
${NEXT_QUESTIONS}
```

표준 토큰 집합: `TITLE DATE TEMPLATE_NAME TAGS QUESTION HYPOTHESIS SUMMARY SETUP METHOD RESULTS FINDINGS CONCLUSION NEXT_QUESTIONS`. 임의로 새 토큰을 추가하지 않는다 — 확장이 필요하면 이 문서를 먼저 개정한다(스킬이 파싱 가능해야 한다).

`QUESTION`은 담백하게 한 문장으로 쓴다 — 조건절을 주렁주렁 붙인 격식체 연구 질문("~는 ~부터 ~가 급격히 튀며 ~에 진입하는가?")이 아니라, 실제로 궁금해서 물어보는 말투로 쓴다(예: "Redis에 요청을 얼마나 넣으면 죽을까?"). 격식·수식은 `HYPOTHESIS`/`RESULTS`에서 붙인다.

`HYPOTHESIS`가 `SUMMARY`보다 먼저 오는 이유는 독자가 "뭘 예상하고 시작했는지"를 먼저 알아야 `SUMMARY`의 반전("근데 틀렸다")이 반전으로 읽히기 때문이다 — 결론을 먼저 까고 시작하는 게 아니라, 예상 → 실제 순서로 읽게 한다.

`SUMMARY`는 산문이 아니라 불릿 리스트로 쓴다 — 훑어보고 바로 핵심(현상 → 반전 → 진짜 원인 방향)이 잡혀야 한다. 3~5줄, 각 줄은 한 문장 이하로 짧게 끊는다. 핵심 수치(임계값 등)를 포함하되, 근거는 `RESULTS`/`FINDINGS`에서 상세히 다룬다.

`SETUP`은 환경/인프라/부하 조건(예: CPU·메모리 제한, concurrency, rps)을 불릿으로 짧게 나열한다 — 산문으로 풀어쓰지 않는다.

`METHOD`는 실제로 수행한 시나리오를 번호를 매겨 순서대로 서술한다(1. ~, 2. ~ ...). 각 단계에 해당 실행 커맨드를 코드 블록으로 함께 보여준다. 캡처 이미지가 있으면 해당 단계 바로 아래에 삽입한다 — 이 프로젝트는 단계별 캡처를 자동 생성하지 않으므로 있으면 넣고 없으면 생략한다(이미지가 없다고 단계 서술 자체를 생략하지 않는다).

`RESULTS`는 핵심 수치 표(markdown table)만 담는다 — 해석·서술은 여기 두지 않고 전부 `FINDINGS`로 보낸다. 표가 여러 개면 순서대로 나열하되, 표 사이/뒤에 설명 문단을 붙이지 않는다.

`FINDINGS`는 두 하위 소제목을 고정하고, `RESULTS`의 수치를 해석하는 산문·차트가 전부 여기 들어온다:
- `### 성능 및 일반적인 사례` — 관측된 현상을 일반적인 패턴으로 서술한다(예: 특정 concurrency·CPU·메모리 조건을 넘으면 성능이 무너지는 지점).
- `### 추가로 알면 좋을 사항` — 표면적 현상과 실제 원인이 다를 때의 정정·단서를 남긴다(예: "서비스가 멈춘 것처럼 보이지만 실제 원인은 CPU가 아니라 다른 병목이었다").

`FINDINGS`의 문체는 옆에서 코드 리뷰해주는 5년차 개발자 톤이다 — 현상을 설명하고 끝내지 않고, 왜 흥미로운지·다음에 뭘 의심하게 되는지까지 짧게 짚는다. 교과서적 설명(기초 개념 재설명)은 하지 않는다 — 이미 아는 사람에게 말하듯 쓴다. 다만 문장은 마침표(.)로 끝나면 줄을 바꾼다 — 한 문단에 여러 문장을 욱여넣지 않는다(문장마다 줄바꿈해야 빽빽한 문단 없이 한눈에 훑힌다).

`CONCLUSION`은 한눈에 훑어지는 게 최우선이다 — 줄바꿈이 애매한 긴 문단으로 늘어놓지 않는다. 결론이 여러 갈래(예: 가설 중 맞은 부분/틀린 부분/남은 의문)로 나뉘면 불릿이나 번호로 쪼갠다. 문단으로 쓸 땐 한 문단에 하나의 주장만 담는다.

기술 용어는 문서 전체를 통틀어 처음 등장하는 자리에서 짧은 괄호 설명을 붙인다(예: `P99(요청 99%가 처리되는 시간 — 사실상 최악에 가까운 케이스)`) — 배경지식 없는 독자도 따라올 수 있어야 한다. 같은 용어를 이후에 또 쓸 땐 반복 설명하지 않는다.

`NEXT_QUESTIONS`는 형식적인 리서치 제안문이 아니라 "이거 왜 이런거지?" 하고 스스로에게 묻는 톤으로, 항목당 1~2문장으로 짧게 쓴다. 우선순위 라벨이나 각주식 근거 나열을 붙이지 않는다 — 궁금증과 그걸 좁히는 첫 번째 추론만 남긴다.

`RESULTS`/`FINDINGS`/`CONCLUSION` 섹션에 등장하는 모든 수치는 반드시 `results.json`의 `data[]` 또는 `summary`에서 인용해야 한다. 문서에 없는 수치를 추측·생성하지 않는다.

## 이미지 정본 산출물

`lib/chart.py`가 생성하는 차트는 항상 정적 PNG이며, 파일명 규칙은 `charts/<metric 슬러그>.png`다(metric 필드명 그대로 소문자·공백을 언더스코어로 치환). 색상/DPI/폰트 등 스타일은 `lib/style.mplstyle` 하나로 고정한다(개별 커스터마이징 금지).
