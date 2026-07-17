"""python -m lib.check_report --structure <README.template.md 또는 README.md>
python -m lib.check_report --content <README.md> --results <results.json> [--agenda <agenda.md>]

리포트 계약(CONTRACT.md §3) 준수 여부를 검사하는 두 모드.

MODE A(--structure): README.template.md 또는 채워진 README.md가 CONTRACT.md §3이
고정한 '## ' 헤더 9개를 정확한 순서로 갖는지 검사한다. 템플릿 스켈레톤에도, 채워진
실험 README에도 그대로 쓸 수 있다.

MODE B(--content): 채워진 실험 README에 대해서만 의미 있는 두 가지 검사를 한다.
  (b1) 수치 출처 검증 — '## 결과'/'## 발견 사항 및 분석'/'## 결론' 섹션이 전부
       존재하고(하나라도 없으면 실패), 그 안의 모든 숫자가 results.json에서
       추적 가능한지 확인한다. 리터럴 값이거나, 같은 metric·series 안(또는
       summary와의 조합)에서 나오는 두 값의 단순 파생값(배수/차이/퍼센트
       증감)이면 통과. 완벽한 조작 탐지 장치는 아니다 — known 값이 많아지면
       우연히 근접하는 파생값이 나올 수 있어(_derived_pairs/_ratio_candidates
       주석 참고), "이 숫자가 results.json 어딘가와 산술적으로 맞아떨어진다"는
       느슨한 신뢰 신호로만 쓰고 최종 판단은 CONTRACT.md 문서 신뢰성 규칙에
       따른 사람 리뷰에 둔다. 실패 시 exit 1.
  (b2) 안건 문체 점검(경고 전용) — --agenda가 주어지면 README '## 안건'을
       agenda.md의 안건과 비교해 거의 동일하거나 격식체 연구 질문 패턴이면 경고만
       출력한다(exit 0 유지, b1이 실패한 경우는 예외).
"""
import argparse
import difflib
import itertools
import json
import re
import sys
from pathlib import Path

# CONTRACT.md §3 고정 헤더 순서 — 계약이 개정되면 이 리스트도 함께 갱신해야 한다.
EXPECTED_HEADERS = [
    "안건",
    "가설",
    "요약",
    "구성",
    "방법",
    "결과",
    "발견 사항 및 분석",
    "결론",
    "연관 연구 주제 제안",
]

# b1이 수치 출처를 검사하는 대상 섹션 (CONTRACT.md §3: "RESULTS/FINDINGS/CONCLUSION
# 섹션에 등장하는 모든 수치는 반드시 results.json에서 인용해야 한다").
CONTENT_SECTIONS = ["결과", "발견 사항 및 분석", "결론"]

# 숫자 토큰 추출: 앞이 글자/숫자/마침표가 아닌 위치에서 시작하는 정수·소수·천단위
# 콤마 숫자만 잡는다. 뒤쪽은 경계를 두지 않는다 — "22.5배"/"10.9%"처럼 한글
# 조사·기호가 숫자 바로 뒤에 붙는 표기를 그대로 지원하기 위함. 반대로 "P99"처럼
# 글자 바로 뒤에 붙은 숫자는(둘 다 단어 문자라 경계가 없어) 애초에 매치 시작점이
# 되지 않는다.
NUMBER_RE = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?")

# 리터럴/파생값 매칭 상대 오차 허용치. 정상적인 인용 오차(콤마 표기 반올림 등)는
# 1e-5 수준이라 넉넉하고, x=100 대 오기값 99.9(0.1% 오차) 같은 우연한 근접값은
# 걸러낼 만큼 타이트하다.
REL_TOL = 5e-4

QUESTION_HEADER = "안건"
STACKED_CLAUSE_MARKERS = [",", "~하며", "~부터", "튀며", "진입하는가"]
SIMILARITY_THRESHOLD = 0.85
QUESTION_EXAMPLE = "Redis에 요청을 얼마나 넣으면 죽을까?"


_HEADING_RE = re.compile(r"^(#{1,6})[ \t]*(.+?)[ \t]*$")


def extract_section(text: str, name: str) -> str | None:
    """`# name` ~ `###### name` 헤더 바로 다음 줄부터, 같거나 더 얕은 레벨의 다음
    헤더 직전까지(더 깊은 레벨 — 예: '### 성능 및 일반적인 사례' 같은 하위
    소제목 — 은 건너뛰고 포함)를 돌려준다. 없으면 None.

    단일 정규식으로 "다음 헤더 직전까지"를 표현하면 '## 발견 사항 및 분석'처럼
    본문이 '### ' 하위 소제목으로 시작하는 섹션에서 그 하위 소제목 자체를
    섹션의 끝으로 오인해 본문 대부분(수치 포함)을 놓친다 — 그래서 줄 단위로
    헤더 레벨을 비교한다."""
    lines = text.split("\n")
    start_idx = None
    target_level = None
    for i, line in enumerate(lines):
        m = _HEADING_RE.match(line)
        if m and m.group(2) == name:
            start_idx = i
            target_level = len(m.group(1))
            break
    if start_idx is None:
        return None

    end_idx = len(lines)
    for j in range(start_idx + 1, len(lines)):
        m = _HEADING_RE.match(lines[j])
        if m and len(m.group(1)) <= target_level:
            end_idx = j
            break
    return "\n".join(lines[start_idx + 1 : end_idx])


# ---------------------------------------------------------------------------
# MODE A — 구조(헤더 순서) 검사
# ---------------------------------------------------------------------------


def check_structure(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    actual = re.findall(r"^##\s+(.+?)\s*$", text, re.MULTILINE)

    if actual == EXPECTED_HEADERS:
        print(f"ok: {path}는 CONTRACT.md §3 헤더 순서를 만족합니다")
        return

    missing = [h for h in EXPECTED_HEADERS if h not in actual]
    extra = [h for h in actual if h not in EXPECTED_HEADERS]
    if missing:
        print(f"누락된 헤더: {missing}", file=sys.stderr)
    if extra:
        print(f"허용되지 않는 헤더: {extra}", file=sys.stderr)
    if not missing and not extra:
        for i, (a, e) in enumerate(zip(actual, EXPECTED_HEADERS)):
            if a != e:
                print(
                    f"헤더 순서 불일치: {i + 1}번째 헤더가 '{e}'여야 하는데 '{a}'입니다",
                    file=sys.stderr,
                )
                break
    print(f"기대한 순서: {EXPECTED_HEADERS}", file=sys.stderr)
    print(f"실제 순서: {actual}", file=sys.stderr)
    raise SystemExit(1)


# ---------------------------------------------------------------------------
# MODE B(b1) — 수치 출처 검증
# ---------------------------------------------------------------------------


def _flatten_numbers(obj):
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        yield float(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _flatten_numbers(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _flatten_numbers(v)


def _known_values(results: dict):
    """results.json에서 '알려진 값'을 만든다.

    `literal`: data[].x, data[].y, summary 아래 모든 리프 값 — 리포트가 그대로
    인용할 수 있는(예: "concurrency=250에서") 모든 값. parameters/run은 제외한다
    (계측된 결과가 아니라 입력/메타데이터이기 때문).

    `groups`: (metric, series)별로 묶은 y값 집합 — 파생값(비율/차이) 후보는 이
    그룹 "안에서만" 만든다. x(스윕 파라미터)나 서로 무관한 metric끼리 짝지으면
    (예: concurrency 4000과 250의 비율, 또는 CPU%와 레이턴시ms의 비율) 실험적으로
    아무 의미 없는 산술 결과가 우연히 다른 숫자와 근접 매치되는 사고가 난다 —
    같은 metric·series의 값끼리만 비교해야 "이 지표가 X% 늘었다"는 서술과
    실제로 대응한다.

    `summary_values`: summary 리프 값. baseline/threshold처럼 그 자체가 이미
    data[]에서 "파생"된 요약치라 summary끼리, 또는 summary와 임의의 y값 사이의
    파생값도 후보로 인정한다."""
    literal: set[float] = set()
    groups: dict[tuple, set[float]] = {}
    for row in results.get("data", []):
        x = row.get("x")
        y = row.get("y")
        if isinstance(x, (int, float)) and not isinstance(x, bool):
            literal.add(float(x))
        if isinstance(y, (int, float)) and not isinstance(y, bool):
            literal.add(float(y))
            key = (row.get("metric"), row.get("series"))
            groups.setdefault(key, set()).add(float(y))
    summary_values = set(_flatten_numbers(results.get("summary", {})))
    literal.update(summary_values)
    return literal, groups, summary_values


def _decimals_of(token: str) -> int:
    return len(token.split(".", 1)[1]) if "." in token else 0


def _rel_close(a: float, b: float) -> bool:
    denom = abs(b) if b else abs(a)
    if denom == 0:
        return a == b
    return abs(a - b) / denom < REL_TOL


def _round_close(a: float, b: float, decimals: int) -> bool:
    # decimals=0(정수로 표기된 값, 예: "16배")일 때 round()만 쓰면 허용 오차가
    # ±0.5(수 크기에 따라 최대 수 %)까지 벌어져, ~수십 개의 known 값 사이에서
    # 우연히 근접하는 파생값이 쏟아진다(경험적으로 확인됨). round 일치에 더해
    # 상대 오차 1.5% 상한을 같이 요구한다 — "표시 자릿수 반올림"은 통과시키되
    # "그냥 비슷한 숫자"는 걸러낸다.
    if round(a, decimals) != round(b, decimals):
        return False
    denom = max(abs(a), abs(b), 1.0)
    return abs(a - b) / denom < 0.015


# 파생값(비율/차이) 후보 생성은 반드시 같은 metric·series 그룹 안에서만, 또는
# summary 값을 한쪽에 낀 조합으로만 한다(_derived_pairs) — 그래도 같은 지표의
# 서로 다른 x끼리는 값 개수가 많으면(예: 9개 스윕 포인트) 우연한 근접 비율이
# 나올 수 있다는 잔여 위험은 남는다. 아래 두 가드는 그 중 가장 뻔한 우연(크기
# 차이가 커서 사실상 리터럴 재탕인 차이값, 5% 이내라 "배수" 주장의 대상이 아닌
# 비율)만 걸러낸다 — 완벽한 조작 탐지가 아니라 사람 리뷰를 보조하는 장치임을
# 전제로 한다(CONTRACT.md 문서 신뢰성 규칙이 최종 근거).
def _difference_candidates(a: float, b: float) -> list[float]:
    lo, hi = sorted((abs(a), abs(b)))
    if hi == 0 or lo / hi < 0.05:
        return []
    return [abs(a - b), a - b]


def _ratio_candidates(a: float, b: float) -> list[float]:
    if b == 0:
        return []
    ratio = a / b
    if 0.95 <= ratio <= 1.05:
        return []
    # a/b("몇 배")에 더해 퍼센트 증감(("a는 b보다 X% 늘었다") = (a-b)/b*100)도
    # 후보에 넣는다 — "몇 배" 표현만 인정하면 훨씬 자연스러운 "X% 증가/감소"
    # 서술이 전부 오탐(too strict)으로 막힌다. 반대로 100*a/b("a는 b의 X%")는
    # 일부러 뺐다 — 이 리포트 문체는 "a가 b의 X%다" 식으로 쓰지 않을뿐더러,
    # 임의의 두 비슷한 크기 값을 나누면 0.1~0.3 사이 값이 흔히 나오고 그걸
    # ×100하면 10~30 사이 "그럴듯한 조작 배수"와 정확히 겹치는 구간에 몰려
    # 오검출(too loose)의 주범이 됐다(실측: 실제 리포트 안에서만도 여러 건
    # 우연히 일치).
    return [ratio, 100 * (ratio - 1)]


def _derived_pairs(groups: dict, summary_values: set[float]):
    for group in groups.values():
        yield from itertools.permutations(group, 2)
    all_y: set[float] = set()
    for group in groups.values():
        all_y |= group
    for s in summary_values:
        for y in all_y:
            yield (s, y)
            yield (y, s)
    yield from itertools.permutations(summary_values, 2)


def _is_sourced(num: float, decimals: int, literal: set[float], groups: dict, summary_values: set[float]) -> bool:
    # (i) 리터럴 값(그대로, 또는 표시 자릿수로 반올림한 값) — x/y/summary 전체 대상.
    for k in literal:
        if _rel_close(num, k) or _round_close(num, k, decimals):
            return True
    # (ii) 같은 metric·series 그룹 안(또는 summary와 짝지은) 두 값의 단순
    # 파생값: a/b, 100*a/b, 퍼센트 증감, |a-b|, a-b
    for a, b in _derived_pairs(groups, summary_values):
        candidates = _difference_candidates(a, b) + _ratio_candidates(a, b)
        for c in candidates:
            if _rel_close(num, c) or _round_close(num, c, decimals):
                return True
    return False


def _line_context(text: str, start: int, end: int) -> str:
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", end)
    if line_end == -1:
        line_end = len(text)
    return text[line_start:line_end].strip()


def check_numbers(readme_text: str, results: dict) -> list[str]:
    literal, groups, summary_values = _known_values(results)
    failures: list[str] = []
    for section_name in CONTENT_SECTIONS:
        section = extract_section(readme_text, section_name)
        if section is None:
            # 섹션 자체가 없으면 수치 출처를 검사할 대상이 없다는 뜻이 아니라
            # CONTRACT.md §3 위반이다 — 조용히 건너뛰면 "수치가 모두 추적됩니다"
            # 라고 거짓 통과를 내보내게 된다. Mode A(--structure)가 실행되지 않는
            # 경로에서도 이 실패만으로 누락이 드러나야 한다.
            failures.append(f"'## {section_name}' 섹션이 없습니다 — CONTRACT.md §3 위반")
            continue
        for m in NUMBER_RE.finditer(section):
            token = m.group(0)
            num = float(token.replace(",", ""))
            decimals = _decimals_of(token)
            if not _is_sourced(num, decimals, literal, groups, summary_values):
                context = _line_context(section, m.start(), m.end())
                failures.append(
                    f"'## {section_name}' 섹션의 수치 '{token}'을(를) results.json에서 "
                    f'추적할 수 없습니다 — 맥락: "{context}"'
                )
    return failures


# ---------------------------------------------------------------------------
# MODE B(b2) — 안건 문체 점검 (경고 전용)
# ---------------------------------------------------------------------------


def check_question_tone(readme_text: str, agenda_text: str) -> list[str]:
    warnings: list[str] = []
    readme_q = extract_section(readme_text, QUESTION_HEADER)
    if readme_q is None:
        return warnings
    readme_q = readme_q.strip()

    agenda_q = extract_section(agenda_text, QUESTION_HEADER)
    if agenda_q is not None:
        agenda_q = agenda_q.strip()
        ratio = difflib.SequenceMatcher(None, readme_q, agenda_q).ratio()
        if ratio > SIMILARITY_THRESHOLD:
            warnings.append(
                "경고: README '## 안건'이 agenda.md의 원문 안건과 거의 동일합니다"
                f"(문자 유사도 {ratio:.0%}) — CONTRACT.md §3은 QUESTION을 격식체 "
                "연구 질문이 아니라 담백한 구어체 한 문장으로 쓰라고 명시한다"
                f'(예: "{QUESTION_EXAMPLE}"). 다시 써 보는 것을 권장합니다.'
            )

    marker_hits = sum(1 for marker in STACKED_CLAUSE_MARKERS if marker in readme_q)
    ends_formal = readme_q.rstrip().endswith("는가?")
    if marker_hits >= 2 or ends_formal:
        warnings.append(
            "경고: README '## 안건'이 격식체 연구 질문 패턴(조건절이 주렁주렁 붙은 "
            "문장, '~는가?'로 끝맺음)에 해당합니다 — CONTRACT.md §3이 QUESTION의 "
            f'안티패턴으로 명시한 표현입니다(예: "~는 ~부터 ~가 급격히 튀며 ~에 '
            f'진입하는가?"). 실제로 궁금해서 물어보는 말투로 다시 쓰세요'
            f'(CONTRACT.md 예: "{QUESTION_EXAMPLE}").'
        )
    return warnings


# ---------------------------------------------------------------------------
# MODE B 진입점
# ---------------------------------------------------------------------------


def check_content(readme_path: Path, results_path: Path, agenda_path: Path | None) -> None:
    readme_text = readme_path.read_text(encoding="utf-8")
    results = json.loads(results_path.read_text(encoding="utf-8"))

    failures = check_numbers(readme_text, results)

    if agenda_path is not None:
        agenda_text = agenda_path.read_text(encoding="utf-8")
        for warning in check_question_tone(readme_text, agenda_text):
            print(warning, file=sys.stderr)

    if failures:
        for f in failures:
            print(f, file=sys.stderr)
        raise SystemExit(1)

    print(f"ok: {readme_path}의 결과/발견 사항 및 분석/결론 수치가 모두 results.json에서 추적됩니다")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--structure", type=Path, help="MODE A: README.template.md 또는 README.md 경로")
    mode.add_argument("--content", type=Path, help="MODE B: 채워진 실험 README.md 경로")
    parser.add_argument("--results", type=Path, help="MODE B 필수: results.json 경로")
    parser.add_argument("--agenda", type=Path, help="MODE B 선택: agenda.md 경로 (안건 문체 점검용)")
    args = parser.parse_args()

    if args.structure is not None:
        check_structure(args.structure)
        return

    if args.results is None:
        parser.error("--content는 --results와 함께 사용해야 합니다")
    check_content(args.content, args.results, args.agenda)


if __name__ == "__main__":
    main()
