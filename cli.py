import asyncio
from pathlib import Path

from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn
import typer

from parserlib.core.client_loader import load_clients
from parserlib.core.exporters import ExporterKind, create_exporter, list_exporter_names
from parserlib.core.models import FetchPlan
from parserlib.core.registry import ClientRegistry

app = typer.Typer(no_args_is_help=True)

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

@app.command("fetch")
def fetch(
    url: str = typer.Argument(help="Resource URL"),
    fmt: ExporterKind = typer.Option(ExporterKind.PDF, "--format", case_sensitive=False, help="Export format"),
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

            from_chapter = typer.prompt("From chapter index", type=int, default=1)

            to_chapter = typer.prompt("To chapter index", type=int, default=total)

            if from_chapter < 1:
                raise typer.BadParameter("From must be >= 1")

            if from_chapter > to_chapter:
                raise typer.BadParameter("From cannot be greater than to")
            if to_chapter > total:
                raise typer.BadParameter(
                    f"to={to_chapter} is out of range, total chapters: {total}"
                )

            plan = FetchPlan(
                work=work,
                from_chapter=from_chapter - 1,
                to_chapter=to_chapter - 1,
            )
            with Progress(
                SpinnerColumn(),
                "[progress.description]{task.description}",
                BarColumn(),
                TaskProgressColumn(),
            ) as progress:
                task_id = progress.add_task("Parsing...", total=None)

                callback = CliProgressCallback(progress, task_id)

                groups = await client.fetch(plan, callback)

        output.mkdir(parents=True, exist_ok=True)
        path = exporter.export(work=work, groups=groups, output_path=output)

        typer.echo(f"Saved: {str(path)}")

    asyncio.run(run())

if __name__ == "__main__":
    app()