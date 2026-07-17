---
layout: home
title: ds_labs
---

**ds_labs**는 컴퓨터/인프라 궁금한 거 직접 찔러보고 기록하는 실험실.

"Redis에 요청을 얼마나 넣으면 터질까?" 같은 질문이 떠오르면 Docker로 환경
띄우고, 부하 걸고, 결과 그래프로 남긴다. Redis, Kubernetes, ClickHouse,
Spring Boot 등 스택은 계속 늘어남.

## 실험 루프

```
안건(연구 질문) → 템플릿 기반 환경 구성 → 테스트 진행 → 문서화(이미지 포함) → 결론 정리 → 다음 연구 과제 제안
```

모든 실험은 `docker compose` 명령 한 줄로 그대로 재현 가능. Claude Code가
돌려도, 사람이 직접 같은 명령을 타이핑해도 결과는 똑같음 — 둘이 결국 같은
명령을 친다. 재현 코드는 각 글 하단 GitHub 링크에.

## 지금 상태

실행/검증/발행 파이프라인(3대 계약: 실행 진입점 · `results.json` · 문서 템플릿)
다 돌아감. 발행된 실험은 새 글이 올라올 때마다 아래 표에 자동으로 쌓임.

| 제목 | 날짜 | 태그 |
|---|---|---|
{% for post in site.posts %}{% unless post.categories contains "meta" %}| [{{ post.title }}]({{ post.url | relative_url }}) | {{ post.date | date: "%Y-%m-%d" }} | {{ post.tags | join: ", " }} |
{% endunless %}{% endfor %}

## 더 보기

- [GitHub 저장소](https://github.com/dja1369/ds_labs) — 재현 코드 전체
- [기여 가이드](https://github.com/dja1369/ds_labs/blob/main/CONTRIBUTING.md) — 새 실험 템플릿 추가 방법
- [연구 안건 목록](https://github.com/dja1369/ds_labs/blob/main/TOPICS.md) — 다음 실험 후보
- [태그별로 보기]({{ '/tags/' | relative_url }}) — 실험을 태그로 훑어보기
