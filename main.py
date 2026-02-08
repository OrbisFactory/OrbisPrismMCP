#!/usr/bin/env python3
# CLI entry point: delegates to src.prism.cli

import sys
from pathlib import Path

# Allow running from root without installing the package (prism is in src/prism)
_root = Path(__file__).resolve().parent
sys.path.insert(0, str(_root / "src"))

from src.prism.entrypoints import main

if __name__ == "__main__":
    sys.exit(main())
