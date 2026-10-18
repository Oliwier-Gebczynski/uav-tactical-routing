"""Repository paths shared by Python tools."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def resolve_input_path(value):
    """Prefer an explicit existing path, then resolve repository data paths."""
    path = Path(value).expanduser()
    return path if path.is_absolute() or path.exists() else ROOT / path
