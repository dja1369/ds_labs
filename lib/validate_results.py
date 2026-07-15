"""python -m lib.validate_results <results.json>

results.json을 schemas/results.schema.json 대비 검증한다. 실패 시 exit 1과 함께
어떤 필드가 왜 틀렸는지 stderr에 출력한다(fail loud) — 검증을 통과해야만 다음
파이프라인 단계(CSV 파생/차트 생성)로 진행할 수 있다.
"""
import json
import sys
from pathlib import Path

import jsonschema

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "results.schema.json"


def validate(results_path: Path) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    data = json.loads(results_path.read_text(encoding="utf-8"))

    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    if errors:
        for err in errors:
            location = "/".join(str(p) for p in err.path) or "<root>"
            print(f"schema violation at {location}: {err.message}", file=sys.stderr)
        raise SystemExit(1)

    # 스키마는 x가 number|string 유니온이지만, 같은 metric 안에서 숫자/문자열이
    # 섞이면 lib/chart.py가 선 그래프/막대 그래프 중 무엇을 그려야 할지 결정할 수
    # 없다. 혼용은 여기(검증 단계)에서 거부한다.
    x_types_by_metric: dict[str, set[type]] = {}
    for row in data.get("data", []):
        x_types_by_metric.setdefault(row["metric"], set()).add(type(row["x"]))
    for metric, types in x_types_by_metric.items():
        is_numeric_only = types <= {int, float}
        is_string_only = types <= {str}
        if not (is_numeric_only or is_string_only):
            print(
                f"metric '{metric}'의 x 값이 숫자와 문자열을 혼용합니다 — 허용되지 않습니다",
                file=sys.stderr,
            )
            raise SystemExit(1)

    print(f"OK: {results_path} matches schema_version {data.get('schema_version')}")


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: python -m lib.validate_results <results.json>", file=sys.stderr)
        raise SystemExit(2)
    validate(Path(sys.argv[1]))


if __name__ == "__main__":
    main()
