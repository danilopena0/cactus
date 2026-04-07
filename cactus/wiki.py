import re
from datetime import date
from pathlib import Path


def get_wiki_dir(project_root: Path) -> Path:
    return project_root / "wiki"


def list_pages(wiki_dir: Path) -> list[str]:
    if not wiki_dir.exists():
        return []
    return [
        p.name for p in wiki_dir.glob("*.md")
        if p.name not in ("index.md", "log.md")
    ]


def read_page(wiki_dir: Path, filename: str) -> str:
    return (wiki_dir / filename).read_text(encoding="utf-8")


def write_page(wiki_dir: Path, filename: str, content: str) -> None:
    # Normalize filename to kebab-case
    filename = re.sub(r"[^a-z0-9.\-]", "-", filename.lower()).strip("-")
    if not filename.endswith(".md"):
        filename += ".md"

    today = date.today().isoformat()
    if "updated:" in content:
        content = re.sub(r"updated: \d{4}-\d{2}-\d{2}", f"updated: {today}", content)

    wiki_dir.mkdir(parents=True, exist_ok=True)
    (wiki_dir / filename).write_text(content, encoding="utf-8")


def read_index(wiki_dir: Path) -> str:
    p = wiki_dir / "index.md"
    return p.read_text(encoding="utf-8") if p.exists() else ""


def write_index(wiki_dir: Path, content: str) -> None:
    (wiki_dir / "index.md").write_text(content, encoding="utf-8")


def append_log(wiki_dir: Path, entry: str) -> None:
    log_path = wiki_dir / "log.md"
    if log_path.exists():
        existing = log_path.read_text(encoding="utf-8")
    else:
        existing = "# Cactus Operation Log\n\n---\n"
    log_path.write_text(existing + "\n" + entry + "\n", encoding="utf-8")


def search_wiki(wiki_dir: Path, query: str) -> list[tuple[str, str]]:
    query_words = set(query.lower().split())
    results = []

    for filename in list_pages(wiki_dir):
        content = read_page(wiki_dir, filename)
        content_lower = content.lower()

        score = sum(content_lower.count(w) for w in query_words)
        if score > 0:
            lines = content.split("\n")
            excerpt_lines = []
            for line in lines:
                if any(w in line.lower() for w in query_words):
                    excerpt_lines.append(line)
                    if len(excerpt_lines) >= 5:
                        break
            excerpt = "\n".join(excerpt_lines)
            results.append((filename, excerpt, score))

    results.sort(key=lambda x: x[2], reverse=True)
    return [(f, e) for f, e, _ in results[:15]]


def build_wiki_context(wiki_dir: Path, filenames: list[str]) -> str:
    parts = []
    for fn in filenames:
        path = wiki_dir / fn
        if path.exists():
            content = read_page(wiki_dir, fn)
            parts.append(f"=== {fn} ===\n{content}")
    return "\n\n".join(parts)
