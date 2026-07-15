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

8. **README 작성 (judgment, 유일한 프로즈 작성 단계)** —
   `templates/<slug>/README.template.md`를 복사해 `experiments/<slug>/README.md`로
   만들고 `CONTRACT.md` 3절의 토큰(`TITLE DATE TEMPLATE_NAME TAGS QUESTION SUMMARY
   HYPOTHESIS SETUP METHOD RESULTS CONCLUSION NEXT_QUESTIONS`)을 채운다.
   **`RESULTS`/`CONCLUSION` 섹션의 모든 수치는 반드시 `results.json`의 `data[]`
   또는 `summary`에서 직접 인용한다 — 추측 금지, 데이터 기반 서술 강제.**
   `SUMMARY`는 본문을 읽지 않아도 결론이 파악되도록 2~4문장으로 압축한다.
   `NEXT_QUESTIONS`는 이번 결과에서 자연스럽게 파생되는 후속 질문 1~3개를
   구체적으로 제안한다(`TOPICS.md`에 관련 항목이 있으면 참조).

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
