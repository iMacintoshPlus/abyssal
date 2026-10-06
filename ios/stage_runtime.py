#!/usr/bin/env python3
"""Stage the project's pinned offline JAR importer into an iOS export copy."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from browser_runtime import SOURCES, stage_dependencies

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("project", type=Path, help="Disposable staged Godot project directory")
args = parser.parse_args()
destination = args.project.resolve() / "ios_importer"
destination.mkdir(parents=True, exist_ok=True)
# Use the same older WebAssembly-compatible Pyodide build as Android, allowing
# the project to retain iOS 14 as its minimum deployment version.
stage_dependencies(destination, ROOT / "android/dependencies.json")
browser_lock = json.loads((ROOT / "browser/dependencies.json").read_text())
amr = {"schema": 1, "files": [item for item in browser_lock["files"] if item["path"] in
       ("vendor/amrnb.js", "licenses/OpenCORE-AMR.txt", "licenses/OpenCORE-NOTICE.txt")]}
lock_path = destination / "amr-runtime-lock.json"
lock_path.write_text(json.dumps(amr))
stage_dependencies(destination, lock_path)
lock_path.unlink()
with zipfile.ZipFile(destination / 'sources.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
    for name, source in SOURCES.items():
        archive.writestr(name, (ROOT / source).read_bytes())
for name in ('LICENSE.md', 'THIRD_PARTY_NOTICES.md'):
    shutil.copyfile(ROOT / name, destination / name)
for source, name in [
    (ROOT / "browser/audio.js", "audio.js"),
    (ROOT / "android/import.js", "import.js"),
    (ROOT / "ios/runtime/bootstrap.js", "bootstrap.js"),
    (ROOT / "ios/runtime/index.html", "index.html"),
]:
    shutil.copyfile(source, destination / name)
print(f"Staged offline iOS importer at {destination}")
