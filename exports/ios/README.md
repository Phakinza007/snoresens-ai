# Snoresens AI iPhone — 0.2.0 (build 2)

Native arm64 / iOS 15+ release from source `d64c1419c9c9450eb748be02f5144b281345e922`, tagged `snore-ios-v0.2.0`. Built with Xcode 27.1, without signing.

- [Successful GitHub Actions build](https://github.com/Phakinza007/snoresens-ai/actions/runs/43886713217) — analyzer clean, 31 tests passed, native build and archive checks passed.
- Artifact `SnoresensAI-iOS-unsigned` contains the IPA and verification JSON (7-day retention).
- Local installer: `exports/ios/Snoresens-AI-unsigned.ipa` and frozen copy `exports/ios/versions/Snoresens-AI-0.2.0-unsigned.ipa`. Binaries are ignored by Git.
- IPA SHA256: `91da49ff5332c9211517ff014d0f75a34544c41f96479f56289e8abde39495d1`.
- Local verification matches the CI verification exactly: app 0.2.0+2, microphone description, `UIBackgroundModes: audio`, Files integration, both model hashes identical to the original v2 app. See [archive verification](../../results/native-ios/unsigned-build-checks.json) and [feature checks](../../results/native-ios/feature-checks.json).
- Install by signing with your own account through [AltStore Classic](../../mobile/ALTSTORE_INSTALL_TH.md) or Xcode. Installing the new IPA is required to get the new features on the phone.

[Release notes and device test steps](../../mobile/RELEASE_0.2.0_TH.md): pause/resume recording, durable history/audio, five-minute analysis parts with resume and a weighted recording summary, playback and JSON/CSV export. The v2 classification model is unchanged.

The app is configured for background recording, but lock-screen microphone capture, interruptions, export and overnight operation still need testing on a physical iPhone. CI and widget tests do not establish those device results. The archive is unsigned and contains no provisioning profile or Apple Account.

## Previous version

Version 0.1.0+1 is preserved as tag `snore-ios-v0.1.0` at `b798350ef039a333bafcb03be0f01a649513e1d9`. Local original IPA: `exports/ios/versions/Snoresens-AI-0.1.0-unsigned.ipa`, SHA256 `0d337f1f5a2766ac9c3ea8ebae2f441160051cdd4e3816101680ae7b7fe10692`. Its proof is frozen in [results/native-ios/0.1.0](../../results/native-ios/0.1.0/). That app has memory-only history and no background audio capability.
