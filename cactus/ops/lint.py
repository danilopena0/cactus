from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

from cactus.llm import call_llm_structured, load_schema
from cactus.wiki import (
    append_log,
    build_wiki_context,
    get_wiki_dir,
    list_pages,
    read_page,
    write_page,
)


class LintIssue(BaseModel):
    severity: str       # "error" | "warning" | "info"
    page: str
    issue_type: str     # "contradiction" | "orphan" | "missing_link" | "stale" | "schema_violation" | "asymmetric_connection" | "confidence_mismatch"
    description: str
    suggested_fix: str | None


class LintReport(BaseModel):
    issues: list[LintIssue]
    pages_scanned: int
    summary: str
    auto_fixable: list[str]


class LintFix(BaseModel):
    filename: str
    new_content: str
    fix_description: str


LINT_SYSTEM = """You are the quality auditor for a personal knowledge base called Cactus.
Your job is to find problems in wiki pages and report or fix them.

SCHEMA CONTRACT:
{schema}

TODAY: {today}
"""

LINT_SCAN_USER = """Perform a thorough quality audit of the following wiki pages.

WIKI CONTENT:
<wiki>
{wiki_context}
</wiki>

Check for ALL of the following:

1. **Schema violations**: Missing required frontmatter fields, wrong confidence values,
   malformed links, missing sections (Summary, Content, Connections, Open Questions, Sources).

2. **Orphan pages**: Pages with no incoming or outgoing Connections links.

3. **Broken links**: [[PageTitle]] references that don't match any existing page title.

4. **Asymmetric connections**: If page A links to B, B must link back to A.

5. **Contradictions**: Facts in one page that contradict facts in another (quote both).

6. **Stale sources**: Pages listing source files that don't appear to exist.
   Known source files: {source_files}

7. **Confidence mismatches**: Pages claiming confidence=high from a single source,
   or confidence=low when multiple strong sources are present.

For each issue, set severity:
- error: Breaks wiki integrity (broken link, contradiction, schema violation)
- warning: Degrades quality (orphan, asymmetric link, confidence mismatch)
- info: Minor improvement opportunity

List filenames you can AUTO-FIX (add missing links, fix frontmatter, repair schema)
without losing any information.
"""

LINT_FIX_USER = """Fix the following wiki page. Preserve ALL existing content.
Only make the minimal changes needed to fix the reported issues.

CURRENT CONTENT:
<page>
{current_content}
</page>

ISSUES TO FIX:
{issues_text}
"""

BATCH_SIZE = 20


def run_lint(project_root: Path, auto_fix: bool = False, console=None) -> LintReport:
    wiki_dir = get_wiki_dir(project_root)
    sources_dir = project_root / "sources"
    schema = load_schema()
    today = datetime.now().strftime("%Y-%m-%d")
    datetime_now = datetime.now().strftime("%Y-%m-%d %H:%M")

    all_pages = list_pages(wiki_dir)
    source_files = [p.name for p in sources_dir.iterdir()] if sources_dir.exists() else []

    if not all_pages:
        if console:
            console.print("[yellow]No wiki pages to lint.[/yellow]")
        return LintReport(issues=[], pages_scanned=0, summary="No pages.", auto_fixable=[])

    system = LINT_SYSTEM.format(schema=schema, today=today)
    all_issues: list[LintIssue] = []
    auto_fixable: list[str] = []

    for i in range(0, len(all_pages), BATCH_SIZE):
        batch = all_pages[i : i + BATCH_SIZE]
        if console:
            console.print(f"[cyan]Scanning pages {i + 1}–{i + len(batch)}...[/cyan]")

        wiki_context = build_wiki_context(wiki_dir, batch)

        report: LintReport = call_llm_structured(
            system=system,
            messages=[
                {
                    "role": "user",
                    "content": LINT_SCAN_USER.format(
                        wiki_context=wiki_context,
                        source_files=", ".join(source_files) or "(none)",
                    ),
                }
            ],
            output_format=LintReport,
            max_tokens=8000,
        )

        all_issues.extend(report.issues)
        auto_fixable.extend(report.auto_fixable)

    auto_fixable = list(set(auto_fixable))

    if auto_fix and auto_fixable:
        if console:
            console.print(f"\n[cyan]Auto-fixing {len(auto_fixable)} pages...[/cyan]")

        for filename in auto_fixable:
            issues_for_page = [i for i in all_issues if i.page == filename]
            issues_text = "\n".join(
                f"- [{i.severity.upper()}] {i.issue_type}: {i.description}"
                for i in issues_for_page
            )
            current_content = read_page(wiki_dir, filename)

            fix: LintFix = call_llm_structured(
                system=system,
                messages=[
                    {
                        "role": "user",
                        "content": LINT_FIX_USER.format(
                            current_content=current_content,
                            issues_text=issues_text,
                        ),
                    }
                ],
                output_format=LintFix,
                max_tokens=4000,
            )

            write_page(wiki_dir, fix.filename, fix.new_content)
            if console:
                console.print(f"  [green]Fixed:[/green] {fix.filename} — {fix.fix_description}")

    final_report = LintReport(
        issues=all_issues,
        pages_scanned=len(all_pages),
        summary=_summarize_issues(all_issues),
        auto_fixable=auto_fixable,
    )

    error_count = sum(1 for i in all_issues if i.severity == "error")
    warning_count = sum(1 for i in all_issues if i.severity == "warning")
    log_entry = (
        f"## {datetime_now} — Lint\n\n"
        f"- **Action**: lint\n"
        f"- **Source**: (full wiki scan)\n"
        f"- **Pages affected**: {len(all_pages)} pages scanned\n"
        f"- **Summary**: Found {error_count} errors and {warning_count} warnings across {len(all_pages)} pages."
    )
    append_log(wiki_dir, log_entry)

    return final_report


def _summarize_issues(issues: list[LintIssue]) -> str:
    if not issues:
        return "No issues found. Wiki is healthy."

    by_type: dict[str, int] = {}
    for issue in issues:
        by_type[issue.issue_type] = by_type.get(issue.issue_type, 0) + 1

    parts = [f"{count} {itype}" for itype, count in sorted(by_type.items())]
    return "Issues: " + ", ".join(parts)
