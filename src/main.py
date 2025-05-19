#!/usr/bin/env python3
"""
Bilibili Danmaku Downloader

This program downloads danmaku (comments) from Bilibili videos.
It supports various resource types: 
- avid (single video, av format)
- bvid (single video, bv format)
- epid (episode)
- ssid (season)
- mdid (media)
"""
import asyncio
import os
import re
import sys
from datetime import datetime

import typer
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from rich.table import Table

from client import BilibiliAPIClient
from danmaku import DanmakuDownloader, DanmakuExporter, DanmakuExportFormat
from resources import ResourceID, ResourceFetcher

app = typer.Typer(
    name="BiliDanmakuDownload",
    help="Download danmaku (comments) from Bilibili videos",
    add_completion=False
)
console = Console()

DEFAULT_OUTPUT_DIR = "output"
DEFAULT_COOKIE_FILE = "cookie.txt"


async def download_all_danmaku(
        resource_id_input,
        output_dir: str = DEFAULT_OUTPUT_DIR,
        output_format: str = DanmakuExportFormat.XML,
        cookie_file: str = DEFAULT_COOKIE_FILE
) -> None:
    """
    Download danmaku for all content associated with a resource ID.
    
    Args:
        resource_id_input: ResourceID object or resource ID string (avid, BVid, epid, ssid, mdid)
        output_dir: Output directory
        output_format: Output format
        cookie_file: Path to the cookie file
    """
    # Parse resource ID if it's a string
    if isinstance(resource_id_input, ResourceID):
        resource_id = resource_id_input
        resource_id_str = str(resource_id)
    else:
        resource_id_str = resource_id_input
        try:
            resource_id = ResourceID(resource_id_str)
        except ValueError as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            return

    console.print(f"[bold green]Processing resource:[/bold green] {resource_id_str}")

    # Create client and fetchers
    async with BilibiliAPIClient(cookie_file=cookie_file) as client:
        resource_fetcher = ResourceFetcher(client)
        danmaku_downloader = DanmakuDownloader(client)

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        try:
            # Get content IDs
            console.print("[bold]Fetching content metadata...[/bold]")
            content_dict = await resource_fetcher.fetch_content_ids(resource_id)

            # Print content info
            table = Table(title=f"Content of {resource_id_str}")
            table.add_column("AVID", style="cyan")
            table.add_column("Title", style="green")
            table.add_column("CID", style="yellow")
            table.add_column("Duration", style="magenta")

            for id_key, (title, cid, duration) in content_dict.items():
                # Format duration as MM:SS
                minutes = duration // 60
                seconds = duration % 60
                duration_str = f"{minutes}:{seconds:02d}"
                table.add_row(id_key, title, cid, duration_str)

            console.print(table)

            # Download danmaku for each content
            with Progress(
                    TextColumn("[bold blue]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    TimeRemainingColumn(),
                    console=console
            ) as progress:
                total_task = progress.add_task("[cyan]Total progress", total=len(content_dict))

                for id_key, (title, cid, duration) in content_dict.items():
                    task_desc = f"Downloading danmaku for: {title}"
                    dl_task = progress.add_task(task_desc, total=1)

                    # Generate safe filename
                    safe_title = re.sub(r'[\\/*?:"<>|]', "_", title)
                    output_filename = f"{resource_id_str}_{id_key}_{safe_title}.{output_format}"
                    output_path = os.path.join(output_dir, output_filename)

                    # Download danmaku with duration-based segment calculation
                    try:
                        danmaku_list = await danmaku_downloader.download_danmaku(cid, duration)
                        await DanmakuExporter.export(danmaku_list, output_path, output_format)

                        progress.update(dl_task, completed=1, description=f"[green]✓ Downloaded: {title}")
                    except Exception as e:
                        progress.update(dl_task, completed=1, description=f"[red]✗ Failed: {title} - {e}")

                    # Update total progress
                    progress.update(total_task, advance=1)

            console.print(f"[bold green]✓ Download completed![/bold green] Files saved to: {output_dir}")

        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")


@app.command()
def download(
        resource_id: str = typer.Argument(..., help="Resource ID (avid, BVid, epid, ssid, mdid) "),
        output_dir: str = typer.Option(DEFAULT_OUTPUT_DIR, "--output", "-o", help="Output directory"),
        format: str = typer.Option(
            DanmakuExportFormat.XML,
            "--format",
            "-f",
            help="Output format (xml, json, csv, txt)"
        ),
        cookie_file: str = typer.Option(
            DEFAULT_COOKIE_FILE,
            "--cookie",
            "-c",
            help="Path to the cookie file"
        )
) -> None:
    """
    Download danmaku for a Bilibili resource.
    
    Examples:
        python main.py download av12345
        python main.py download BV1xx411c7mD
        python main.py download ep67890 --format json
        python main.py download ss12345 -o my_danmaku -f csv
        python main.py download av12345 --cookie my_cookie.txt
    """
    if format not in [DanmakuExportFormat.XML, DanmakuExportFormat.JSON,
                      DanmakuExportFormat.CSV, DanmakuExportFormat.TEXT]:
        console.print(f"[bold red]Error:[/bold red] Invalid output format: {format}")
        console.print("Supported formats: xml, json, csv, txt")
        return

    asyncio.run(download_all_danmaku(resource_id, output_dir, format, cookie_file))


@app.command()
def interactive() -> None:
    """
    Run the program in interactive mode.
    """
    console.print("[bold blue]Bilibili Danmaku Downloader - Interactive Mode[/bold blue]")
    console.print("Enter resource ID (avid, BVid, epid, ssid, mdid) or 'q' to quit:")

    while True:
        resource_id_str = console.input("[bold cyan]> [/bold cyan]")

        if resource_id_str.lower() in ["q", "quit", "exit"]:
            console.print("[bold]Goodbye![/bold]")
            break

        if not resource_id_str:
            continue

        # Verify resource ID immediately
        try:
            resource_id = ResourceID(resource_id_str)
            console.print(f"[bold green]Valid resource ID:[/bold green] {resource_id_str} (Type: {resource_id.resource_type})")
        except ValueError as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            console.print("Please enter a valid resource ID or 'q' to quit:")
            continue

        # Ask for format
        console.print("Select output format:")
        console.print("1. XML (default, compatible with most players)")
        console.print("2. JSON (for analysis)")
        console.print("3. CSV (for spreadsheet)")
        console.print("4. Plain text")

        format_choice = console.input("[bold cyan]Format [1-4] > [/bold cyan]")
        if not format_choice or format_choice == "1":
            format = DanmakuExportFormat.XML
        elif format_choice == "2":
            format = DanmakuExportFormat.JSON
        elif format_choice == "3":
            format = DanmakuExportFormat.CSV
        elif format_choice == "4":
            format = DanmakuExportFormat.TEXT
        else:
            console.print("[yellow]Invalid choice, using XML.[/yellow]")
            format = DanmakuExportFormat.XML

        # Ask for output directory
        default_dir = os.path.join(DEFAULT_OUTPUT_DIR, datetime.now().strftime("%Y%m%d_%H%M%S"))
        output_dir = console.input(f"[bold cyan]Output directory [{default_dir}] > [/bold cyan]")
        if not output_dir:
            output_dir = default_dir

        # Ask for cookie file
        cookie_file = console.input(f"[bold cyan]Cookie file [{DEFAULT_COOKIE_FILE}] > [/bold cyan]")
        if not cookie_file:
            cookie_file = DEFAULT_COOKIE_FILE

        # Start download
        asyncio.run(download_all_danmaku(resource_id, output_dir, format, cookie_file))

        # Continue prompt
        console.print("\nEnter another resource ID or 'q' to quit:")


if __name__ == "__main__":
    try:
        if len(sys.argv) == 1:
            # Default to interactive mode if no arguments
            interactive()
        else:
            app()
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Operation cancelled by user.[/bold yellow]")
        sys.exit(0)
