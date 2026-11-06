"""Install the knowledge-team agent definitions so Claude Code can use them in ANY project folder.

Copies video_tools/agents/*.md (except README) to the user-level agents folder (~/.claude/agents).
Run again after editing a definition. A new Claude Code session is needed before new agent types appear.

    python agents/install.py            # install / update
    python agents/install.py --check    # show which installed copies are missing or outdated
"""
import argparse
import filecmp
import shutil
from pathlib import Path

SRC = Path(__file__).resolve().parent
DST = Path.home() / ".claude" / "agents"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="only report differences, copy nothing")
    a = ap.parse_args()
    files = sorted(p for p in SRC.glob("*.md") if p.name.lower() != "readme.md")
    DST.mkdir(parents=True, exist_ok=True)
    for f in files:
        target = DST / f.name
        state = "missing" if not target.exists() else ("same" if filecmp.cmp(f, target, shallow=False) else "outdated")
        if a.check:
            print(f"{f.name:<28} {state}")
        elif state != "same":
            shutil.copy2(f, target)
            print(f"{f.name:<28} installed ({state} before)")
        else:
            print(f"{f.name:<28} up to date")
    print(f"target: {DST}")


if __name__ == "__main__":
    main()
