from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

from cactus.llm import call_llm, call_llm_structured, load_schema
from cactus.wiki import (
    append_log,
    build_wiki_context,
    get_wiki_dir,
    list_pages,
    read_index,
    search_wiki,
    write_page,
)


class QueryDiscovery(BaseModel):
    has_discoveries: bool
    new_pages: list[dict]   # list of {filename, content}
    log_entry: str


QUERY_SYSTEM = """You are the query interface for a personal knowledge base called Cactus.
Your job is to answer questions by synthesizing information from the wiki pages provided.

SCHEMA CONTRACT:
{schema}

TODAY: {today}
"""

QUERY_USER = """QUESTION: {question}

RELEVANT WIKI PAGES:
<wiki>
{wiki_context}
</wiki>

FULL INDEX (for reference):
<index>
{index}
</index>

INSTRUCTIONS:
1. Answer the question thoroughly using only the wiki content above.
2. Cite your sources using [[PageTitle]] inline links.
3. If the wiki does not fully answer the question, say so explicitly and describe what's missing.
4. After your answer, add a "## Gaps & Discoveries" section listing:
   - New connections between pages not reflected in their Connections sections.
   - Information from training that could fill a gap (flagged as "Not in wiki").

Format:
## Answer
<your synthesized answer with [[wiki links]]>

## Sources Used
- [[PageTitle]] — why you used it

## Gaps & Discoveries
- <gap or connection>
"""

DISCOVERY_USER = """You just answered a query and found gaps and discoveries.

ORIGINAL QUESTION: {question}

YOUR ANSWER:
{answer}

TASK:
Decide whether any discovered gaps warrant new wiki pages.
Only create pages for concrete facts from the wiki that are missing as pages,
or clearly implied sub-topics the wiki should cover.
Do NOT create speculative pages based on training data alone.

If no meaningful discoveries, set has_discoveries = false and provide an empty new_pages list.
If has_discoveries = true, include a log entry in this format:
## {datetime_now} — Query (discoveries): {question_short}
- **Action**: query
- **Source**: "{question}"
- **Pages affected**: <comma-separated filenames of new pages>
- **Summary**: <one sentence>
"""


def run_query(
    question: str,
    project_root: Path,
    file_discoveries: bool = True,
    console=None,
) -> str:
    wiki_dir = get_wiki_dir(project_root)
    schema = load_schema()
    today = datetime.now().strftime("%Y-%m-%d")
    datetime_now = datetime.now().strftime("%Y-%m-%d %H:%M")

    if console:
        console.print(f"[cyan]Searching wiki for:[/cyan] {question}")

    search_results = search_wiki(wiki_dir, question)
    if not search_results:
        all_pages = list_pages(wiki_dir)
        search_results = [(fn, "") for fn in all_pages[:10]]

    relevant_filenames = [fn for fn, _ in search_results]
    wiki_context = build_wiki_context(wiki_dir, relevant_filenames)
    index = read_index(wiki_dir)

    if console:
        console.print(f"[dim]Retrieved {len(relevant_filenames)} relevant pages[/dim]")

    system = QUERY_SYSTEM.format(schema=schema, today=today)

    answer_messages = [
        {
            "role": "user",
            "content": QUERY_USER.format(
                question=question,
                wiki_context=wiki_context,
                index=index,
            ),
        }
    ]

    answer_parts: list[str] = []

    def collect(chunk: str) -> None:
        answer_parts.append(chunk)
        if console:
            console.print(chunk, end="")

    if console:
        console.print("\n[bold]Answer:[/bold]\n")

    answer = call_llm(
        system=system,
        messages=answer_messages,
        max_tokens=8000,
        stream_callback=collect if console else None,
    )

    if not answer and answer_parts:
        answer = "".join(answer_parts)

    if console:
        console.print("\n")

    if file_discoveries:
        discovery: QueryDiscovery = call_llm_structured(
            system=system,
            messages=[
                *answer_messages,
                {"role": "assistant", "content": answer},
                {
                    "role": "user",
                    "content": DISCOVERY_USER.format(
                        question=question,
                        answer=answer,
                        datetime_now=datetime_now,
                        question_short=question[:60],
                    ),
                },
            ],
            output_format=QueryDiscovery,
            max_tokens=8000,
        )

        if discovery.has_discoveries:
            for page_data in discovery.new_pages:
                write_page(wiki_dir, page_data["filename"], page_data["content"])
                if console:
                    console.print(f"[green]Filed discovery:[/green] {page_data['filename']}")
            if discovery.log_entry:
                append_log(wiki_dir, discovery.log_entry)

    pages_used = ", ".join(relevant_filenames[:5])
    log_entry = (
        f"## {datetime_now} — Query: {question[:60]}\n\n"
        f"- **Action**: query\n"
        f"- **Source**: \"{question}\"\n"
        f"- **Pages affected**: {pages_used}\n"
        f"- **Summary**: Query synthesized from {len(relevant_filenames)} pages."
    )
    append_log(wiki_dir, log_entry)

    return answer
