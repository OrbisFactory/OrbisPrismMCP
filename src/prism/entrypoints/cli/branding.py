# src/prism/entrypoints/cli/branding.py
#? CLI Branding: ASCII logo and version.

from rich.console import Console
from rich.text import Text

console = Console()

#_ ASCII art logo with Rich colors. We use a raw string for the backslashes.
LOGO = r"""
[blue]  ♦  [/blue]  ____  _____ ____  ____  ____  ____ _____ ____ _   _ ____  _____ ____  
[blue] ♦   ♦ [/blue] |  _ \| ____/ ___||  _ \|  _ \|  _ \_   _/ ___| | | / ___|| ____|  _ \ 
[blue]♦     ♦[/blue] | |_) |  _| \___ \| |_) | |_) | |_) || | \___ \| |_| \___ \|  _| | |_) |
[blue] ♦   ♦ [/blue] |  _ <| |___ ___) |  __/|  _ <|  _ < | |  ___) |  _  |___) | |___|  _ < 
[blue]  ♦  [/blue] |_| \_\_____|____/|_|   |_| \|_| \_\|_| |____/|_| |_|____/|_____|_| \_\
"""

VERSION_TEXT = "VERSION 0.4.0 | ORBISFACTORY"

def get_logo_and_version() -> Text:
    """Returns the ASCII art logo and version information combined as a Rich Text object."""
    logo_lines = LOGO.strip().split('\n')
    cleaned_logo_lines = [Text.from_markup(line).plain for line in logo_lines]
    logo_width = max(len(line) for line in cleaned_logo_lines) if cleaned_logo_lines else 0

    centered_version_text = VERSION_TEXT.center(logo_width)
    
    full_output = Text.from_markup(LOGO)
    full_output.append(f"\n{centered_version_text}")
    
    return full_output

def print_logo() -> None:
    """Prints the logo and version directly to the Rich console."""
    console.print(get_logo_and_version())