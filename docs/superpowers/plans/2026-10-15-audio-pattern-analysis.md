# Sanor Audio Pattern Analysis Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task by task. Steps use checkbox syntax for tracking. Implement directly in the current session unless the user requests delegation.

**Goal:** Extend Sanor with useful audio timelines, quiet-gap detection, frequency measurements, rhythm analysis, and recording comparisons, without health conclusions.

**Architecture:** Keep the existing YAMNet and snoring classifier unchanged. Add deterministic audio measurements in a small Python module, expose additive fields through the existing analysis response, and extend the existing local web interface. Validate the web version before porting measurements to Flutter.

**Tech Stack:** Existing Python 3.12 environment, NumPy, SciPy, SoundFile, TensorFlow Lite, plain JavaScript/HTML/CSS, and Flutter/Dart for the later mobile phase. Use Python unittest for focused numerical tests.

**Spec:** The agreed scope in this conversation: describe audio patterns only; use recording duration, relative loudness, quiet gaps, frequency, and rhythm. The earlier `PLAN_AUDIO_ONLY.md` provides background, but its broader cough-counting and breathing roadmap is outside this implementation.

## Global constraints

- No health scores, disease classification, or health interpretations.
- Keep the current snoring threshold from `artifacts/mobile_metrics.json`.
- Snoring percentage uses recording duration.
- Loudness stays in dBFS; no conversion to calibrated dB SPL.
- A non-snoring window is not automatically a quiet window.
- Process recordings locally; do not add an external service.
- Preserve existing JSON fields and CSV columns; new fields are additive.
- Keep full-resolution results for calculations; aggregate only for display.
- The mobile source exists, but building and device validation remain outstanding.
- The workspace currently has no Git repository; commits are optional only after version control is explicitly set up.

## Current baseline

`predict.py` already prepares mono 16 kHz audio, runs inference per second, produces snoring events, and exports RMS/dBFS timelines. `compare.py` already compares normalized summaries. `web_server.py` exposes `POST /api/analyze` and loads timeline CSV rows, currently as strings. `web/app.js` already displays a simple snoring timeline and a comparison table. This plan extends those features rather than rebuilding them.

## Review focus

1. Entirely silent recordings must produce finite JSON or null values, never NaN or Infinity.
2. Final partial windows must retain their actual duration.
3. Speech or fan noise between snoring segments must not be labeled quiet solely because snoring stopped.
4. Long recordings must remain usable without a DOM element for every audio sample or window.
5. Separate 30-minute recording parts must not silently create false rhythm intervals or split-session totals.

## Delivery order

First release: Tasks 1–3, an improved web timeline with quiet-gap review.
Second release: Tasks 4–5, frequency/rhythm measurements and richer comparisons.
Third release: Task 6, mobile integration and device testing.

### Task 1: Establish the shared result contract

**Files:** Modify `predict.py`, `web_server.py`; create `tests/test_analysis_contract.py`.

**Interface:** Retain `summary`, `snore_events`, and `timeline`. Add top-level `audio_patterns` with `schema_version: 1`, `config`, `quiet_gaps`, `frequency_summary`, and `rhythm_summary`. Initially use an empty gap list and null summaries. Keep the command-line timeline CSV export. Add `--include-timeline` so the web server can request typed timeline rows directly in JSON instead of reparsing CSV strings.

- [ ] Add contract tests for existing fields, numeric timeline values, null optional values, and the partial final window.
- [ ] Run `python -m unittest discover -s tests -p 'test_analysis_contract.py' -v`; confirm the new contract tests fail before implementation.
- [ ] Implement the additive response structure and `--include-timeline`; update `analyze_bytes` to request it. Retain temporary input cleanup and existing error responses.
- [ ] Run the contract tests and analyze `test_snore_16k.wav` through both CLI and `analyze_bytes`. Assert equal summaries and event timestamps.
- [ ] Record the baseline summary for regression comparison; do not regenerate or train models.

**Done when:** The web and CLI expose identical analytical values, and all old fields remain available.

### Task 2: Add quiet-gap measurements

**Files:** Create `audio_patterns.py`, `tests/test_audio_patterns.py`; modify `predict.py`.

**Interface:** `detect_quiet_gaps(timeline: list[dict], snore_events: list[dict], quiet_threshold_dbfs: float = -45.0, min_gap_seconds: float = 10.0) -> list[dict]`. Each result contains `start_seconds`, `end_seconds`, and `duration_seconds`. Store the settings in `audio_patterns.config`.

**Algorithm:** Classify a window as quiet when its RMS is null because it is digital silence, or its finite RMS is at or below the configured threshold. Merge adjacent quiet windows. Return only runs at least the minimum duration that lie between detected snoring events. Leading/trailing quiet remains visible in the loudness timeline but is excluded from this between-event list. A loud non-snoring window breaks a quiet run. The default -45 dBFS is a configurable engineering starting point.

- [ ] Add synthetic timeline tests: exactly 10 seconds qualifies; 9.9 seconds does not; all silence yields no between-snore gap; loud speech breaks a run; partial windows use actual durations.
- [ ] Run `python -m unittest discover -s tests -p 'test_audio_patterns.py' -v`; confirm missing-function failures.
- [ ] Implement the pure function without importing TensorFlow. Validate finite thresholds and positive minimum duration, and reject invalid settings with clear errors.
- [ ] Add CLI options `--quiet-threshold-dbfs` and `--min-quiet-gap-seconds`; serialize the settings and returned gaps.
- [ ] Run the tests and manually listen to flagged intervals in a sample recording. Record false detections without changing the snoring classifier.

**Done when:** Quiet gaps are derived from measured audio level, with boundaries and reproducible settings.

### Task 3: Improve the web timeline and clip review

**Files:** Modify `web/app.js`, `web/index.html`, `web/style.css`.

**Consumes:** Typed `timeline`, `snore_events`, and `audio_patterns.quiet_gaps` from Tasks 1–2.

**Produces:** Aligned snoring and RMS/dBFS tracks, a quiet-gap list, elapsed-time labels, and click-to-seek playback for available source audio.

- [ ] Keep a local object URL for each selected WAV. For recorder parts, associate the Blob with its analysis result. Release URLs when their results are removed.
- [ ] Draw bounded-resolution tracks using canvas or SVG. Snoring bins preserve brief events using any positive window; loudness bins retain min/max levels and do not turn null into zero dBFS.
- [ ] Make an event or gap selection seek an audio player to the selected start time. Provide keyboard-operable controls and textual start/end/duration values.
- [ ] Show long gaps as “Quiet gap” and loudness as “Relative level (dBFS).” Keep existing Thai UI language consistent.
- [ ] Check a short file, a silent file, and synthetic eight-hour results. Verify that short events remain visible, timestamps align, and rendering uses bounded element counts.
- [ ] Check selecting two files, switching results, and replaying recorded parts. Confirm each result plays its associated audio.

**Done when:** Users can locate and listen to detected snoring segments and quiet gaps from the timeline.

### Task 4: Add frequency and rhythm measurements

**Files:** Extend `audio_patterns.py`, `tests/test_audio_patterns.py`, `predict.py`, `web/app.js`.

**Interfaces:**

- `spectral_features(frame: np.ndarray, sample_rate: int) -> dict`: returns `dominant_frequency_hz` and `spectral_centroid_hz`, both nullable.
- `summarize_rhythm(snore_events: list[dict]) -> dict`: returns `interval_count`, `mean_start_interval_seconds`, `std_start_interval_seconds`, and `interval_cv`, with unavailable measurements null.

**Algorithm:** For frequency, subtract the mean, apply a Hann window, and use an rFFT. Ignore the DC bin; return null for zero-energy or insufficient-length frames. Compute the centroid from magnitude weights. Compute features only for snoring-positive windows and aggregate their medians. Call these spectral measurements, not fundamental pitch. For rhythm, use consecutive snoring-segment start intervals; require at least three segments for variation metrics and document population standard deviation.

- [ ] Add tests with 200 Hz and 800 Hz generated tones, all-zero samples, a DC signal, and short frames. Frequency estimates should be within one FFT-bin width.
- [ ] Add rhythm tests: starts at 0, 5, 10, 15 seconds yield mean 5, standard deviation 0, and CV 0; fewer than three segments yield null variation metrics.
- [ ] Run the focused tests before implementation, implement both functions, then rerun.
- [ ] Add per-window spectral fields to CSV and optional JSON timelines; populate the frequency and rhythm summaries. Preserve partial-window duration and existing snoring values.
- [ ] Show summaries with units and “Not enough segments” for unavailable rhythm metrics. Do not assign good/bad categories.
- [ ] Measure processing time on the same WAV with and without spectral features, and record overhead before enabling them by default.

**Done when:** Reproducible frequency and segment-spacing measurements appear with clear definitions.

### Task 5: Extend recording comparisons and exports

**Files:** Modify `compare.py`, `web/app.js`, `web/index.html`; create `tests/test_comparison.py`; update `README.md`.

**Interface:** Add nullable frequency/rhythm fields and quiet-gap counts to comparison rows. Preserve existing per-hour snoring measures. Treat imported files as separate recordings by default. Recorder-generated parts may share a session identifier and sequence number.

- [ ] Test unequal recording durations, null levels, missing optional fields, and reordered inputs. Verify existing normalized measures stay unchanged.
- [ ] Add raw-value comparison columns and user-selected baseline differences; report missing values as unavailable, never zero.
- [ ] Add JSON/CSV download controls for summaries and timeline data without including audio in those exports.
- [ ] For grouped recorder parts, calculate total snoring percentage from summed durations. Merge boundary snoring segments only when sequence and continuity are confirmed; exclude unknown joins from rhythm calculations.
- [ ] Test a snoring segment spanning two contiguous parts and a session with a missing part. Do not average percentages or per-part medians to manufacture session statistics.
- [ ] Run `python -m unittest discover -s tests -v` and the existing CLI sample commands. Document the fields, defaults, units, and grouping rules.

**Done when:** Different-length recordings can be compared and exported, and grouped recorder sessions respect boundaries.

### Task 6: Port validated features to Flutter

**Files:** Modify `mobile/lib/inference.dart`, `mobile/lib/main.dart`; create `mobile/lib/audio_patterns.dart`, `mobile/test/audio_patterns_test.dart`; update `mobile/README.md`.

**Dependency:** Complete Tasks 1–5 first. Flutter SDK installation and physical target devices are prerequisites for mobile validation; report any unavailable environment explicitly.

- [ ] Export small synthetic parity fixtures covering silence, threshold boundaries, partial windows, quiet gaps, tones, and event intervals from the Python implementation.
- [ ] Implement quiet-gap and rhythm measurements in Dart using the same definitions and result fields. Port frequency measurements after selecting an FFT implementation and checking its dependency/license footprint.
- [ ] Test exact event/gap boundaries within 0.001 seconds, dBFS within 0.1 dB, and frequency within one FFT-bin width against Python fixtures. Record model probability differences separately.
- [ ] Add the timeline, summary, local playback, and comparison UI using the verified data contract.
- [ ] Run `flutter analyze` and `flutter test`; build and test on Android and iOS targets that are actually available.
- [ ] Test microphone denial, interruptions, lock-screen operation, final segment saving, and long-session resource usage. Record supported behavior per device rather than assuming background recording works.

**Done when:** Built mobile versions reproduce the Python measurements and their recording behavior is documented from real-device tests.

## Completion checks

- [ ] Existing sample snoring results remain unchanged.
- [ ] Numerical tests pass for silence, partial windows, spectral features, gaps, and rhythm.
- [ ] Web timeline and playback work with imported files and recorder parts.
- [ ] Long-result display remains responsive.
- [ ] Exports retain settings and units needed to reproduce measurements.
- [ ] Documentation clearly distinguishes implemented features from untested mobile behavior.

## Deferred work

Model retraining, cough event counting, OSA labels, calibrated sound pressure, sleep-stage estimation, accounts, cloud storage, and external uploads are not required for this plan.
