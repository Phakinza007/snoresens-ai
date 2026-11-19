# Snoresens AI iPhone — 0.3.0 (build 3)

Native arm64 / iOS 15+ release from source `4de7482b58c1e60a2b6daabd10d3814e2d4cb46f`, tagged `snore-ios-v0.3.0`. Built with Xcode 27.1, without signing.

- [Successful GitHub Actions build](https://github.com/Phakinza007/snoresens-ai/actions/runs/44467062193) — analyzer clean, 37 tests passed, native build and archive checks passed.
- Artifact `SnoresensAI-iOS-unsigned` contains the IPA and verification JSON (7-day retention).
- Local installer: `exports/ios/Snoresens-AI-unsigned.ipa` and frozen copy `exports/ios/versions/Snoresens-AI-0.3.0-unsigned.ipa`. Binaries are ignored by Git.
- IPA SHA256: `0bd540393a3c2aeecbc01ae246364a2835037e24a8afeab4307de8256a20762f`.
- Local verification matches the CI verification exactly: app 0.3.0+3, microphone description, `UIBackgroundModes: audio`, Files integration, web UI assets (`thai.ttf`, Lucide SVGs, `sample.wav`), and both model hashes identical to the original v2 app. See [archive verification](../../results/native-ios/unsigned-build-checks.json), [feature checks](../../results/native-ios/feature-checks.json), and [web UI checks](../../results/native-ios/web-ui-checks.json).
- Install by signing with your own Apple Account over the existing app through [AltServer / AltStore Classic](../../mobile/ALTSTORE_INSTALL_TH.md) or Xcode to preserve stored recordings and preferences.

[Release notes for 0.3.0](../../mobile/RELEASE_0.3.0_TH.md): web-matched Snoresens interface, four bottom tabs, guided preparation/consent, dark recording screen, 20 ms zoomed report, morning checklist, and profile/data management, while preserving native background recording, durable Documents storage, five-minute analysis parts with resume, and the frozen v2 model.

The app is configured for background recording, but lock-screen microphone capture, interruptions, export, and overnight operation still need testing on a physical iPhone (see [0.2.0 device test steps](../../mobile/RELEASE_0.2.0_TH.md)). CI and widget tests do not establish those device results or user visual acceptance. The archive is unsigned and contains no provisioning profile or Apple Account.

## Previous versions

- Version 0.2.0+2 is preserved as tag `snore-ios-v0.2.0` at `d64c1419c9c9450eb748be02f5144b281345e922` ([build 43886713217](https://github.com/Phakinza007/snoresens-ai/actions/runs/43886713217)). Local IPA: `exports/ios/versions/Snoresens-AI-0.2.0-unsigned.ipa`, SHA256 `91da49ff5332c9211517ff014d0f75a34544c41f96479f56289e8abde39495d1`. Its proof is frozen in [results/native-ios/0.2.0](../../results/native-ios/0.2.0/).
- Version 0.1.0+1 is preserved as tag `snore-ios-v0.1.0` at `b798350ef039a333bafcb03be0f01a649513e1d9`. Local original IPA: `exports/ios/versions/Snoresens-AI-0.1.0-unsigned.ipa`, SHA256 `0d337f1f5a2766ac9c3ea8ebae2f441160051cdd4e3816101680ae7b7fe10692`. Its proof is frozen in [results/native-ios/0.1.0](../../results/native-ios/0.1.0/). That app has memory-only history and no background audio capability.
