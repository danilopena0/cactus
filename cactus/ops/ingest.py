from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

from cactus.llm import VISION_MODEL, call_llm_structured, load_schema
from cactus.sources import load_source
from cactus.wiki import (
    append_log,
    build_wiki_context,
    get_wiki_dir,
    list_pages,
    read_index,
    read_page,
    search_wiki,
    write_index,
    write_page,
)


class WikiPageDraft(BaseModel):
    filename: str
    action: str            # "create" | "update"
    title: str
    tags: list[str]
    confidence: str        # "high" | "medium" | "low"
    full_content: str      # complete markdown including frontmatter


class IngestPlan(BaseModel):
    pages: list[WikiPageDraft]
    index_update: str
    log_entry: str


INGEST_SYSTEM = """You are the knowledge architect for a personal knowledge base called Cactus.
Your job is to process new source material and produce or update wiki pages.

SCHEMA CONTRACT — follow this exactly:
{schema}

EXISTING WIKI STATE:
{existing_pages_summary}

TODAY: {today}
"""

INGEST_USER = """A new source has been added to the knowledge base.

SOURCE METADATA:
- Filename: {filename}
- Type: {source_type}
- Size: {char_count} characters

SOURCE CONTENT:
<source>
{source_content}
</source>

EXISTING WIKI PAGES (full content of relevant pages):
<wiki>
{wiki_context}
</wiki>

CURRENT INDEX:
<index>
{current_index}
</index>

TASK:
Analyze the source and produce a structured ingestion plan. You must:

1. Identify 10-15 distinct concepts, facts, methods, or entities worth capturing.
   Each concept becomes one wiki page. Prefer atomic pages (one thing per page).

2. For each concept:
   - Check if an existing wiki page already covers it.
   - If yes: action = "update", add new information and update Connections/Sources.
   - If no: action = "create", write the full page from scratch.

3. Write each page according to the SCHEMA CONTRACT exactly:
   - Include all frontmatter fields.
   - Set confidence based on how well-sourced the claim is.
   - Populate Connections with [[links]] to other pages you are creating or that exist.
   - If the source reveals a contradiction with an existing page, add it to Open Questions.

4. Produce an updated index.md grouping all pages (old and new) by inferred category.

5. Produce a log entry in this exact format:
   ## {datetime_now} — Ingest: {filename}
   - **Action**: ingest
   - **Source**: {filename}
   - **Pages affected**: <comma-separated filenames>
   - **Summary**: <one sentence>
"""

INGEST_USER_IMAGE = """A new image source has been added to the knowledge base.

SOURCE METADATA:
- Filename: {filename}
- Type: image

Analyze the image above. Identify all concepts, entities, processes, or information
visible in the image. Then follow the same instructions as a text ingest.

EXISTING WIKI PAGES:
<wiki>
{wiki_context}
</wiki>

CURRENT INDEX:
<index>
{current_index}
</index>
"""


def run_ingest(source_path: str, project_root: Path, console=None) -> None:
    today = datetime.now().strftime("%Y-%m-%d")
    datetime_now = datetime.now().strftime("%Y-%m-%d %H:%M")

    sources_dir = project_root / "sources"
    sources_dir.mkdir(exist_ok=True)
    wiki_dir = get_wiki_dir(project_root)
    wiki_dir.mkdir(exist_ok=True)

    if console:
        console.print(f"[cyan]Loading source:[/cyan] {source_path}")
    source = load_source(source_path, sources_dir)

    existing = list_pages(wiki_dir)
    existing_summary = _build_existing_summary(wiki_dir, existing)

    if len(existing) <= 20:
        relevant = existing
    else:
        hits = search_wiki(wiki_dir, source.text_content[:2000])
        relevant = [f for f, _ in hits]

    wiki_context = build_wiki_context(wiki_dir, relevant) if relevant else "(No existing pages yet)"
    current_index = read_index(wiki_dir)
    schema = load_schema()

    system = INGEST_SYSTEM.format(
        schema=schema,
        existing_pages_summary=existing_summary,
        today=today,
    )

    if source.source_type == "image" and source.image_b64:
        # Groq vision uses OpenAI-compatible image_url format with data URIs
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{source.media_type};base64,{source.image_b64}"
                        },
                    },
                    {
                        "type": "text",
                        "text": INGEST_USER_IMAGE.format(
                            filename=source.filename,
                            wiki_context=wiki_context,
                            current_index=current_index,
                        ),
                    },
                ],
            }
        ]
    else:
        messages = [
            {
                "role": "user",
                "content": INGEST_USER.format(
                    filename=source.filename,
                    source_type=source.source_type,
                    char_count=source.char_count,
                    source_content=source.text_content,
                    wiki_context=wiki_context,
                    current_index=current_index,
                    datetime_now=datetime_now,
                ),
            }
        ]

    if console:
        console.print("[cyan]Calling Claude for ingest plan...[/cyan]")

    ingest_model = VISION_MODEL if source.source_type == "image" else None
    plan: IngestPlan = call_llm_structured(
        system=system,
        messages=messages,
        output_format=IngestPlan,
        max_tokens=8000,
        **({"model": ingest_model} if ingest_model else {}),
    )

    if console:
        console.print(f"[green]Plan ready: {len(plan.pages)} pages to write[/green]")

    for draft in plan.pages:
        write_page(wiki_dir, draft.filename, draft.full_content)
        label = "[green]Created[/green]" if draft.action == "create" else "[yellow]Updated[/yellow]"
        if console:
            console.print(f"  {label} [bold]{draft.filename}[/bold]")

    write_index(wiki_dir, plan.index_update)
    append_log(wiki_dir, plan.log_entry)

    if console:
        console.print("[bold green]Ingest complete.[/bold green]")


def _build_existing_summary(wiki_dir: Path, filenames: list[str]) -> str:
    if not filenames:
        return "(Empty wiki — no pages yet)"

    lines = [f"The wiki currently has {len(filenames)} pages:"]
    for fn in filenames[:50]:
        content = read_page(wiki_dir, fn)
        for line in content.split("\n"):
            if line.startswith("title:"):
                title = line.replace("title:", "").strip()
                lines.append(f"  - {fn} (title: {title})")
                break
        else:
            lines.append(f"  - {fn}")

    if len(filenames) > 50:
        lines.append(f"  ... and {len(filenames) - 50} more.")

    return "\n".join(lines)
