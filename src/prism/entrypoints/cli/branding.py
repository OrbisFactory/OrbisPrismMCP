# src/prism/entrypoints/cli/branding.py
#? CLI Branding: ASCII logo and version.

from rich.console import Console
from rich.text import Text

console = Console()

#_ ASCII art logo with Rich colors. We use a raw string for the backslashes.
LOGO = r"""
[blue]  ♦  [/blue]  _   _           _      _         _            __  __ _____ ____ ___ ____  
[blue] ♦   ♦ [/blue] | | | |         (_)    | |       | |          |  \/  | ____/ ___|_ _/ ___| 
[blue]♦     ♦[/blue] | |_| | ___  ___ _  ___| |_ ___  | |     ___  | |\/| |  _| | |    | |\\___ \ 
[blue] ♦   ♦ [/blue] |  _  |/ _ \/ __| |/ __| __/ _ \ | |    / _ \ | |  | | |__| | |___ | | ___) |
[blue]  ♦  [/blue] |_| |_|\___/\___|_|\___|\__\___/ |_|   | (_) ||_|  |_|_____\____|___|____/ 
"""

VERSION_TEXT = "Version 1.0.0 | OrbisFactory"

def get_logo_and_version() -> Text:
    """Returns the ASCII art logo and version information combined as a Rich Text object."""
    #_ The logo already has Rich styles embedded in the string.
    #_ We calculate the logo's width (without Rich color codes) to center the version text.
    #_ For an accurate calculation, we might need a function to strip Rich codes,
    #_ but for this purpose, an estimation based on the lines is sufficient.
    logo_lines = LOGO.strip().split('\n')
    #_ We remove the color tags to calculate the actual width
    cleaned_logo_lines = [Text.from_markup(line).plain for line in logo_lines]
    logo_width = max(len(line) for line in cleaned_logo_lines) if cleaned_logo_lines else 0

    #_ Center the version text according to the logo's width
    centered_version_text = VERSION_TEXT.center(logo_width)
    
    #_ Combine the logo and version text into a single Text object
    full_output = Text.from_markup(LOGO)
    full_output.append(f"\n{centered_version_text}")
    
    return full_output

def print_logo() -> None:
    """Prints the logo and version directly to the Rich console."""
    console.print(get_logo_and_version())
