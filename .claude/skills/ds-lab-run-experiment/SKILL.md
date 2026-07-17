---
name: ds-lab-run-experiment
description: >
  안건(연구 질문)을 받아 templates/ 아래 기존/신규 템플릿으로 실험을 실행하고,
  results.json/csv를 검증하고, 차트를 만들고, README를 채워 Jekyll에 발행한다.
  트리거: "실험 시작", "안건 실행해줘", "~는 얼마부터 ~할까?" 같은 연구 질문 형태의
  요청, 기존 experiments/<slug>/ 재실행 요청.
---

# ds-lab-run-experiment

안건 → 템플릿 선택/생성 → 실행 → 검증 → 차트 → README → 발행까지 이어지는
ds_labs의 메인 실험 루프를 수행한다. 모든 기계적 단계는 사람도 Claude 없이
동일한 명령을 그대로 타이핑해 재현할 수 있어야 한다 — 스킬 안에만 존재하는
숨은 로직을 두지 않는다.

## 여러 실험을 동시에 굴릴 때

`TOPICS.md` 백로그에서 후보 실험이 여러 개 뽑혔다면, 1단계(안건 명확화)·2단계
(템플릿 선정)·8단계(README 작성) 같은 judgment/글쓰기 단계는 실험마다 상태를
공유하지 않는다 — 서로 다른 후보 실험 두세 개를 별도 서브에이전트로 동시에
디스패치해 병렬로 진행해도 안전하다. 반면 4단계(`experiment.sh` 실행, 부하
테스트)는 호스트당 반드시 직렬로 돌려야 한다 — 같은 머신에서 서비스 두 개에
동시에 부하를 걸면 CPU/메모리/네트워크 자원 경쟁이 두 실험의 레이턴시·처리량
수치를 동시에 오염시킨다. 즉 "글쓰기는 병렬, 측정은 직렬"이 원칙이다. 이건
코드로 강제하는 게 아니라 여러 실험을 배치로 굴릴 때 사람/오케스트레이터가
지켜야 할 프로세스 규칙이다.

## 절차

1. **안건 명확화 (judgment)** — 사용자의 연구 질문을 성공 기준이 있는 형태로
   재진술한다. 모호하면 코드를 건드리기 전에 반드시 되묻는다: 어떤 기술 스택인가?
   기존 `templates/*/TEMPLATE.md` 중 재사용 가능한 것이 있는가? 안건을 kebab-case
   `experiment_id`로 확정한다(이후 Jekyll 슬러그와 1:1 대응하므로 이 시점에 고정).

2. **템플릿 선정 또는 위임** — `templates/` 하위 `TEMPLATE.md`(`_skeleton` 제외)를
   훑어 일치하는 템플릿이 있는지 판단한다. 없으면 사용자에게 확인 후
   `ds-lab-new-template` 스킬로 위임한다.

3. **파라미터 설정 (judgment)** — `templates/<slug>/params.yml`을 안건에 맞게
   조정한다. 이 단계만 모델 판단이 필요하다 — 결정적 변환이 아닌 곳에만 모델을
   쓴다.

4. **실행 (결정적, 모델이 값을 임의로 바꾸지 않음)**
   ```
   docker compose -f templates/<slug>/docker-compose.yml run --rm runner ./experiment.sh --params params.yml --out results --smoke
   ```
   먼저 `--smoke`로 파이프라인이 살아있는지 확인한 뒤, `--smoke` 없이 본 실행.
   exit code가 0이 아니면 즉시 중단하고 stderr 전체를 그대로 보고한다 — 실패를
   숨기지 않는다. "완료"라고 보고하기 전에 반드시 `results/results.json` 존재
   여부를 확인한다.

5. **검증**
   ```
   docker compose -f docker/runner/docker-compose.yml run --rm runner python -m lib.validate_results templates/<slug>/results/results.json
   ```
   실패 시 결과를 폐기하고 원인(스키마 위반 필드)을 사용자에게 보고한다. 검증을
   건너뛰고 다음 단계로 넘어가지 않는다.

6. **실험 디렉토리 확정** — `experiments/<YYYY-MM-DD>-<experiment_id>/`를 만들고
   `results/`, `params.yml`, `agenda.md`(안건+가설 원문)를 옮긴다. **이 디렉토리가
   이미 존재하면 조용히 덮어쓰지 않고 즉시 중단해 사용자에게 알린다**(append-only
   원칙, fail loud). 같은 날 의도적 재실행이면 사용자 확인 후 `-run2`, `-run3` 서수
   접미사를 붙인 새 디렉토리를 만든다 — 접미사가 붙으면 Jekyll 포스트 슬러그와
   이미지 경로에도 동일하게 반영되어 기존 발행물을 덮어쓰지 않는다.

7. **CSV 파생 + 차트 생성** — `results.csv`는 3대 계약의 일부이므로 이 단계에서
   반드시 함께 생성한다(누락은 계약 위반).
   ```
   docker compose -f docker/runner/docker-compose.yml run --rm runner python -m lib.to_csv experiments/<slug>/results/results.json experiments/<slug>/results/results.csv
   docker compose -f docker/runner/docker-compose.yml run --rm runner python -m lib.chart --results experiments/<slug>/results/results.json --out experiments/<slug>/results/charts/
   ```

8. **README 작성 (judgment, 유일한 프로즈 작성 단계)** — 먼저 기계적으로 채울 수
   있는 부분을 스크립트로 미리 채운다.
   ```
   docker compose -f docker/runner/docker-compose.yml run --rm runner python -m lib.scaffold_report experiments/<slug>/
   ```
   `lib/scaffold_report.py`는 `results.json`/`params.yml`에서 100% 기계적으로
   도출되는 부분(`RESULTS` 표 전체, `SETUP`의 `params.yml` 최상위 값과
   `run.environment`)만 채우고, 판단이 필요한 나머지(`QUESTION` `HYPOTHESIS`
   `SUMMARY` `METHOD` `FINDINGS` `CONCLUSION` `NEXT_QUESTIONS`, `SETUP`의
   인프라 설명 불릿)는 `TODO(scaffold_report)` 표시가 붙은 자리표시자로 남긴다.
   이 judgment pass에서 그 자리표시자들을 실제 프로즈로 채운다 — 스크립트를
   먼저 돌려두면 표 조립처럼 손이 많이 가는 부분을 사람이 다시 타이핑할 필요가
   없다. `CONTRACT.md` 3절의 토큰(`TITLE DATE TEMPLATE_NAME TAGS QUESTION HYPOTHESIS
   SUMMARY SETUP METHOD RESULTS FINDINGS CONCLUSION NEXT_QUESTIONS`)을 채운다.
   **`RESULTS`/`FINDINGS`/`CONCLUSION` 섹션의 모든 수치는 반드시 `results.json`의
   `data[]` 또는 `summary`에서 직접 인용한다 — 추측 금지, 데이터 기반 서술 강제.**
   `QUESTION`은 담백한 한 문장으로, `HYPOTHESIS`는 `SUMMARY`보다 먼저 온다(예상 →
   실제 순서). `SUMMARY`는 산문이 아니라 3~5줄 불릿으로 훑어보고 핵심(현상 → 반전
   → 진짜 원인 방향)이 잡히게 쓴다. `RESULTS`는 핵심 수치 표만 담고 해석은 넣지
   않는다 — 해석·차트는 전부 `FINDINGS`로 보낸다. `METHOD`는 시나리오를 번호 매겨
   순서대로 서술하고 각 단계의 실행 커맨드를 코드 블록으로 보여준다. `FINDINGS`는
   `### 성능 및 일반적인 사례`·`### 추가로 알면 좋을 사항` 두 소제목을 고정하고,
   옆에서 코드 리뷰해주는 5년차 개발자 톤(교과서적 설명 없이, 왜 흥미로운지까지
   짚는)으로 쓴다 — 문장은 마침표로 끝나면 줄을 바꿔 빽빽한 문단을 만들지 않는다.
   `CONCLUSION`은 긴 문단보다 불릿/번호로 한눈에 훑히게 쓴다. 기술 용어는 문서
   전체에서 처음 등장하는 자리에 짧은 괄호 설명을 붙인다(예: `P99(요청 99%가
   처리되는 시간)`) — 이후 재등장 시엔 반복하지 않는다.
   `NEXT_QUESTIONS`는 형식적 리서치 제안이 아니라 "이거 왜 이런거지?" 톤으로, 이번
   결과에서 자연스럽게 파생되는 후속 질문 1~3개를 항목당 1~2문장으로 구체적으로
   제안한다(`TOPICS.md`에 관련 항목이 있으면 참조) — 우선순위 라벨이나 각주식
   근거 나열은 붙이지 않는다.

9. **발행**
   ```
   docker compose -f docker/runner/docker-compose.yml run --rm runner python -m lib.publish_post experiments/<slug>/
   ```
   → `docs/_posts/<date>-<slug>.md` + `docs/assets/images/<date>-<slug>/*.png` 생성.

10. **사람 확인 요청** — `git add`/`commit`/`push`는 스킬이 자동 실행하지 않는다.
    `git diff --stat`을 보여주고 사람이 직접 커밋/푸시하도록 안내한다(오배포 사고
    방지). 스킵된 단계가 있으면(예: 검증 실패 후 강행) 반드시 명시한다 —
    "완료" 남용 금지.

## 금지 사항

- `results.json`을 스키마에 맞추기 위해 손으로 값을 지어내지 않는다.
- 검증 실패를 무시하고 발행 단계로 넘어가지 않는다.
- `templates/_skeleton/`은 실제 실험 템플릿 선택 대상이 아니다(더미 템플릿).
