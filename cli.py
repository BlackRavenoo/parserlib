import asyncio
from pathlib import Path
import re

from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn
import typer

from parserlib.core.client_loader import load_clients
from parserlib.core.exporters import ExporterKind, create_exporter, list_exporter_names
from parserlib.core.models import ChapterEntry, FetchPlan
from parserlib.core.registry import ClientRegistry

app = typer.Typer(no_args_is_help=True)

def _parse_selection_range(selection: str, max_index: int) -> tuple[int, int]:
    raw = selection.strip().lower()
    if raw == "all":
        return (1, max_index)

    match = re.fullmatch(r"(\d+)(?:-(\d+))?", raw)
    if not match:
        raise typer.BadParameter("Unsupported selection. Use all, N or N-M")

    left = int(match.group(1))
    right = int(match.group(2) or match.group(1))

    if left > right:
        raise typer.BadParameter(f"Invalid range: {raw}")

    if left < 1 or left > max_index:
        raise typer.BadParameter(f"Index {left} is out of range 1..{max_index}")

    if right < 1 or right > max_index:
        raise typer.BadParameter(f"Index {right} is out of range 1..{max_index}")

    return (left, right)

def _format_chapter(chapter: ChapterEntry) -> str:
    return f"[{chapter.id}] {chapter.title}"

def _resolve_format(file_path: Path, fmt: ExporterKind | None) -> ExporterKind:
    if fmt is not None:
        return fmt

    suffix = file_path.suffix.lower().lstrip(".")
    try:
        return ExporterKind(suffix)
    except ValueError as exc:
        supported = ", ".join(list_exporter_names())
        raise typer.BadParameter(
            f"Cannot detect format from extension '{file_path.suffix}'. Use --format. Supported: {supported}"
        ) from exc

class CliProgressCallback:
    def __init__(self, progress: Progress, task_id: int):
        self.progress = progress
        self.task_id = task_id

    def __call__(self, current: int, total: int, title: str):
        self.progress.update(
            self.task_id,
            completed=current,
            total=total,
            description=title
        )

@app.callback()
def bootstrap() -> None:
    load_clients()

@app.command("list-sites")
def list_sites():
    typer.echo("Supported sites:")
    for domain, client_cls in ClientRegistry.all().items():
        typer.echo(f"{domain} -> {client_cls.__name__}")

@app.command("list-formats")
def list_formats():
    typer.echo("Supported formats:")
    for name in list_exporter_names():
        typer.echo(name)

@app.command("append")
def append_file(
    url: str = typer.Argument(help="Resource URL"),
    file_path: Path = typer.Argument(help="Existing file path"),
    fmt: ExporterKind | None = typer.Option(None, "--format", case_sensitive=False, show_choices=True, help="File format (auto by extension if omitted)"),
):
    if not file_path.exists():
        raise typer.BadParameter(f"File not found: {file_path}")

    async def run() -> None:
        resolved_format = _resolve_format(file_path, fmt)
        exporter = create_exporter(resolved_format)

        if not exporter.supports_append:
            raise typer.BadParameter(f"Format '{resolved_format.value}' does not support append")

        async with ClientRegistry.get_by_url(url) as client:
            work = await client.inspect(url)
            existing_ids = exporter.get_downloaded_chapter_ids(file_path)

            downloaded = [chapter for chapter in work.chapters if chapter.id in existing_ids]
            missing = [chapter for chapter in work.chapters if chapter.id not in existing_ids]

            typer.echo(f"Found chapters in source: {len(work.chapters)}")
            typer.echo(f"Already downloaded: {len(downloaded)}")
            for chapter in downloaded:
                typer.echo(f"  + {_format_chapter(chapter)}")

            typer.echo(f"Missing chapters: {len(missing)}")
            for idx, chapter in enumerate(missing, start=1):
                typer.echo(f"{idx:>4}. {_format_chapter(chapter)}")

            if not missing:
                typer.echo("Nothing to append. All chapters are already in file.")
                return

            selection = typer.prompt(
                "Choose missing chapters (all, N or N-M)",
                default="all",
            )
            start_local, end_local = _parse_selection_range(selection, len(missing))
            selected_missing = missing[start_local - 1:end_local]

            chapter_index_by_id = {
                chapter.id: idx
                for idx, chapter in enumerate(work.chapters)
            }
            selected_work_indexes = sorted(
                chapter_index_by_id[chapter.id]
                for chapter in selected_missing
            )

            groups = []
            with Progress(
                SpinnerColumn(),
                "[progress.description]{task.description}",
                BarColumn(),
                TaskProgressColumn(),
            ) as progress:
                task_id = progress.add_task("Parsing selected chapters...", total=None)
                callback = CliProgressCallback(progress, task_id)

                for chapter_idx in selected_work_indexes:
                    plan = FetchPlan(work=work, from_chapter=chapter_idx, to_chapter=chapter_idx)
                    fetched = await client.fetch(plan, callback)
                    groups.extend(fetched)

            groups.sort(key=lambda group: group.id)
            exporter.append(work=work, groups=groups, file_path=file_path)

            typer.echo(f"Appended {len(groups)} chapters to: {file_path}")

    asyncio.run(run())

@app.command("fetch")
def fetch(
    url: str = typer.Argument(help="Resource URL"),
    fmt: ExporterKind = typer.Option(ExporterKind.PDF, "--format", case_sensitive=False, show_choices=True, help="Export format"),
    output: Path = typer.Option(Path("."), "--output", help="Output directory"),
):
    async def run() -> None:
        exporter = create_exporter(fmt)

        async with ClientRegistry.get_by_url(url) as client:
            work = await client.inspect(url)
            total = len(work.chapters)

            if total == 0:
                typer.echo("No chapters found for this URL")
                raise typer.Exit(1)

            typer.echo(f"Found {total} chapters:")
            for idx, chapter in enumerate(work.chapters, start=1):
                typer.echo(f"{idx:>4}. {chapter.title}")

            selection = typer.prompt(
                "Choose chapters (all, N or N-M)",
                default="all",
            )
            start_idx, end_idx = _parse_selection_range(selection, total)

            typer.echo(f"Selected chapters: {end_idx - start_idx + 1}")

            with Progress(
                SpinnerColumn(),
                "[progress.description]{task.description}",
                BarColumn(),
                TaskProgressColumn(),
            ) as progress:
                task_id = progress.add_task("Parsing...", total=None)

                callback = CliProgressCallback(progress, task_id)

                plan = FetchPlan(
                    work=work,
                    from_chapter=start_idx - 1,
                    to_chapter=end_idx - 1,
                )
                groups = await client.fetch(plan, callback)

            groups.sort(key=lambda group: group.id)

        output.mkdir(parents=True, exist_ok=True)
        path = exporter.export(work=work, groups=groups, output_path=output)

        typer.echo(f"Saved: {str(path)}")

    asyncio.run(run())

if __name__ == "__main__":
    app()