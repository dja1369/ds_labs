"""python -m lib.scaffold_report <experiments/<slug>/>

<experiment_dir>/results/results.json과 <experiment_dir>/params.yml을 읽어,
기계적으로 도출 가능한 부분만 채운 README.md 초안을 WRITE/OVERWRITE한다.
CONTRACT.md 3절의 헤더 블록과 '## section' 헤더 구조를 그대로 따르되(현재
lib/check_report.py Mode A가 없어 CONTRACT.md에서 직접 헤더 목록을
하드코딩했다), 판단이 필요한 절은 "TODO(scaffold_report)" 표시가 붙은
자리표시자로 남긴다 — 이후 사람/Claude의 프로즈 작성 단계(ds-lab-run-experiment
스킬 8단계)가 이 자리를 채운다.

기계적으로 채우는 부분은 다음 두 곳뿐이다:
- RESULTS: results.json의 data[]를 metric/series별로 묶어 표를 조립한다
  (100% 기계적 — 판단 불필요).
- SETUP: params.yml의 최상위 스칼라/리스트 값과 results.json의
  run.environment(arch/cpu_cores/memory_gb)만 그대로 옮긴다. 이 값들은 단순
  key:value 전사이기 때문이다. docker-compose.yml/experiment.sh에서 나오는
  인프라 설명 불릿(예: "redis:7-alpine, cpus: 2 제한")은 원본이 산문으로
  큐레이션된 것이라 이 스크립트가 지어낼 수 없다 — TODO로 남긴다.

QUESTION/HYPOTHESIS/SUMMARY/METHOD/FINDINGS/CONCLUSION/NEXT_QUESTIONS은
전부 판단이 필요한 프로즈이므로 TODO 자리표시자로만 남긴다.

대상 README.md가 이미 존재하고 "TODO(scaffold_report)" 마커를 하나도
포함하지 않으면(=이미 사람이 다 채운 완성 문서로 판단) 실패한다(fail loud)
— lib/scaffold.py와 마찬가지로 기존 산출물을 조용히 덮어쓰지 않는다.
"""
import json
import re
import sys
from pathlib import Path

import yaml

from lib.check_report import extract_section

TODO = "TODO(scaffold_report)"

# 결과/구성은 기계적으로 채워지는 절이라 판단 프로즈가 들어있는지 확인할
# 대상에서 뺀다 — 나머지 절은 전부 사람/Claude가 채워야 하는 판단 영역이다.
JUDGMENT_SECTIONS = [
    "안건",
    "가설",
    "요약",
    "방법",
    "발견 사항 및 분석",
    "결론",
    "연관 연구 주제 제안",
]

# CONTRACT.md 3절의 '## section' 헤더 순서. lib/check_report.py Mode A가
# 아직 없으므로 여기서 직접 하드코딩한다 — 착지하면 그쪽으로 대체한다.
SECTION_ORDER = [
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

DATE_PREFIX_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-")


def _fmt_num(value) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _derive_date(experiment_dir: Path, results: dict) -> str:
    m = DATE_PREFIX_RE.match(experiment_dir.name)
    if m:
        return m.group(1)
    started_at = results.get("run", {}).get("started_at", "")
    return started_at[:10] if started_at else TODO


def _build_results(data: list[dict]) -> str:
    if not data:
        return f"{TODO}: results.json의 data[]가 비어 있습니다"

    rows_by_metric: dict[str, list[dict]] = {}
    for row in data:
        rows_by_metric.setdefault(row["metric"], []).append(row)

    tables = []
    for metric, rows in rows_by_metric.items():
        x_label = rows[0]["x_label"]
        unit = rows[0]["unit"]

        series_names: list[str] = []
        for row in rows:
            if row["series"] is not None and row["series"] not in series_names:
                series_names.append(row["series"])

        xs = sorted({row["x"] for row in rows}, key=lambda v: (isinstance(v, str), v))

        lines = [f"**{metric}**", ""]
        if series_names:
            header = [x_label] + [f"{s} ({unit})" for s in series_names]
            lookup = {(row["x"], row["series"]): row["y"] for row in rows}
            body_rows = [
                [_fmt_num(x)]
                + [_fmt_num(lookup[(x, s)]) if (x, s) in lookup else "" for s in series_names]
                for x in xs
            ]
        else:
            header = [x_label, f"{metric} ({unit})"]
            lookup = {row["x"]: row["y"] for row in rows}
            body_rows = [[_fmt_num(x), _fmt_num(lookup[x])] for x in xs]

        lines.append("| " + " | ".join(header) + " |")
        lines.append("|" + "---|" * len(header))
        for cells in body_rows:
            lines.append("| " + " | ".join(cells) + " |")
        tables.append("\n".join(lines))

    return "\n\n".join(tables)


def _build_setup(params: dict, environment: dict) -> str:
    lines = [
        f"- {TODO}: docker-compose.yml/experiment.sh 기반 인프라 설명"
        " (이미지, 리소스 제한, 부하 도구 등) — 사람이 직접 작성"
    ]
    for key, value in params.items():
        if key == "smoke" or isinstance(value, dict):
            continue
        lines.append(f"- {key}: {value}")
    if environment:
        arch = environment.get("arch", "?")
        cpu_cores = environment.get("cpu_cores", "?")
        memory_gb = environment.get("memory_gb", "?")
        lines.append(f"- 실행 환경(컨테이너 내부 관측치): {arch}, {cpu_cores} core, {memory_gb}GB")
    return "\n".join(lines)


def _header_block(template_name: str, date: str) -> str:
    return (
        f"# {TODO}: 제목 작성 (질문형 한 문장, 예: \"Redis에 요청을 얼마나 넣으면 죽을까?\")\n"
        "\n"
        f"- 날짜: {date}\n"
        f"- 템플릿: {template_name}\n"
        f"- 태그: {TODO}: 쉼표로 구분한 태그 작성"
    )


def _still_fully_scaffolded(existing: str) -> bool:
    """모든 판단 절(제목 포함)이 아직 스캐폴딩 당시의 TODO 자리표시자 그대로인지
    확인한다. 하나라도 실제 프로즈로 바뀌었다면 이미 작성이 시작된 문서이므로
    False를 돌려준다 — "TODO 마커가 파일 어딘가에 하나라도 있으면 통째로
    덮어써도 된다"는 예전 판단은 8/9 절이 이미 완성된 문서에서 나머지 1개
    절만 TODO로 남아 있어도 전체를 조용히 지워버리는 사고를 낼 수 있었다."""
    title_match = re.match(r"^#\s+(.+)$", existing, re.MULTILINE)
    if not title_match or TODO not in title_match.group(1):
        return False
    for name in JUDGMENT_SECTIONS:
        section = extract_section(existing, name)
        if section is None or TODO not in section:
            return False
    return True


def scaffold_report(experiment_dir: Path) -> Path:
    results_path = experiment_dir / "results" / "results.json"
    params_path = experiment_dir / "params.yml"
    readme_path = experiment_dir / "README.md"

    if not results_path.is_file():
        print(f"results.json이 없습니다: {results_path}", file=sys.stderr)
        raise SystemExit(1)
    if not params_path.is_file():
        print(f"params.yml이 없습니다: {params_path}", file=sys.stderr)
        raise SystemExit(1)

    if readme_path.is_file():
        existing = readme_path.read_text(encoding="utf-8")
        if not _still_fully_scaffolded(existing):
            print(
                f"이미 존재합니다: {readme_path} — 판단 절 중 하나 이상이 이미 "
                f"작성되어 있어(TODO 마커가 없음) 덮어쓰지 않습니다. 전체를 다시 "
                "스캐폴딩하려면 파일을 먼저 지우세요",
                file=sys.stderr,
            )
            raise SystemExit(1)

    results = json.loads(results_path.read_text(encoding="utf-8"))
    params = yaml.safe_load(params_path.read_text(encoding="utf-8")) or {}

    template_name = results.get("experiment", {}).get("template", TODO)
    date = _derive_date(experiment_dir, results)
    environment = results.get("run", {}).get("environment", {})

    sections = {
        "안건": f'{TODO}: 담백한 한 문장으로 작성 (예: "Redis에 요청을 얼마나 넣으면 죽을까?")',
        "가설": f"{TODO}: 실행 전 예상했던 바를 서술",
        "요약": f"{TODO}: 3~5줄 불릿. 현상 → 반전 → 진짜 원인 방향 순으로",
        "구성": _build_setup(params, environment),
        "방법": f"{TODO}: 수행한 시나리오를 번호를 매겨 순서대로 서술하고, 각 단계의 실행 커맨드를 코드 블록으로",
        "결과": _build_results(results.get("data", [])),
        "발견 사항 및 분석": (
            f"### 성능 및 일반적인 사례\n{TODO}: 관측된 현상을 일반적인 패턴으로 서술\n\n"
            f"### 추가로 알면 좋을 사항\n{TODO}: 표면적 현상과 실제 원인이 다를 때의 정정·단서"
        ),
        "결론": f"{TODO}: 가설 중 맞은 부분/틀린 부분/아직 모르는 것을 불릿이나 번호로",
        "연관 연구 주제 제안": f"{TODO}: 이번 결과에서 자연스럽게 파생되는 후속 질문 1~3개",
    }

    parts = [_header_block(template_name, date)]
    for heading in SECTION_ORDER:
        parts.append(f"## {heading}\n{sections[heading]}")

    content = "\n\n".join(parts) + "\n"
    readme_path.write_text(content, encoding="utf-8")
    print(f"wrote {readme_path} (기계적 초안 — {TODO} 표시는 judgment pass에서 채울 것)")
    return readme_path


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: python -m lib.scaffold_report <experiments/<slug>/>", file=sys.stderr)
        raise SystemExit(2)
    scaffold_report(Path(sys.argv[1]))


if __name__ == "__main__":
    main()
