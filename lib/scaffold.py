"""python -m lib.scaffold <new-slug>

templates/_skeleton을 templates/<new-slug>로 복사하고, 파일 내용에 등장하는
"_skeleton" 문자열을 <new-slug>로 치환한다. `cp -r`의 크로스플랫폼 대체다
(cmd.exe에는 `cp`가 없다) — 항상 runner 컨테이너 내부에서 실행된다.

대상 디렉토리가 이미 존재하면 실패한다(fail loud) — 기존 템플릿을 조용히
덮어쓰지 않는다.
"""
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_ROOT = REPO_ROOT / "templates"
SKELETON = TEMPLATES_ROOT / "_skeleton"
SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif"}


def scaffold(slug: str) -> Path:
    if not SLUG_RE.match(slug):
        print(
            f"'{slug}'는 유효한 슬러그가 아닙니다 (소문자/숫자/하이픈만, 예: my-new-template)",
            file=sys.stderr,
        )
        raise SystemExit(1)

    target = TEMPLATES_ROOT / slug
    if target.exists():
        print(f"이미 존재합니다: {target} — 기존 템플릿을 덮어쓰지 않습니다", file=sys.stderr)
        raise SystemExit(1)

    for src in SKELETON.rglob("*"):
        if src.is_dir():
            continue
        rel = src.relative_to(SKELETON)
        dest_rel = Path(*(part.replace("_skeleton", slug) for part in rel.parts))
        dest = target / dest_rel
        dest.parent.mkdir(parents=True, exist_ok=True)

        if src.suffix.lower() in BINARY_SUFFIXES:
            dest.write_bytes(src.read_bytes())
        else:
            text = src.read_text(encoding="utf-8")
            dest.write_text(text.replace("_skeleton", slug), encoding="utf-8")

        if src.stat().st_mode & 0o111:
            dest.chmod(dest.stat().st_mode | 0o111)

    print(f"scaffolded templates/{slug}/ (templates/_skeleton/ 복사)")
    return target


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: python -m lib.scaffold <new-slug>", file=sys.stderr)
        raise SystemExit(2)
    scaffold(sys.argv[1])


if __name__ == "__main__":
    main()
