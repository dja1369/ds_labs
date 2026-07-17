"""python -m lib.check_posts

docs/_posts/*.md에 대한 최소 무결성 검사(가벼운 Jekyll 발행 사전 점검):
1. 모든 포스트가 '---'로 감싼 YAML front matter를 갖고, 그 YAML이 파싱 가능한지.
2. 포스트 본문의 마크다운 이미지/링크 참조(`![alt](target)`/`[text](target)`,
   `lib/publish_post.py`가 생성하는 `{{ '/assets/...' | relative_url }}` 형태
   포함)가 실제로 docs/ 아래 존재하는 파일을 가리키는지.

실제 Jekyll 빌드(bundle install + jekyll build)는 이 저장소의 "항상
docker compose run --rm runner로만 실행" 관례에 비해 Ruby 툴체인이라는 별도
무게를 PR CI에 얹으므로, 발행 파이프라인이 만들어내는 산출물의 구조적 결함만
빠르게 잡는 정적 검사로 대체한다.
"""
import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_ROOT = REPO_ROOT / "docs"
POSTS_DIR = DOCS_ROOT / "_posts"

LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
LIQUID_RELATIVE_URL_RE = re.compile(r"""\{\{\s*['"]([^'"]+)['"]\s*\|\s*relative_url\s*\}\}""")
SKIP_PREFIXES = ("http://", "https://", "#", "mailto:")


def _check_front_matter(post: Path, text: str) -> tuple[dict | None, str, list[str]]:
    errors: list[str] = []
    if not text.startswith("---\n"):
        errors.append(f"{post}: front matter가 '---'로 시작하지 않습니다")
        return None, text, errors

    end = text.find("\n---", 4)
    if end == -1:
        errors.append(f"{post}: front matter를 닫는 '---'를 찾을 수 없습니다")
        return None, text, errors

    try:
        front_matter = yaml.safe_load(text[4:end])
    except yaml.YAMLError as exc:
        errors.append(f"{post}: front matter YAML 파싱 실패 — {exc}")
        return None, text, errors

    if not isinstance(front_matter, dict):
        errors.append(f"{post}: front matter가 key: value 매핑이 아닙니다")
        return None, text, errors

    body = text[end + len("\n---") :]
    return front_matter, body, errors


def _check_links(post: Path, body: str) -> list[str]:
    errors: list[str] = []
    for m in LINK_RE.finditer(body):
        target = m.group(1).strip()
        liquid_m = LIQUID_RELATIVE_URL_RE.fullmatch(target)
        if liquid_m:
            target = liquid_m.group(1)
        if target.startswith(SKIP_PREFIXES):
            continue

        target_path = target.split("#", 1)[0]
        if not target_path:
            continue
        if target_path.startswith("/"):
            resolved = DOCS_ROOT / target_path.lstrip("/")
        else:
            resolved = post.parent / target_path

        if not resolved.is_file():
            errors.append(
                f"{post}: 참조 '{target}'이(가) 가리키는 파일이 존재하지 않습니다 "
                f"(확인 경로: {resolved.relative_to(REPO_ROOT)})"
            )
    return errors


def check_posts() -> None:
    posts = sorted(POSTS_DIR.glob("*.md"))
    if not posts:
        print(f"ok: {POSTS_DIR}에 검사할 포스트가 없습니다")
        return

    all_errors: list[str] = []
    for post in posts:
        text = post.read_text(encoding="utf-8")
        front_matter, body, fm_errors = _check_front_matter(post, text)
        all_errors.extend(fm_errors)
        if front_matter is None:
            continue
        all_errors.extend(_check_links(post, body))

    if all_errors:
        for err in all_errors:
            print(err, file=sys.stderr)
        raise SystemExit(1)

    print(f"ok: {len(posts)}개 포스트의 front matter/이미지·링크 참조를 확인했습니다")


def main() -> None:
    check_posts()


if __name__ == "__main__":
    main()
