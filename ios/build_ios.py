#!/usr/bin/env python3
"""Create an Xcode project from a disposable copy of the upstream Godot game."""
import argparse
import os
import plistlib
from pathlib import Path
import re
import shutil
import subprocess
from patch_game import apply as patch_game

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_GODOT = "4.7.2.stable.official.ed1daf0bf"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--godot", type=Path, default=Path("/Applications/Godot.app/Contents/MacOS/Godot"))
parser.add_argument("--template", type=Path, required=True, help="Official matching ios.zip from Godot export templates")
parser.add_argument("--output", type=Path, default=ROOT / "ios/build/export")
parser.add_argument("--version", help="Release version; defaults to this checkout's upstream validation document")
parser.add_argument("--simulator-library", type=Path,
                    help="Optional arm64 simulator libgodot.a built from matching Godot sources")
args = parser.parse_args()
release_match = re.search(r'^# Abyssal Engine ([0-9]+\.[0-9]+\.[0-9]+)\b',
                          (ROOT / "public/VALIDATION.md").read_text(), re.MULTILINE)
release_version = args.version or (release_match.group(1) if release_match else None)
if not release_version or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', release_version):
    raise SystemExit("Cannot determine a numeric release version; supply --version X.Y.Z.")
godot = args.godot.resolve()
template = args.template.resolve()
version = subprocess.check_output([str(godot), "--version"], text=True).strip()
if version != EXPECTED_GODOT:
    raise SystemExit(f"Expected {EXPECTED_GODOT}; found {version}.")
if not template.is_file(): raise SystemExit(f"iOS export template not found: {template}")
for kind in ("debug", "release"):
    if not (ROOT / f"ios/build/plugin/AbyssalIOSImporter.{kind}.xcframework").is_dir():
        raise SystemExit("Build the iOS plugin first with ios/build_plugin.py.")

build = args.output.resolve()
if build.exists(): shutil.rmtree(build)
stage = build / "game"
shutil.copytree(ROOT / "game", stage, ignore=shutil.ignore_patterns(".godot", ".DS_Store", "*.uid"))
patch_game(stage)
project_file = stage / "project.godot"
project_text = project_file.read_text()
project_text = re.sub(r'^config/name=.*$', 'config/name="Abyssal"', project_text, flags=re.MULTILINE)
project_text = re.sub(r'^config/version=.*\n?', '', project_text, flags=re.MULTILINE)
project_text = project_text.replace('[application]\n', f'[application]\nconfig/version="{release_version}"\n', 1)
project_text = re.sub(r'^window/handheld/orientation=.*\n?', '', project_text, flags=re.MULTILINE)
project_text = project_text.replace("[display]\n", '[autoload]\n\nAbyssalIOSPlatform="*res://ios/platform.gd"\n\n[display]\n', 1)
project_text = project_text.replace('[display]\n', '[display]\nwindow/handheld/orientation=4\n', 1)
project_text = project_text.replace("[rendering]\n", "[rendering]\ntextures/vram_compression/import_etc2_astc=true\n", 1)
project_file.write_text(project_text)
template_path = str(template).replace("\\", "\\\\").replace('"', '\\"')
preset = (ROOT / "ios/export_presets.cfg").read_text()
preset = preset.replace('custom_template/debug=""', 'custom_template/debug="' + template_path + '"')
preset = preset.replace('custom_template/release=""', 'custom_template/release="' + template_path + '"')
(stage / "export_presets.cfg").write_text(preset)
plugin = stage / "ios/plugins/AbyssalIOSImporter"
plugin.mkdir(parents=True)
shutil.copyfile(ROOT / "ios/runtime/platform.gd", stage / "ios/platform.gd")
shutil.copyfile(ROOT / "ios/runtime/abyssal_ios_importer.gdip", plugin / "AbyssalIOSImporter.gdip")
for kind in ("debug", "release"):
    name = f"AbyssalIOSImporter.{kind}.xcframework"
    shutil.copytree(ROOT / "ios/build/plugin" / name, plugin / name)
subprocess.run(["python3", str(ROOT / "ios/stage_runtime.py"), str(stage)], check=True)

# Keep generated plugin/runtime files and export settings out of the developer's checkout.
env = dict(os.environ)
env.setdefault("DEVELOPER_DIR", "/Applications/Xcode.app/Contents/Developer")
subprocess.run([str(godot), "--headless", "--path", str(stage), "--editor", "--import"], env=env, check=True)
export_path = build / "Abyssal.ipa"
subprocess.run([str(godot), "--headless", "--path", str(stage), "--export-release", "iOS", str(export_path)], env=env, check=True)

# A project-only export writes an Xcode project directory at the chosen path.
projects = list(build.rglob("*.xcodeproj"))
if not projects:
    raise SystemExit(f"Godot export completed without an Xcode project. Inspect {build} for diagnostics.")
# Godot emits empty privacy descriptions even when these permissions are unused.
# Keep any future non-empty descriptions, but remove invalid empty entries.
info_path = projects[0].parent / "Abyssal/Abyssal-Info.plist"
info = plistlib.loads(info_path.read_bytes())
for key in ("NSCameraUsageDescription", "NSMicrophoneUsageDescription", "NSPhotoLibraryUsageDescription"):
    if key in info and not str(info[key]).strip():
        del info[key]
info_path.write_bytes(plistlib.dumps(info, sort_keys=False))
project_file = projects[0] / "project.pbxproj"
project_text = project_file.read_text()
# Godot's generated framework phase places libgodot before statically linked
# plugins. Put our plugin first so its references to Godot symbols are visible
# when the engine archive is scanned by Apple's linker.
framework_phase = re.search(
    r"(PBXFrameworksBuildPhase section \*/.*?files = \()(.*?)(\);)",
    project_text,
    flags=re.DOTALL,
)
if not framework_phase:
    raise SystemExit("Could not find Xcode's framework link phase.")
files = framework_phase.group(2)
plugin_id = "589384010000000000000001"
engine_id = re.search(r"([A-F0-9]{24}) /\* Abyssal\.xcframework \*/", files)
if not engine_id:
    raise SystemExit("Could not find the Godot engine framework in Xcode's link phase.")
plugin_entry = re.search(rf"^\s*{plugin_id},?\s*$", files, flags=re.MULTILINE)
engine_entry = re.search(rf"^\s*{engine_id.group(1)} /\* Abyssal\.xcframework \*/,?\s*$", files, flags=re.MULTILINE)
if plugin_entry and engine_entry and plugin_entry.start() > engine_entry.start():
    plugin_line = plugin_entry.group(0)
    engine_line = engine_entry.group(0)
    files = files[:engine_entry.start()] + plugin_line + "\n" + engine_line + files[plugin_entry.end():]
    project_text = project_text[:framework_phase.start(2)] + files + project_text[framework_phase.end(2):]
# Godot's iOS template links MoltenVK even for the Compatibility renderer.
project_text = project_text.replace(
    " -ObjC\";",
    " -ObjC -framework Metal -framework QuartzCore -framework IOSurface\";",
)
project_file.write_text(project_text)

# Godot's downloadable iOS template currently ships an x86_64-only simulator
# archive in a slice marked for both x86_64 and arm64. Apple Silicon Xcode then
# ignores the engine objects and reports hundreds of unresolved symbols. A
# matching local SCons build can replace that simulator slice for local runs.
if args.simulator_library:
    simulator_library = args.simulator_library.resolve()
    if not simulator_library.is_file():
        raise SystemExit(f"Simulator library not found: {simulator_library}")
    architectures = subprocess.check_output(
        ["xcrun", "lipo", "-archs", str(simulator_library)], text=True
    ).split()
    if architectures != ["arm64"]:
        raise SystemExit("The simulator override must contain only arm64 code.")
    engine_framework = projects[0].parent / "Abyssal.xcframework"
    simulator_slice = engine_framework / "ios-arm64_x86_64-simulator"
    shutil.copyfile(simulator_library, simulator_slice / "libgodot.a")
    info_path = engine_framework / "Info.plist"
    info = plistlib.loads(info_path.read_bytes())
    for item in info["AvailableLibraries"]:
        if item.get("SupportedPlatformVariant") == "simulator":
            item["SupportedArchitectures"] = ["arm64"]
    info_path.write_bytes(plistlib.dumps(info, sort_keys=False))
print(f"Xcode project ready: {projects[0]}")
