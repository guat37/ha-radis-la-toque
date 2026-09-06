"""Replace publication placeholders with the actual GitHub account name."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
TOKEN = "guat37"


def main() -> int:
    if len(sys.argv) != 2 or not sys.argv[1].strip():
        print("Usage: python scripts/set_github_owner.py <github_username>")
        return 2
    owner = sys.argv[1].strip().lstrip("@")
    changed = 0
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if TOKEN not in text:
            continue
        path.write_text(text.replace(TOKEN, owner), encoding="utf-8")
        changed += 1
    print(f"Updated {changed} files for GitHub owner @{owner}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
