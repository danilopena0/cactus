import base64
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import httpx
from pypdf import PdfReader


@dataclass
class Source:
    filename: str
    source_type: str       # "pdf" | "url" | "text" | "image"
    text_content: str
    image_b64: str | None
    media_type: str | None
    char_count: int


def load_source(path_or_url: str, sources_dir: Path) -> Source:
    if path_or_url.startswith(("http://", "https://")):
        return _load_url(path_or_url, sources_dir)

    p = Path(path_or_url)
    if not p.is_absolute():
        p = sources_dir / p

    suffix = p.suffix.lower()
    if suffix == ".pdf":
        return _load_pdf(p)
    elif suffix in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
        return _load_image(p)
    else:
        return _load_text(p)


def _load_url(url: str, sources_dir: Path) -> Source:
    response = httpx.get(url, follow_redirects=True, timeout=30)
    response.raise_for_status()
    text = response.text

    filename = _url_to_filename(url)
    dest = sources_dir / filename
    dest.write_text(text, encoding="utf-8")

    return Source(
        filename=filename,
        source_type="url",
        text_content=text[:150_000],
        image_b64=None,
        media_type=None,
        char_count=len(text),
    )


def _load_pdf(path: Path) -> Source:
    reader = PdfReader(path)
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    text = "\n\n".join(pages)

    return Source(
        filename=path.name,
        source_type="pdf",
        text_content=text[:150_000],
        image_b64=None,
        media_type=None,
        char_count=len(text),
    )


def _load_image(path: Path) -> Source:
    media_type = mimetypes.guess_type(path.name)[0] or "image/png"
    data = path.read_bytes()
    b64 = base64.standard_b64encode(data).decode("utf-8")

    return Source(
        filename=path.name,
        source_type="image",
        text_content="",
        image_b64=b64,
        media_type=media_type,
        char_count=0,
    )


def _load_text(path: Path) -> Source:
    text = path.read_text(encoding="utf-8", errors="replace")
    return Source(
        filename=path.name,
        source_type="text",
        text_content=text[:150_000],
        image_b64=None,
        media_type=None,
        char_count=len(text),
    )


def _url_to_filename(url: str) -> str:
    parsed = urlparse(url)
    domain = parsed.netloc.replace(".", "-")
    path = parsed.path.strip("/").replace("/", "-") or "index"
    return f"url-{domain}-{path[:50]}.html"
