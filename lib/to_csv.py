"""python -m lib.to_csv <results.json> <out.csv>

results.json의 data[]에서 results.csv를 파생시킨다. 컬럼은 data[] 필드와
1:1 고정이다 — 템플릿별 자유 컬럼은 허용하지 않는다(파서가 어떤 실험이든
같은 컬럼셋을 기대할 수 있어야 자동 파싱이 신뢰성을 갖는다).
"""
import csv
import json
import sys
from pathlib import Path

FIELDS = ["metric", "series", "x_label", "x", "y", "unit", "note"]


def to_csv(results_path: Path, out_path: Path) -> None:
    data = json.loads(results_path.read_text(encoding="utf-8"))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for row in data["data"]:
            writer.writerow({field: row.get(field, "") if row.get(field) is not None else "" for field in FIELDS})

    print(f"wrote {out_path}")


def main() -> None:
    if len(sys.argv) != 3:
        print("usage: python -m lib.to_csv <results.json> <out.csv>", file=sys.stderr)
        raise SystemExit(2)
    to_csv(Path(sys.argv[1]), Path(sys.argv[2]))


if __name__ == "__main__":
    main()
