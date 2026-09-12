"""Small operating-system adapters used by the desktop UI."""

import os
import subprocess
import sys
from pathlib import Path


def open_path(path: Path) -> None:
    """Open a file or folder with the operating system's default application."""
    target = str(Path(path))
    if sys.platform.startswith("win"):
        os.startfile(target)
    elif sys.platform == "darwin":
        subprocess.run(["open", target], check=False)
    else:
        subprocess.run(["xdg-open", target], check=False)
