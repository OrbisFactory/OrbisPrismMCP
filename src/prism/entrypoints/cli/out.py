# src/prism/entrypoints/cli/out.py
#? Salida del CLI con Rich: fases, éxito, error, tablas y spinners.

from contextlib import contextmanager
from typing import Any, Generator, List, Dict

from rich.console import Console
from rich.table import Table

#_ Instancia única de la consola para toda la salida
_console = Console()

def phase(msg: str) -> None:
    """Imprime un encabezado de fase en stdout (cian)."""
    _console.print(f"[cyan]{msg}[/cyan]")

def success(msg: str) -> None:
    """Imprime un mensaje de éxito en stdout (verde)."""
    _console.print(f"[green]✔ {msg}[/green]")

def error(msg: str) -> None:
    """Imprime un mensaje de error en stderr (rojo)."""
    _console.print(f"[red]✖ {msg}[/red]", style="bold")

def table(title: str, data: List[Dict[str, Any]], columns: List[str] | None = None) -> None:
    """
    Imprime una lista de diccionarios como una tabla bien formateada.
    
    Args:
        title (str): El título de la tabla.
        data (List[Dict[str, Any]]): Lista de diccionarios para las filas.
        columns (List[str] | None): Opcional. Lista de claves a usar como columnas. 
                                    Si es None, se usan las claves del primer diccionario.
    """
    if not data:
        _console.print(f"No data to display for '{title}'")
        return

    grid = Table(title=title, show_header=True, header_style="bold magenta")
    
    #_ Usa las claves del primer elemento si no se especifican columnas
    cols = columns or list(data[0].keys())
    
    for col in cols:
        grid.add_column(col)
    
    for item in data:
        #_ Convierte todos los valores a string para la tabla
        grid.add_row(*(str(item.get(col, '')) for col in cols))
        
    _console.print(grid)

@contextmanager
def status(msg: str) -> Generator[None, None, None]:
    """
    Muestra un spinner mientras se ejecuta una tarea.

    Uso:
        with out.status("Haciendo algo..."):
            time.sleep(2)
    """
    with _console.status(f"[cyan]{msg}[/cyan]", spinner="dots"):
        yield