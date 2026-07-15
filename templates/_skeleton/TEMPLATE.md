# _skeleton

새 실험 템플릿을 만들 때 시작점으로 쓰는 뼈대다. 실제 기술 스택을 다루지 않으며
`experiment.sh`는 하드코딩된 더미 `results.json`만 출력한다 — 3대 계약(실행
진입점 / `results.json`·`.csv` / `README.template.md`)이 실제로 끝까지
동작하는지 증명하는 walking skeleton 용도다.

`ds-lab-run-experiment` 스킬은 이 파일을 실제 실험 템플릿 선택에 쓰지 않는다
(안건에 대응하는 실제 기술 스택이 없으므로 매칭 대상에서 제외한다).

## 새 템플릿을 만들려면

`.claude/skills/ds-lab-new-template` 스킬을 쓰거나 직접:
```
docker compose -f docker/runner/docker-compose.yml run --rm runner python -m lib.scaffold <new-slug>
```
를 실행해 이 디렉토리를 `templates/<new-slug>/`로 복사한 뒤, `docker-compose.yml`에
대상 인프라 서비스를 추가하고 `experiment.sh`의 TODO를 실제 측정 로직으로 채운다.

## 전제조건
없음 (더미 템플릿).
