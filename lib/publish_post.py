"""python -m lib.publish_post <experiments/<date>-<experiment_id>/>

experiments/<slug>/README.md + results/results.json으로부터 Jekyll 포스트
(docs/_posts/<slug>.md)와 이미지(docs/assets/images/<slug>/*.png)를 생성한다.
README의 상대 이미지 경로(results/charts/xxx.png)는 baseurl을 반영하는
Liquid `relative_url` 표현식으로 자동 치환된다(7장 baseurl 처리 참고).
"""
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_ROOT = REPO_ROOT / "docs"
CONFIG_PATH = DOCS_ROOT / "_config.yml"

TITLE_RE = re.compile(r"^# (?P<title>.+)$", re.MULTILINE)
FIELD_RE = re.compile(r"^- (?P<key>날짜|템플릿|태그): (?P<value>.+)$", re.MULTILINE)
IMAGE_RE = re.compile(r"!\[(?P<alt>[^\]]*)\]\(results/charts/(?P<name>[^)]+)\)")


def _repo_url() -> str:
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    repo_url = config.get("repo_url")
    if not repo_url:
        print(f"{CONFIG_PATH}에 repo_url이 설정되어 있지 않습니다", file=sys.stderr)
        raise SystemExit(1)
    return repo_url.rstrip("/")


def _front_matter_date(started_at: str) -> str:
    dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
    return dt.strftime("%Y-%m-%d %H:%M:%S %z")


def publish(experiment_dir: Path) -> Path:
    slug = experiment_dir.name  # <date>-<experiment_id>
    readme_path = experiment_dir / "README.md"
    results_path = experiment_dir / "results" / "results.json"
    charts_dir = experiment_dir / "results" / "charts"

    if not readme_path.is_file():
        print(f"README.md가 없습니다: {readme_path}", file=sys.stderr)
        raise SystemExit(1)
    if not results_path.is_file():
        print(f"results.json이 없습니다: {results_path}", file=sys.stderr)
        raise SystemExit(1)

    readme = readme_path.read_text(encoding="utf-8")
    results = json.loads(results_path.read_text(encoding="utf-8"))

    title_match = TITLE_RE.search(readme)
    if not title_match:
        print(f"README.md에 '# 제목' 헤더가 없습니다: {readme_path}", file=sys.stderr)
        raise SystemExit(1)
    title = title_match.group("title").strip()

    fields = {m.group("key"): m.group("value").strip() for m in FIELD_RE.finditer(readme)}
    tags = [t for t in re.split(r"[,\s]+", fields.get("태그", "")) if t]

    body_start = readme.find("## 안건")
    if body_start == -1:
        print(f"README.md에 '## 안건' 섹션이 없습니다: {readme_path}", file=sys.stderr)
        raise SystemExit(1)
    body = readme[body_start:]

    image_dir = DOCS_ROOT / "assets" / "images" / slug
    image_dir.mkdir(parents=True, exist_ok=True)
    if charts_dir.is_dir():
        for png in sorted(charts_dir.glob("*.png")):
            shutil.copyfile(png, image_dir / png.name)

    def _rewrite_image(match: re.Match) -> str:
        alt, name = match.group("alt"), match.group("name")
        return f"![{alt}]({{{{ '/assets/images/{slug}/{name}' | relative_url }}}})"

    body = IMAGE_RE.sub(_rewrite_image, body)

    front_matter = {
        "layout": "post",
        "title": title,
        "date": _front_matter_date(results["run"]["started_at"]),
        "categories": list(tags),
        "tags": list(tags),
        "experiment_id": results["experiment"]["id"],
        "experiment_url": f"{_repo_url()}/tree/main/experiments/{slug}",
        "run_id": results["run"]["run_id"],
    }
    front_matter_yaml = yaml.safe_dump(front_matter, allow_unicode=True, sort_keys=False)
    post = f"---\n{front_matter_yaml}---\n\n{body}"

    posts_dir = DOCS_ROOT / "_posts"
    posts_dir.mkdir(parents=True, exist_ok=True)
    post_path = posts_dir / f"{slug}.md"
    post_path.write_text(post, encoding="utf-8")
    print(f"published {post_path}")
    return post_path


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: python -m lib.publish_post <experiments/<date>-<experiment_id>/>", file=sys.stderr)
        raise SystemExit(2)
    publish(Path(sys.argv[1]))


if __name__ == "__main__":
    main()
