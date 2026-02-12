# src/prism/entrypoints/cli/out.py
#? Rich CLI Output: phases, success, error, tables, and spinners.

from contextlib import contextmanager
from typing import Any, Generator, List, Dict

from rich.console import Console
from rich.table import Table
from rich.progress import (
    Progress, 
    SpinnerColumn, 
    BarColumn, 
    TextColumn, 
    TimeElapsedColumn, 
    MofNCompleteColumn,
    TaskProgressColumn
)

#_ Separate console for status/error (stderr) and data (stdout)
#_ stdout must be reserved for protocol (MCP) or actual data.
_console = Console(stderr=True)
_data_console = Console()

def phase(msg: str) -> None:
    """Prints a phase header to stderr (cyan)."""
    _console.print(f"[cyan]{msg}[/cyan]")

def success(msg: str) -> None:
    """Prints a success message to stderr (green)."""
    _console.print(f"[green]✔ {msg}[/green]")

def error(msg: str) -> None:
    """Prints an error message to stderr (red)."""
    _console.print(f"[red]✖ {msg}[/red]", style="bold")

def table(title: str, data: List[Dict[str, Any]], columns: List[str] | None = None) -> None:
    """
    Prints a list of dictionaries as a well-formatted table to stdout.
    
    Args:
        title (str): The title of the table.
        data (List[Dict[str, Any]]): A list of dictionaries for the rows.
        columns (List[str] | None): Optional. A list of keys to use as columns. 
                                    If None, the keys from the first dictionary are used.
    """
    if not data:
        _data_console.print(f"No data to display for '{title}'")
        return

    grid = Table(title=title, show_header=True, header_style="bold magenta")
    
    #_ Use keys from the first item if columns are not specified
    cols = columns or list(data[0].keys())
    
    for col in cols:
        grid.add_column(col)
    
    for item in data:
        #_ Convert all values to string for the table
        grid.add_row(*(str(item.get(col, '')) for col in cols))
        
    _data_console.print(grid)

@contextmanager
def status(msg: str) -> Generator[None, None, None]:
    """
    Displays a spinner while a task is running (on stderr).

    Usage:
        with out.status("Doing something..."):
            time.sleep(2)
    """
    with _console.status(f"[cyan]{msg}[/cyan]", spinner="dots"):
        yield
def progress() -> Progress:
    """
    Returns a standardized Progress instance configured for the CLI.
    Uses the dedicated stderr console for a premium, non-blocking experience.
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=40), #_ Fixed width for a cleaner, more compact look
        TaskProgressColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=_console,
        transient=True,
    )
