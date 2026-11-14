#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if ! command -v flutter >/dev/null 2>&1; then
  echo 'Flutter SDK not found. Install Flutter from https://docs.flutter.dev/install first.' >&2
  exit 1
fi
flutter create --platforms=android,ios --project-name sanor_mobile .
mkdir -p assets
cp ../artifacts/yamnet_base.tflite ../artifacts/snore_score_head.tflite ../artifacts/mobile_metrics.json assets/
python3 - <<'PY'
from pathlib import Path
manifest = Path('android/app/src/main/AndroidManifest.xml')
text = manifest.read_text()
permission = '<uses-permission android:name="android.permission.RECORD_AUDIO" />'
if permission not in text:
    text = text.replace('<application', permission + '\n    <application', 1)
    manifest.write_text(text)
plist = Path('ios/Runner/Info.plist')
text = plist.read_text()
if 'NSMicrophoneUsageDescription' not in text:
    text = text.replace('</dict>', '<key>NSMicrophoneUsageDescription</key>\n<string>ใช้ไมโครโฟนเพื่อวิเคราะห์เสียงกรนบนเครื่อง</string>\n</dict>', 1)
    plist.write_text(text)
PY
flutter pub get
echo 'Ready. Connect a phone and run: flutter run'
