#!/bin/zsh
set -euo pipefail
cd "${0:A:h}"
if [[ ! -d /Applications/Xcode.app ]]; then
  open 'macappstore://itunes.apple.com/app/id497799835'
  print 'Install Xcode in the App Store, open it once to install iOS components, then run this file again.'
  exit 1
fi
export DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer
if ! command -v flutter >/dev/null 2>&1; then
  if [[ -x /opt/homebrew/bin/flutter ]]; then
    export PATH="/opt/homebrew/bin:$PATH"
  else
    print 'Flutter SDK is missing. Install Flutter, then run mobile/setup.sh.'
    exit 1
  fi
fi
if [[ ! -d ios/Runner.xcworkspace ]]; then
  ./setup.sh
fi
flutter pub get
flutter build ios --config-only --no-codesign
open ios/Runner.xcworkspace
print 'In Xcode: Runner > Signing & Capabilities > Automatically manage signing > select your Personal Team.'
print 'Connect and trust your iPhone, enable Developer Mode on it, select the iPhone target and press Run.'
