# Sanor audio pattern analysis

## Snore duration score in the web interface

The web now shows a descriptive 0–100 snoring score: `100 * (1 - detected_snore_seconds / recording_seconds)`, rounded to one decimal. Higher means less recorded time classified as snoring. This is a presentation of the same duration ratio, not an independent measurement, sleep-quality score, or medical-risk estimate. No good/bad or OSA severity label is assigned. Missing, nonfinite, zero-duration, or inconsistent durations produce null rather than a score. A score of 100 means no snoring was detected in that recording; it does not establish good recording quality or healthy sleep.

The score appears in the comparison table and recording detail. Web JSON exports add a versioned `audio_scores.snore_duration` object with the formula and interpretation; comparison CSV adds `snore_duration_score` and its maximum. Python and Flutter outputs have not been changed for this score. Verify with `node tests/test_snore_score.cjs`.

## Experimental sound review and breathing estimates

The Python/web version now includes `sound_review` and `breathing_rate` outputs. See [the Thai project review](docs/SANOR_PROJECT_REVIEW_TH.md) for scope, model results and architecture.

`sound_review` merges adjacent windows separately for snore, cough, speech and breathing-like audio; categories may overlap. Cough uses the existing trained head's configured threshold, or raw YAMNet Cough scores when the head is absent. Speech (official YAMNet index 0) and Breathing (index 36) use an experimental 0.5 review threshold. Digital silence and levels below -60 dBFS are not flagged. Segment counts are review groups, not cough or breath counts; speech does not establish sleep talking or speaker identity. Bruxism and movement are not supported classifiers.

`breathing_rate` analyzes independent 30-second windows. It checks clipping and signal level, requires breathing-like score coverage at least 50%, and rejects excessive speech/cough or snoring. A band-limited roughly 10 Hz RMS envelope supplies autocorrelation peaks within 6–30 cycles/minute, cross-checked against envelope peak intervals. Correlation >= 0.65 and interval CV <= 0.25 are engineering defaults, not clinical thresholds. Nonqualifying and partial windows retain null rate plus an explicit reason. Summaries include median estimated rate and duration coverage. This is an experimental envelope-cycle estimator, not validated respiratory rate: recurring machinery or double-peaked breathing may fool it. No apnea counts or medical interpretation are produced.

The web exposes four sound tracks, a type filter in the playback list, a breathing plot when estimates exist, paginated window statuses, and breathing-window CSV export. Older results remain viewable and state when new analysis data is absent. The existing eight-hour fixture does not contain measured breathing estimates. Each file is independent; session aggregation does not combine these new results across joins. These features have not been ported to Flutter.

Verification: `python -m unittest discover -s tests -v`, `node tests/test_sleep_audio_web.cjs`, and existing chart/measurement Node checks. Synthetic modulation at 15 cycles/minute checks estimator arithmetic and abstention; it is not human validation. A real sample upload through the running local server showed 131 snore seconds and 49 seconds of overlapping breathing-like review windows; no 30-second window qualified for a breathing estimate, correctly producing null median and zero coverage.

The local web and Python tools now provide snoring segments, relative loudness, quiet gaps, frequency measurements, and segment-spacing statistics. The existing model and snoring threshold are unchanged.

## Use the web interface

Run from the project directory:

```bash
.venv/bin/python web_server.py
```

Open `http://127.0.0.1:8765`. Select WAV recordings or use the existing recorder. Expand the quiet-gap settings before analysis to change the level threshold and minimum duration. Recordings take a snapshot of these settings when the session starts.

Select a file name in the comparison table to see its summary, aligned audio tracks, and event list. Select an event or move the time slider to seek the audio player, then press Play to listen. Event lists are paginated and tracks use at most 700 display bins; the exported results retain every original analysis window. Bins preserve brief snoring detections and minimum/maximum loudness instead of majority-voting events away.

Use the reference-file selector to compare snoring percentage and relative loudness against a chosen file. Percentage differences are percentage points. A dash means the measurement is unavailable. Compare levels using the same device, microphone settings, and placement.

Download the comparison CSV, all results JSON, or an individual recording's timeline CSV and JSON. Audio is not embedded in these downloads. Results and playback references stay in this browser tab until removed or the page is reloaded; there is no persistent recording-history database. Removing a result releases its playback reference without deleting the original audio file.

The WAV limit remains 200 MB per file. The recorder divides long sessions into 30-minute WAV parts. Session summaries sum recorded duration and snoring duration, rather than averaging file percentages. Because MediaRecorder restarts can introduce an unmeasured gap, recorder parts currently mark joins as unconfirmed. Session calculations never merge segments or compute rhythm intervals across those joins. Session time means recorded time and excludes unrecorded interruptions. Imported WAV files remain independent recordings.

## Measurement definitions

| Measurement | Definition |
| --- | --- |
| Snoring percentage | Detected snoring seconds / recorded seconds × 100 |
| Snoring segments | Adjacent one-second windows classified as snoring, with the final partial window counted at its actual duration |
| Relative loudness | RMS dBFS calculated from the mono 16 kHz signal; digital silence is null |
| Quiet gap | A contiguous run of non-snoring windows at or below the configured dBFS threshold, bounded by snoring segments on both sides |
| Default quiet settings | At most -45 dBFS for at least 10 seconds; an adjustable starting point |
| Dominant frequency | Strongest non-DC FFT bin after mean removal and a Hann window |
| Spectral centroid | Magnitude-weighted mean frequency of non-DC FFT bins |
| Frequency summary | Median per-window features for snoring-positive windows only |
| Rhythm mean | Mean interval between consecutive snoring-segment starts |
| Rhythm variation | Population standard deviation and coefficient of variation (standard deviation / mean), available with at least two measured intervals |

Frequency FFTs use next-power-of-two zero padding in both Python and Dart. Frequency values describe the spectrum, not fundamental pitch. Silent, constant, and insufficient-length frames have null spectral measurements. Quiet detection uses timeline dBFS rounded to two decimals, consistently with exports and the mobile implementation. Leading/trailing silence and loud non-snoring audio are not between-snore quiet gaps.

## Python commands and result contract

```bash
.venv/bin/python predict.py test_snore_16k.wav \
  --include-timeline \
  --quiet-threshold-dbfs -45 \
  --min-quiet-gap-seconds 10 \
  --timeline-csv /tmp/sanor-timeline.csv

.venv/bin/python compare.py test_snore_16k.wav \
  --json /tmp/sanor-comparison.json
```

`--no-spectral` skips spectral work while retaining snoring, loudness, quiet gaps, and rhythm. Without `--include-timeline`, JSON remains compact and retains the existing CSV export option.

Existing `summary`, `snore_events`, and file/export fields remain. New `audio_patterns` contains schema version 1, measurement settings, quiet gaps, frequency summary, and rhythm summary. Optional typed JSON `timeline` rows and CSV add spectral fields and settings columns. The local web API returns the same typed rows directly rather than reparsing CSV strings.

`POST /api/analyze` accepts WAV bytes, with optional `X-Quiet-Threshold-Dbfs` and `X-Min-Quiet-Gap-Seconds` headers. `POST /api/session-summary` accepts analysis objects with `session_id`, unique integer `part`, and `contiguous_with_previous` flags. Only explicitly confirmed adjacent joins may merge boundary events. Mixed settings are recorded and session-wide quiet-gap output is suppressed. Raw timeline values, not per-file medians, supply session level/frequency summaries.

## Verification and current limits

Run numerical, contract, session, and request-handler checks:

```bash
.venv/bin/python -m unittest discover -s tests -v
node tests/test_web_measurements.cjs
```

`tests/browser.html` is a development harness for the real interface with generated analysis fixtures. Serve the project locally and open that page to load a real analyzed sample or an eight-hour rendering fixture. This harness does not replace an end-to-end analysis-server test.

Verified here: original sample summaries/events unchanged in six CLI runs; full inference on a silent 12.25-second WAV; correct final 0.25-second window; strict finite JSON; browser event seeking; reference comparison; result removal; and desktop/390 px layouts. An eight-hour/28,800-window display fixture rendered in approximately 5 ms on this machine. That is a display check, not an eight-hour recording or inference test.

Three runs each on the 150.435-second sample had median process times of 1.946 seconds without spectral work and 1.886 seconds with it. The small difference is timing noise, not evidence that spectral work improves speed.

The environment denied opening the analysis server's port during this session. Its processing function and request handlers were exercised directly; the browser used a permitted static server and local fixtures. A live upload-to-analysis round trip still needs verification when running the server normally.

Flutter source now includes corresponding measurements, local playback, timeline views, baseline percentage differences, and JSON/CSV exports. Playback uses [audioplayers](https://pub.dev/packages/audioplayers); save dialogs use the existing [file_picker](https://pub.dev/packages/file_picker). Flutter and Dart are unavailable here, so the mobile source, parity tests, build, playback behavior, permissions, lock-screen behavior, and device performance remain unverified. Background recording has not been added.

## Extended loudness, pitch, and rhythm features

The Python/web version now adds:

- `snore_mean_rms` and `snore_max_rms`, with corresponding dBFS fields. The mean is a duration-weighted arithmetic mean of linear per-window RMS, converted to dBFS afterward. It is not an arithmetic mean of decibels. Maximum means the highest analysis-window RMS, not a peak-sample measurement.
- `audio_patterns.post_gap_loudness`: comparisons of up to three seconds of detected snoring immediately before and after a detected quiet gap. Both sides must directly adjoin the gap; intervening non-snoring speech/noise prevents the comparison. A return at least 3 dB louder is marked `is_louder`. This configurable helper's default is an engineering display threshold, not an apnea classification rule. JSON retains all comparisons and their before/after levels; the playback list highlights louder returns.
- Per-window `pitch_hz`, `pitch_confidence`, and `voiced_frame_fraction`. The estimator uses normalized autocorrelation on 80 ms frames with a 40 ms hop, downsampled to 4 kHz, searching 50–1000 Hz. It requires correlation at least 0.6 and at least three accepted subframes comprising half the window. Confidence is a correlation measurement, not a calibrated probability. Unclear/noisy/nonperiodic windows return null pitch. Pitch is computed only on snoring-positive windows and is separate from dominant frequency and spectral centroid.
- `audio_patterns.rhythm_autocorrelation`: normalized autocorrelation of a roughly 10 Hz RMS envelope masked to snoring-positive windows. It searches 1–15-second periods with at least three observed cycles and a correlation of at least 0.3. A short or constant signal, or absence of a qualifying peak, yields no period estimate. This measures recurring sound-level patterns, not actual breathing rate.
- `audio_patterns.rhythm_timeline`: local period estimates in 60-second windows advanced every 30 seconds; a final window of at least 10 seconds retains its actual length. Missing estimates remain null. Each file is analyzed independently; session summaries do not synthesize an autocorrelation curve across recording joins.
- An optional bounded spectrogram using Hann-windowed 512-sample FFTs, 256-sample hops, and mean power aggregation into at most 600 time bins × 128 frequency bins. It covers the entire recording, including non-snoring sound. Values are relative one-sided spectral power density in dBFS/Hz. Digital silence is floored at -120; empty time bins are null. The chart uses the same -110 to -20 color range across files; display colors saturate outside that range, while exports retain the numeric measurements.

The web automatically requests the spectrogram and exposes the new charts under “ดู Spectrogram, Pitch และจังหวะเสียง”. Click the spectrogram or pitch plot to seek playback, or use the existing keyboard-accessible time slider. The autocorrelation plot uses lag time, while the local rhythm plot uses time within the recording. New summary values also appear in comparison CSV exports.

For the command line:

```bash
.venv/bin/python predict.py test_snore_16k.wav --include-timeline --include-spectrogram \
  --timeline-csv /tmp/sanor-extended-timeline.csv
node tests/test_audio_charts.cjs
```

`--include-spectrogram` cannot be combined with `--no-spectral`. Tests cover weighted/partial-window loudness, pure/harmonic tones, silence/noise abstention, adjacency of quiet gaps, known five-second envelope rhythm, and bounded spectrogram bins. The browser harness includes a generated 200 Hz measurement fixture to exercise pitch and louder-return display; its manual labels are not an AI accuracy test. These extended features have not yet been ported to Flutter. Gasping and wheezing classifiers and real apnea-model training still need labeled data.

## Research-informed scoring criteria (experimental)

The dashboard now applies the measured values to separate 0–100 categories:

- Duration points = `100 * (1 - detected_snore_seconds / recording_seconds)`. This is the existing project-defined score; 25% snoring deducts 25 points.
- Pattern points = `100 * (1 - qualifying_intervals / total_consecutive_intervals)`. Qualifying means strictly `10 < start-to-start interval < 100` seconds. Two qualifying intervals out of four deduct 50 points. No consecutive intervals returns null, not 100.
- PSS remains unavailable until calibrated psychoacoustic loudness N5 (sone) and mean roughness (asper) are implemented; RMS/dBFS are not substitutes. Null is not zero.

The pattern interval criterion comes from [STII research](https://arxiv.org/abs/1208.2242), but converting its interval fraction into points is our own unvalidated rubric, not the published STII formula. The raw adapted STII (qualifying intervals / recording hours) is also displayed. The original study used sleep hours and 17 patients. Current model segments can merge several snores, so these are segment-based exploratory measures. High pattern points only means a smaller qualifying fraction; intervals over 100 seconds are excluded and this does not establish regularity or safety.

[Snoring duration reference](https://pmc.ncbi.nlm.nih.gov/articles/PMC8304057/) supports the underlying duration measure, not our score transformation. [PSS reference](https://link.springer.com/article/10.1007/s11325-020-02108-y) gives `28.5*ln(N5/sone) + 11.3*ln(Rmean/asper) - 23.9`; it has no inherent 0–100 scale. No combined health score or risk labels are generated. JSON contains formulas, interpretation and research URLs; CSV includes pattern points, interval counts and adapted STII.

### Combined score (version 1)

User-requested single score: `100 - 50*(snore_seconds/recording_seconds) - 50*(qualifying_start_intervals/total_start_intervals)`, rounded once to one decimal. Equivalently a 50/50 mean of the two unrounded category scores. Both valid categories are required; fewer than two events, invalid events or missing duration returns null, without changing weights. PSS is explicitly excluded. Equal weights are a project choice with no clinical validation. The dashboard and comparison table show this composite; category details are collapsed. Existing CSV duration fields retain their meaning, with new combined_snore_score/version fields. JSON includes the composite formula, weights and exclusions. This supersedes the earlier statement that no combined score is generated; no combined *health* score is generated.
