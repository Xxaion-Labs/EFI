#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = ("exo" + "cortical").lower()
TEXT_SUFFIXES = {
    ".md", ".txt", ".json", ".svg", ".html", ".css", ".js", ".py",
    ".yml", ".yaml", ".toml", ".xml", ".csv", ".sh", ".ps1", ".bat", ".cmd"
}
violations = []
for p in ROOT.rglob("*"):
    if not p.is_file():
        continue
    if ".git" in p.parts or "_site" in p.parts:
        continue
    if p.suffix.lower() not in TEXT_SUFFIXES:
        continue
    try:
        text = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue
    if FORBIDDEN in text.lower():
        violations.append(p.relative_to(ROOT).as_posix())

if violations:
    print("RETIRED_TERMINOLOGY_FOUND")
    for item in violations:
        print(item)
    sys.exit(2)

print("PASS_EXTRACORTICAL_TERMINOLOGY_NONREGRESSION")
