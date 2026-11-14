# Audio-only apnea research implementation

Spec: ../specs/2026-10-15-audio-only-apnea.md

- [ ] Add strict window-manifest validation and pure audio features; test missing clinical reference, alignment, person/night/recording leakage and partial windows.
- [ ] Add patient-weighted baseline training, validation-only threshold selection, held-out metrics, and portable NPZ/JSON model artifacts.
- [ ] Add explicit research inference with silent/short-window abstention and missing-artifact status; never reuse the snoring score as apnea risk.
- [ ] Expose trained/untrained research state in CLI/web results and document normalized data preparation.
- [ ] Run synthetic plumbing tests, serialization checks, all existing numerical/handler tests, and the original sample regression.
- [ ] Train/evaluate on a verified clinical subset when one is available. This is currently blocked by unavailable clinical training data; synthetic verification cannot satisfy it.

Ruling: Audio-only preference is confirmed by the user. Proceed with the local preparation tools; leave real-data training incomplete rather than fabricate results or require an unrelated questionnaire.
