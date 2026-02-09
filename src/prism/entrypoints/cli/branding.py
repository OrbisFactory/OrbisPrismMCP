# src/prism/entrypoints/cli/branding.py
#? Branding del CLI: logo ASCII y versión.

from rich.console import Console
from rich.text import Text

console = Console()

#_ Logo en ASCII art con colores Rich. Usamos raw string para las barras invertidas.
LOGO = r"""
[blue]  ♦  [/blue]  _   _           _      _         _            __  __ _____ ____ ___ ____  
[blue] ♦   ♦ [/blue] | | | |         (_)    | |       | |          |  \/  | ____/ ___|_ _/ ___| 
[blue]♦     ♦[/blue] | |_| | ___  ___ _  ___| |_ ___  | |     ___  | |\/| |  _| | |    | |\\___ \ 
[blue] ♦   ♦ [/blue] |  _  |/ _ \/ __| |/ __| __/ _ \ | |    / _ \ | |  | | |__| | |___ | | ___) |
[blue]  ♦  [/blue] |_| |_|\___/\___|_|\___|\__\___/ |_|   | (_) ||_|  |_|_____\____|___|____/ 
"""

VERSION_TEXT = "Version 1.0.0 | OrbisFactory"

def get_logo_and_version() -> Text:
    """Retorna el logo en ASCII art y la información de la versión combinados, como un objeto Rich Text."""
    #_ El logo ya tiene los estilos Rich incorporados en la cadena.
    #_ Calculamos el ancho del logo (sin los códigos de color Rich) para centrar el texto de la versión.
    #_ Para un cálculo preciso, podríamos necesitar una función que elimine los códigos de Rich,
    #_ pero para este propósito, una estimación basada en las líneas es suficiente.
    logo_lines = LOGO.strip().split('\n')
    #_ Quitamos los tags de color para calcular el ancho real
    cleaned_logo_lines = [Text.from_markup(line).plain for line in logo_lines]
    logo_width = max(len(line) for line in cleaned_logo_lines) if cleaned_logo_lines else 0

    #_ Centramos el texto de la versión según el ancho del logo
    centered_version_text = VERSION_TEXT.center(logo_width)
    
    #_ Combinamos el logo y el texto de la versión en un solo objeto Text
    full_output = Text.from_markup(LOGO)
    full_output.append(f"\n{centered_version_text}")
    
    return full_output

def print_logo() -> None:
    """Imprime el logo y la versión directamente a la consola Rich."""
    console.print(get_logo_and_version())