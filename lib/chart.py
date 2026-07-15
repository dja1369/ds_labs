"""python -m lib.chart --results <results.json> --out <dir>

results.json의 data[]를 metric별로 그룹화해 PNG 차트를 생성한다. x가 전부
숫자면 선 그래프, 하나라도 문자열이면 막대 그래프를 그린다(혼용은
lib/validate_results.py가 이미 거부했으므로 여기서는 고려하지 않는다).
series가 여럿이면 한 차트에 여러 선/막대를 그리고 범례를 붙인다.

생성된 PNG 개수가 고유 metric 개수와 일치하지 않으면 실패로 간주한다
(무음 실패 금지). 파일명 규칙: charts/<metric 슬러그>.png.
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # 헤드리스 강제 (Dockerfile의 MPLBACKEND=Agg와 이중 안전장치)

import matplotlib.pyplot as plt

STYLE_PATH = Path(__file__).resolve().parent / "style.mplstyle"
plt.style.use(str(STYLE_PATH))


def _slug(metric: str) -> str:
    return metric.strip().lower().replace(" ", "_")


def _group_by_series(rows: list[dict]) -> dict:
    by_series: dict = defaultdict(list)
    for row in rows:
        by_series[row["series"]].append(row)
    return by_series


def line_chart(rows: list[dict], metric: str, out_path: Path) -> None:
    fig, ax = plt.subplots()
    by_series = _group_by_series(rows)
    for series, series_rows in by_series.items():
        series_rows = sorted(series_rows, key=lambda r: r["x"])
        xs = [r["x"] for r in series_rows]
        ys = [r["y"] for r in series_rows]
        ax.plot(xs, ys, marker="o", label=series if series else metric)
    ax.set_xlabel(rows[0]["x_label"])
    ax.set_ylabel(f'{metric} ({rows[0]["unit"]})')
    ax.set_title(metric)
    if any(series for series in by_series):
        ax.legend()
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def bar_chart(rows: list[dict], metric: str, out_path: Path) -> None:
    fig, ax = plt.subplots()
    by_series = _group_by_series(rows)
    categories = sorted({row["x"] for row in rows})
    n_series = max(len(by_series), 1)
    width = 0.8 / n_series
    for i, (series, series_rows) in enumerate(by_series.items()):
        lookup = {row["x"]: row["y"] for row in series_rows}
        ys = [lookup.get(category) for category in categories]
        offsets = [j + i * width for j in range(len(categories))]
        ax.bar(offsets, ys, width=width, label=series if series else metric)
    ax.set_xticks([j + width * (n_series - 1) / 2 for j in range(len(categories))])
    ax.set_xticklabels([str(c) for c in categories])
    ax.set_xlabel(rows[0]["x_label"])
    ax.set_ylabel(f'{metric} ({rows[0]["unit"]})')
    ax.set_title(metric)
    if any(series for series in by_series):
        ax.legend()
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def generate_charts(results_path: Path, out_dir: Path) -> int:
    data = json.loads(results_path.read_text(encoding="utf-8"))

    rows_by_metric: dict = defaultdict(list)
    for row in data["data"]:
        rows_by_metric[row["metric"]].append(row)

    out_dir.mkdir(parents=True, exist_ok=True)
    generated = 0
    for metric, rows in rows_by_metric.items():
        out_path = out_dir / f"{_slug(metric)}.png"
        numeric = all(isinstance(row["x"], (int, float)) for row in rows)
        if numeric:
            line_chart(rows, metric, out_path)
        else:
            bar_chart(rows, metric, out_path)
        generated += 1

    if generated != len(rows_by_metric):
        print("차트 생성이 완료되지 않았습니다 (일부 metric 누락)", file=sys.stderr)
        return 1
    print(f"generated {generated} chart(s) in {out_dir}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    raise SystemExit(generate_charts(Path(args.results), Path(args.out)))


if __name__ == "__main__":
    main()
