# Sleep audio TDD evidence

Date: 2026-10-16. Journeys were derived from the request to add multiple sound categories and experimental breathing estimates. This folder is not a Git checkout, so checkpoint commits were not applicable.

| Behavior | RED evidence | GREEN evidence |
| --- | --- | --- |
| Review segments and gated rate estimates | `test_sleep_audio.py` executed and failed because the new `sleep_audio` module was missing | Six tests passed after implementation |
| Inference output integration | `test_analysis_contract.py` executed and failed with missing `sound_review` | Both contract tests passed after connecting outputs |
| Browser calculation helpers | `node tests/test_sleep_audio_web.cjs` executed and failed because `soundReviewEntries` was absent | Same target passed after helpers were implemented |

The final Python suite passed 47 tests. Existing Node measurement/chart checks and the new sleep-audio UI checks passed. Python standard-library `trace` reported 87% executable-line coverage of `sleep_audio.py` (156 lines); this is not branch coverage or full-project coverage. Numerical tests cover known 15-cycle/minute modulation, partial final windows, silence, constant tones, noise, clipping, missing model evidence and interfering classes. These are software checks, not clinical validation.

End-to-end: uploaded `test_snore_16k.wav` through the existing localhost server in Chrome. Analysis completed, four sound tracks and category filtering appeared, and the breathing detail panel showed explicit abstention reasons. Snore duration remained 131 seconds from 150.435 recorded seconds. Breathing-like review totaled 49 seconds; no window qualified for a rate estimate. The UI correctly showed unavailable median and 0% coverage. This single recording does not measure sound-classification accuracy.

Limitations: raw Speech/Breathing thresholds are not bedside-calibrated; no own bruxism, movement or sleep-talking classifier was trained. The breathing plot's numerical estimates are tested using generated signals, while real-person reference comparison remains pending.
