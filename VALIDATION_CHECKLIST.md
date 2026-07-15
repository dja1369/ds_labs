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

## 템플릿별 검증 기록

새 템플릿을 추가하거나 기존 템플릿을 변경할 때마다 아래 형식으로 섹션을 추가하세요.
(주 개발 환경이 macOS라면 macOS 항목은 CONTRIBUTING.md 3절의 로컬 자기검증 기록으로
갈음할 수 있습니다 — 별도 실행을 중복 요구하지 않습니다.)

```markdown
## <slug> 템플릿 검증
- [ ] Linux: `--smoke` 통과 (CI 자동, 실행: contract-check #___)
- [ ] macOS: `--smoke` 통과 (수동, 실행자: ___, 날짜: ___, Docker Desktop 버전: ___, arch: arm64/amd64)
- [ ] Windows: `--smoke` 통과 (수동, 실행자: ___, 날짜: ___, Docker Desktop 버전: ___)
- [ ] 3개 OS의 results.json이 동일한 headline 수치(±허용오차)를 냈는가
```

<!-- 아래에 템플릿별 검증 기록을 추가하세요. -->
