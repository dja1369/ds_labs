---
layout: home
title: ds_labs
---

**ds_labs**는 컴퓨터/인프라 실험(Redis, Kubernetes, ClickHouse, Spring Boot 등)을
재현 가능한 형태로 수행하고 기록하는 실험 랩입니다.

## 실험 루프

```
안건(연구 질문) → 템플릿 기반 환경 구성 → 테스트 진행 → 문서화(이미지 포함) → 결론 정리 → 다음 연구 과제 제안
```

모든 실험은 `docker compose` 명령 한 줄로 재현 가능합니다. Claude Code가 이 루프를
보조 실행할 수도, 사람이 직접 같은 명령을 타이핑해 재현할 수도 있습니다 — 두 경로는
완전히 동일한 명령으로 수렴합니다. 재현 코드는 각 글 하단의 GitHub 링크에서 확인할
수 있습니다.

## 지금 상태

실행/검증/발행 파이프라인(3대 계약: 실행 진입점 · `results.json` · 문서 템플릿)이
동작을 마쳤고, 첫 실전 실험을 준비 중입니다. 아래는 그동안의 기록입니다.

## 더 보기

- [GitHub 저장소](https://github.com/dja1369/ds_labs) — 재현 코드 전체
- [기여 가이드](https://github.com/dja1369/ds_labs/blob/main/CONTRIBUTING.md) — 새 실험 템플릿 추가 방법
- [연구 안건 목록](https://github.com/dja1369/ds_labs/blob/main/TOPICS.md) — 다음 실험 후보
