from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(
    name="cactus",
    help="Personal LLM-powered knowledge base. Powered by Claude.",
    add_completion=False,
)
console = Console()


def _find_project_root() -> Path:
    cwd = Path.cwd()
    for candidate in [cwd, *cwd.parents]:
        if (candidate / "wiki").is_dir():
            return candidate
    return cwd


@app.command()
def ingest(
    source: str = typer.Argument(..., help="Path to a file (PDF, image, text) or URL to ingest."),
    root: Optional[Path] = typer.Option(None, "--root", help="Project root directory."),
) -> None:
    """Ingest a new source into the wiki."""
    project_root = root or _find_project_root()

    console.print(Panel(
        f"[bold]Ingesting:[/bold] {source}\n[dim]Project root: {project_root}[/dim]",
        title="Cactus Ingest",
        border_style="green",
    ))

    try:
        from cactus.ops.ingest import run_ingest
        run_ingest(source, project_root, console=console)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


@app.command()
def query(
    question: str = typer.Argument(..., help="Question to ask the knowledge base."),
    no_file: bool = typer.Option(False, "--no-file", help="Do not file discovered gaps back into the wiki."),
    root: Optional[Path] = typer.Option(None, "--root", help="Project root directory."),
) -> None:
    """Query the wiki and get a synthesized answer."""
    project_root = root or _find_project_root()

    console.print(Panel(
        f"[bold]Query:[/bold] {question}",
        title="Cactus Query",
        border_style="blue",
    ))

    try:
        from cactus.ops.query import run_query
        run_query(question, project_root, file_discoveries=not no_file, console=console)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


@app.command()
def lint(
    fix: bool = typer.Option(False, "--fix", help="Auto-fix issues that can be safely repaired."),
    root: Optional[Path] = typer.Option(None, "--root", help="Project root directory."),
) -> None:
    """Check the wiki for issues: contradictions, orphan pages, broken links, schema violations."""
    project_root = root or _find_project_root()

    console.print(Panel(
        "[bold]Running wiki health check...[/bold]",
        title="Cactus Lint",
        border_style="yellow",
    ))

    try:
        from cactus.ops.lint import run_lint
        report = run_lint(project_root, auto_fix=fix, console=console)

        if report.issues:
            table = Table(title=f"Lint Report — {report.pages_scanned} pages scanned")
            table.add_column("Severity", style="bold")
            table.add_column("Page", style="cyan")
            table.add_column("Type")
            table.add_column("Description")

            severity_styles = {"error": "red", "warning": "yellow", "info": "dim"}
            for issue in sorted(report.issues, key=lambda i: i.severity):
                style = severity_styles.get(issue.severity, "white")
                table.add_row(
                    f"[{style}]{issue.severity.upper()}[/{style}]",
                    issue.page,
                    issue.issue_type,
                    issue.description[:80],
                )
            console.print(table)

        console.print(f"\n[bold]Summary:[/bold] {report.summary}")

        if report.auto_fixable and not fix:
            console.print(
                f"\n[dim]{len(report.auto_fixable)} page(s) can be auto-fixed. "
                f"Run [bold]cactus lint --fix[/bold] to apply.[/dim]"
            )
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


@app.command()
def status(
    root: Optional[Path] = typer.Option(None, "--root", help="Project root directory."),
) -> None:
    """Show a summary of the current wiki state."""
    project_root = root or _find_project_root()
    wiki_dir = project_root / "wiki"
    sources_dir = project_root / "sources"

    pages = list(wiki_dir.glob("*.md")) if wiki_dir.exists() else []
    page_count = sum(1 for p in pages if p.name not in ("index.md", "log.md"))
    sources = list(sources_dir.iterdir()) if sources_dir.exists() else []

    console.print(Panel(
        f"[bold]Wiki pages:[/bold] {page_count}\n"
        f"[bold]Sources:[/bold] {len(sources)}\n"
        f"[bold]Project root:[/bold] {project_root}",
        title="Cactus Status",
        border_style="green",
    ))


if __name__ == "__main__":
    app()
