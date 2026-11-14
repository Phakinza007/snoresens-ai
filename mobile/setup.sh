#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if ! command -v flutter >/dev/null 2>&1; then
  echo 'Flutter SDK not found. Install Flutter from https://docs.flutter.dev/install first.' >&2
  exit 1
fi
flutter create --platforms="${SANOR_PLATFORMS:-ios}" --org com.phakinza --project-name sanor_mobile --empty --no-pub .
mkdir -p assets
cp ../artifacts/yamnet_base.tflite assets/
cp ../artifacts/snore_v2/snore_score_head.tflite assets/
cp ../artifacts/snore_v2/metrics.json assets/mobile_metrics.json
python3 - <<'PY'
from pathlib import Path
manifest = Path('android/app/src/main/AndroidManifest.xml')
permission = '<uses-permission android:name="android.permission.RECORD_AUDIO" />'
if manifest.exists():
    text = manifest.read_text()
else:
    text = permission
if manifest.exists() and permission not in text:
    text = text.replace('<application', permission + '\n    <application', 1)
    manifest.write_text(text)
plist = Path('ios/Runner/Info.plist')
if plist.exists():
    import plistlib
    config = plistlib.loads(plist.read_bytes())
    config['NSMicrophoneUsageDescription'] = 'ใช้ไมโครโฟนเพื่อบันทึกและวิเคราะห์เสียงกรนบนอุปกรณ์ของคุณ'
    config['CFBundleDisplayName'] = 'Snoresens AI'
    plist.write_bytes(plistlib.dumps(config,sort_keys=False))
project = Path('ios/Runner.xcodeproj/project.pbxproj')
if project.exists():
    text = project.read_text()
    if 'STRIP_STYLE' not in text:
        text = text.replace('SWIFT_VERSION = 5.0;', 'SWIFT_VERSION = 5.0;\n\t\t\t\tSTRIP_STYLE = \"non-global\";')
        project.write_text(text)
PY
flutter pub get
echo 'Source ready. Run flutter analyze and flutter test, then open ios/Runner.xcworkspace to select your Personal Team and iPhone.'
