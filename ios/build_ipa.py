#!/usr/bin/env python3
"""Export an isolated Xcode project and package an unsigned device IPA."""
import argparse
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--godot', type=Path, required=True)
parser.add_argument('--template', type=Path, required=True)
parser.add_argument('--output', type=Path, default=ROOT / 'ios/build/dist/Abyssal-iOS-unsigned.ipa')
args = parser.parse_args()
env = dict(os.environ)
env.setdefault('DEVELOPER_DIR', '/Applications/Xcode.app/Contents/Developer')
env.setdefault('ABYSSAL_CACHE_HOME', str(ROOT / 'ios/build/cache'))

def run(command, **kwargs):
    subprocess.run([str(item) for item in command], env=env, check=True, **kwargs)

build = ROOT / 'ios/build/ci-export'
run(['python3', ROOT / 'ios/build_ios.py', '--godot', args.godot,
     '--template', args.template, '--output', build])
app_info = build / 'Abyssal/Abyssal-Info.plist'
info = plistlib.loads(app_info.read_bytes())
info['CFBundleName'] = 'Abyssal'
info['CFBundleDisplayName'] = 'Abyssal'
if env.get('GITHUB_RUN_NUMBER'):
    info['CFBundleVersion'] = env['GITHUB_RUN_NUMBER']
app_info.write_bytes(plistlib.dumps(info, sort_keys=False))
for localized in (build / 'Abyssal').glob('*.lproj/InfoPlist.strings'):
    localized.write_text('"CFBundleDisplayName" = "Abyssal";\n')
run(['xcodebuild', '-project', build / 'Abyssal.xcodeproj', '-scheme', 'Abyssal',
     '-configuration', 'Release', '-sdk', 'iphoneos', '-destination', 'generic/platform=iOS',
     '-derivedDataPath', build / 'DerivedData', 'CODE_SIGNING_ALLOWED=NO',
     'CODE_SIGNING_REQUIRED=NO', 'CODE_SIGN_IDENTITY=', 'DEVELOPMENT_TEAM=', 'build'])
app = build / 'DerivedData/Build/Products/Release-iphoneos/Abyssal.app'
if not app.is_dir():
    raise SystemExit('Xcode did not produce Abyssal.app')
package = build / 'package/Payload'
package.mkdir(parents=True)
shutil.copytree(app, package / app.name, symlinks=True)
output = args.output.resolve()
output.parent.mkdir(parents=True, exist_ok=True)
if output.exists(): output.unlink()
run(['ditto', '-c', '-k', '--keepParent', 'Payload', output], cwd=package.parent)
with zipfile.ZipFile(output) as archive:
    info = plistlib.loads(archive.read('Payload/Abyssal.app/Info.plist'))
    assert info['CFBundleIdentifier'] == 'com.imacintoshplus.abyssal'
    assert info['CFBundleDisplayName'] == 'Abyssal'
    assert info['MinimumOSVersion'] == '14.0'
    if any(name.endswith(('.jar', '.abyss', 'embedded.mobileprovision')) or
           '/_CodeSignature/' in name for name in archive.namelist()):
        raise SystemExit('Unexpected original game content or signing data in IPA')
print(f'Unsigned IPA ready: {output}')
