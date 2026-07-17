# VALIDATION_CHECKLIST.md

신규/변경된 템플릿을 머지하기 전 사람이 수행한 크로스-OS 수동 검증 기록입니다.
CI(`contract-check.yml`)는 Linux(ubuntu-latest)에서만 실제 컨테이너 스모크런을
자동 수행할 수 있습니다 — GitHub 호스팅 macOS 러너는 Docker가 없고 Apple Silicon
러너는 중첩 가상화를 지원하지 않으며, Windows 러너는 Linux 컨테이너를 실행할 수
없습니다. 따라서 macOS와 Windows 검증은 사람이 실제 Docker Desktop으로 수행하고
여기에 기록해야 머지할 수 있습니다.

## 머지 기준

- [ ] `contract-check`(ubuntu, 실제 스모크런) 통과
- [ ] `static-check`(windows, 정적 검증) 통과
- [ ] 아래 템플릿별 섹션의 macOS·Windows 수동 검증 체크 완료
- [ ] `TEMPLATE.md` 문서 완결성 확인(기술/전제조건/사용 예시 존재, `README.template.md`의
      `${TOKEN}`이 `CONTRACT.md`의 표준 토큰 집합과 일치)

넷 다 충족해야 머지합니다.

## 이미지 아키텍처 확인

```
docker manifest inspect <base-image>
```
`linux/amd64`·`linux/arm64` 둘 다 없으면 템플릿 `TEMPLATE.md`에 "Apple Silicon에서
QEMU 에뮬레이션으로 느릴 수 있음"을 명시하거나 대체 이미지를 찾습니다.

## `FINDINGS` 문체 확인 (CONTRACT.md §3)

리뷰 시 `README.template.md`의 `발견 사항 및 분석`이 "5년차 개발자 리뷰" 톤인지
한 줄이라도 대조해봅니다 — 현상 재설명이 아니라 왜 흥미로운지가 남아야 합니다.

- 좋은 예(`redis-blocking-threshold`): "여기서부터가 진짜다 — redis-server 자체는
  이 구간 내내 안 바빴다."
- 나쁜 예: "CPU 사용률이란 서버가 요청을 처리하는 동안 프로세서를 사용한 비율을
  뜻하며, 이 값이 낮다는 것은 시스템 자원에 여유가 있음을 의미한다."

## 템플릿별 검증 기록

새 템플릿을 추가하거나 기존 템플릿을 변경할 때마다 아래 형식으로 섹션을 추가하세요.
(주 개발 환경이 macOS라면 macOS 항목은 CONTRIBUTING.md 5절의 로컬 자기검증 기록으로
갈음할 수 있습니다 — 별도 실행을 중복 요구하지 않습니다.)

```markdown
## <slug> 템플릿 검증
- [ ] Linux: `--smoke` 통과 (CI 자동, 실행: contract-check #___)
- [ ] macOS: `--smoke` 통과 (수동, 실행자: ___, 날짜: ___, Docker Desktop 버전: ___, arch: arm64/amd64)
- [ ] Windows: `--smoke` 통과 (수동, 실행자: ___, 날짜: ___, Docker Desktop 버전: ___)
- [ ] 3개 OS의 results.json이 동일한 headline 수치(±허용오차)를 냈는가
```

<!-- 아래에 템플릿별 검증 기록을 추가하세요. -->

## redis-blocking-threshold 템플릿 검증
(PR #3 머지 당시 이 섹션이 누락되어 있었음을 뒤늦게 발견해 기존 기록을 근거로 backfill함.)
- [x] Linux: `--smoke`/실전 통과 (CI 자동, contract-check 성공, PR #3 · 커밋 c4c67ac · 2026-07-15)
- [x] macOS: 통과 (CONTRIBUTING.md 5절 갈음 — PR #3 본문에 기록된 로컬 자기검증 로그: `--smoke`(2 스텝)·실전(9 스텝, 37초) 양쪽 모두 실행→검증→CSV 파생→차트 생성→teardown까지 통과)
- [ ] Windows: `--smoke` 통과 (수동, 실행자: ___, 날짜: ___, Docker Desktop 버전: ___) — **미기록, 확인 필요**
- [ ] 3개 OS의 results.json이 동일한 headline 수치(±허용오차)를 냈는가 — Windows 미검증으로 확인 불가
