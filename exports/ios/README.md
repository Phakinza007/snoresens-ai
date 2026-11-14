# Snoresens AI iPhone build

Native arm64 / iOS 15+ release built without signing from source commit `b798350ef039a333bafcb03be0f01a649513e1d9`.

- [Successful GitHub Actions build](https://github.com/Phakinza007/snoresens-ai/actions/runs/43606730787)
- Artifact: `SnoresensAI-iOS-unsigned` (7-day retention). Download and extract the artifact ZIP to get `Snoresens-AI-unsigned.ipa`.
- Local prepared IPA: `exports/ios/Snoresens-AI-unsigned.ipa`. The binary is ignored by Git; source and build instructions are tracked.
- IPA SHA256: `0d337f1f5a2766ac9c3ea8ebae2f441160051cdd4e3816101680ae7b7fe10692`.
- Both model hashes and microphone permission description checked. See [verification](../../results/native-ios/unsigned-build-checks.json).
- The archive is unsigned, with no provisioning profile or Apple Account. Install by signing it with your account through [AltStore Classic](../../mobile/ALTSTORE_INSTALL_TH.md), or build/sign from Xcode.
- Physical-device inference, microphone behavior and background recording have not been verified.
