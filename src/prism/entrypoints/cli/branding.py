import sys
from rich.console import Console
from rich.text import Text

#_ Use stderr for branding to avoid polluting stdout (important for MCP/pipes)
console = Console(stderr=True)

# ... (LOGO and VERSION_TEXT constants remain the same)
LOGO = r"""
[blue] ██████╗ ██████╗ ██████╗ ██╗███████╗██████╗ ██████╗ ██╗███████╗███╗   ███╗[/blue]
[blue]██╔═══██╗██╔══██╗██╔══██╗██║██╔════╝██╔══██╗██╔══██╗██║██╔════╝████╗ ████║[/blue]
[blue]██║   ██║██████╔╝██████╔╝██║███████╗██████╔╝██████╔╝██║███████╗██╔████╔██║[/blue]
[blue]██║   ██║██╔══██╗██╔══██╗██║╚════██║██╔═══╝ ██╔══██╗██║╚════██║██║╚██╔╝██║[/blue]
[blue]╚██████╔╝██║  ██║██████╔╝██║███████║██║     ██║  ██║██║███████║██║ ╚═╝ ██║[/blue]
[blue] ╚═════╝ ╚═╝  ╚═╝╚═════╝ ╚═╝╚══════╝╚═╝     ╚═╝  ╚═╝╚═╝╚══════╝╚═╝     ╚═╝[/blue]
"""                                                                     

VERSION_TEXT = "VERSION 0.5.0 | ORBISFACTORY"

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
    """
    Prints the logo and version to the Rich console.
    Only prints if stderr is a TTY to avoid issues with MCP/Pipes.
    Falls back to plain text if encoding fails.
    """
    if not sys.stderr.isatty():
        return

    try:
        console.print(get_logo_and_version())
    except UnicodeEncodeError:
        # Fallback for limited encodings (like cp1252 in some Windows environments)
        sys.stderr.write(f"\n*** {VERSION_TEXT} ***\n\n")
