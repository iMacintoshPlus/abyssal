#!/usr/bin/env python3
"""Build the iOS picker/import bridge for Godot 4.7.2 device and simulator."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import ast

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = "ed1daf0bf001b61586d9930840f2f1394092c079"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--godot-source", type=Path, required=True)
parser.add_argument("--scons", default="scons")
args = parser.parse_args()
source = args.godot_source.resolve()
env = dict(os.environ)
env.setdefault("DEVELOPER_DIR", "/Applications/Xcode.app/Contents/Developer")
version_file = source / "version.py"
try:
    version = ast.parse(version_file.read_text())
    values = {node.targets[0].id: ast.literal_eval(node.value) for node in version.body
              if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)}
except (OSError, SyntaxError, ValueError):
    values = {}
if (values.get("major"), values.get("minor"), values.get("patch"), values.get("status")) != (4, 7, 2, "stable"):
    raise SystemExit("Use Godot 4.7.2-stable sources matching the installed export templates.")
if (source / ".git").exists():
    try:
        revision = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except subprocess.CalledProcessError:
        revision = ""
    if revision and revision != EXPECTED:
        raise SystemExit("The Godot source checkout does not match the official 4.7.2-stable revision.")

def run(command, **kwargs):
    subprocess.run([str(item) for item in command], env=env, check=True, **kwargs)

run([args.scons, "platform=ios", "target=template_release", "arch=arm64",
     "core/disabled_classes.gen.h", "core/version_generated.gen.h",
     "core/extension/gdextension_interface.gen.h"], cwd=source)

build = ROOT / "ios/build/plugin"
build.mkdir(parents=True, exist_ok=True)
for target in ("debug", "release"):
    libraries = []
    for sdk_name, triple in [
        ("iphoneos", "arm64-apple-ios14.0"),
        ("iphonesimulator", "arm64-apple-ios14.0-simulator"),
    ]:
        sdk = subprocess.check_output(["xcrun", "--sdk", sdk_name, "--show-sdk-path"], env=env, text=True).strip()
        obj = build / f"abyssal_importer.{target}.{sdk_name}.o"
        library = build / f"AbyssalIOSImporter.{target}.{sdk_name}.a"
        command = ["xcrun", "--sdk", sdk_name, "clang++", "-c", ROOT / "ios/native/abyssal_importer.mm",
                   "-o", obj, "-I" + str(source), "-I" + str(source / "platform/ios"),
                   "-std=c++17", "-target", triple, "-isysroot", sdk, "-fobjc-arc", "-fblocks",
                   "-DIOS_ENABLED", "-DAPPLE_EMBEDDED_ENABLED", "-DUNIX_ENABLED", "-DTHREADS_ENABLED", "-DNDEBUG", "-O2"]
        if target == "debug": command.append("-DDEBUG_ENABLED")
        if sdk_name == "iphonesimulator": command.append("-DIOS_SIMULATOR")
        run(command)
        run(["xcrun", "libtool", "-static", "-o", library, obj])
        libraries.extend(["-library", library])
    framework = build / f"AbyssalIOSImporter.{target}.xcframework"
    if framework.exists(): shutil.rmtree(framework)
    run(["xcodebuild", "-create-xcframework", *libraries, "-output", framework])
print("Built device and Apple Silicon simulator importer frameworks.")
