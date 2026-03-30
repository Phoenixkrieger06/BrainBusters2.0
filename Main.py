from __future__ import annotations

from pathlib import Path

from gui import run_gui

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "brainbuster.db"


if __name__ == "__main__":
    raise SystemExit(run_gui(DB_PATH))