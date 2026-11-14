# Audio-only apnea research

## What exists now

Sanor has a separate local research pipeline for labeling audio windows, training a baseline classifier, reporting held-out performance, exporting numeric model artifacts, and reviewing scored audio windows. The questionnaire is deferred.

**No real apnea model has been trained.** The existing snoring and cough data do not contain the required sleep-study labels. The application reports `not_trained` and keeps the research switch disabled until a compatible artifact exists. No personal risk percentage, AHI, or apnea-event count is generated.

The software has been exercised with generated audio to check its wiring. A synthetic artifact is explicitly marked `synthetic_only` and cannot analyze ordinary user recordings. Synthetic performance is not evidence of apnea-detection performance.

## Data source and model target

[PSG-Audio](https://doi.org/10.1038/s41597-021-00977-w) is a candidate dataset with synchronized ambient microphone recordings and clinical annotations. The [original dataset](https://doi.org/10.11922/sciencedb.00345) must be acquired and its version, license, channel names, and alignment checked. No dataset has been downloaded for this pipeline. Hospital ambient recordings also need external testing against the phone and bedroom setup used by Sanor.

The baseline target is **a 30-second audio window containing annotated apnea/hypopnea**, not patient-level OSA diagnosis or distinguishing central from obstructive apnea. Obstructive, central, and mixed apneas and hypopneas all contribute positive event time. A separately validated person-level model and calibration would be needed for a risk percentage. Clinical diagnostic use requires appropriate validation; see the [AASM diagnostic testing guideline](https://aasm.org/resources/clinicalguidelines/diagnostic-testing-osa.pdf).

## Prepare clinical audio

Use ambient microphone audio only. Physiological signals and tracheal/contact microphone recordings must not be substituted for the bedside audio. Export ambient audio from EDF into WAV, retain the original time base, and explicitly verify its synchronization with the annotations. This project does not yet implement an EDF/RML importer; normalized WAV/CSV input is required. Account for segmented EDF offsets and synchronization padding before generating labels.

CSV header templates are in `data/apnea/templates/`:

| File | Required fields |
| --- | --- |
| `recordings.csv` | `recording_id,audio_path,person_id,night_id,split,reference,alignment_verified` |
| `events.csv` | `recording_id,start_seconds,end_seconds,event_type` |
| `scored_sleep.csv` | `recording_id,start_seconds,end_seconds` |
| `windows.csv` | `audio_path,person_id,night_id,start_seconds,duration_seconds,label,split,reference,alignment_verified` |

Use globally unique pseudonymous person, night, and recording identifiers. `split` is `train`, `validation`, or `test`. `reference` is `PSG` or `HSAT`; `alignment_verified` must be `true` only after checking alignment. These are declarations supplied with the data, not authenticity checks performed by the program. All times are seconds relative to the exported audio start. Relative audio paths are resolved against `recordings.csv` or `windows.csv` as appropriate.

The normalized event types are `obstructive_apnea`, `central_apnea`, `mixed_apnea`, `hypopnea`, and `artifact`. Sleep coverage intervals must represent explicitly reviewed sleep audio. Do not mark wake, missing sensor data, unscored intervals, or synchronization padding as scored sleep. An empty event list without reviewed sleep coverage does not produce negative labels.

The preparation tool:

- Uses non-overlapping, full 30-second windows.
- Requires complete scored-sleep coverage for each window.
- Excludes windows with any artifact overlap.
- Labels at least 10 seconds of union respiratory-event overlap as positive.
- Labels zero overlap as negative; excludes windows with a smaller nonzero overlap.
- Rejects unknown event types and invalid/out-of-recording timestamps.
- Validates patient/night/source separation, both labels, and at least two people per split before writing the manifest.

The two-person floor is a software check, not a clinical sample-size recommendation. Boundary-window exclusion also changes the evaluation population: reported metrics cover unambiguous scored windows, not every moment of a recording.

```bash
.venv/bin/python prepare_apnea.py \
  data/apnea/recordings.csv \
  data/apnea/events.csv \
  data/apnea/scored_sleep.csv \
  --out data/apnea/windows.csv
```

Alternatively provide a `windows.csv` with these exact reviewed label definitions. Software cannot verify the clinical correctness of hand-entered labels.

## Train and evaluate

Install the existing training dependencies from `requirements.txt` into the Python environment if necessary. Feature extraction needs NumPy, SciPy, and SoundFile; training additionally uses scikit-learn.

```bash
.venv/bin/python train_apnea.py data/apnea/windows.csv --out artifacts/apnea
```

Choose a new output directory; existing models are not overwritten. The pipeline resamples to 16 kHz mono, extracts 13 log-mel MFCC means/standard deviations plus 30 per-second log-RMS and zero-crossing measurements, and fits a patient-weighted standardized logistic-regression baseline. It rejects completely silent training windows and exact waveform duplicates crossing splits.

The scaler and classifier are fitted only to training data. The review threshold maximizes validation-window balanced accuracy, with ties favoring specificity. The test set is used only to report metrics: confusion counts, precision, recall, specificity, AUROC, Brier score, per-person metrics, and false-positive windows per scored hour. Brier score is descriptive; scores are not calibrated personal risk.

The outputs are `apnea_research.npz` and `apnea_research.json`. The latter records feature definitions, threshold selection, patient splits, manifest checksum, weights checksum, and validation status. Numeric NPZ arrays avoid executable pickle models. Training always marks clinical validation false.

## Analyze audio

```bash
.venv/bin/python apnea_research.py --status
.venv/bin/python apnea_research.py night.wav --models artifacts/apnea

# Combine with ordinary snoring analysis; explicit opt-in:
.venv/bin/python predict.py night.wav --apnea-research --include-timeline
```

Without opt-in, ordinary analysis returns model availability but no apnea-model scores. When enabled, research inference processes non-overlapping 30-second windows. Digital-silence windows receive `insufficient_signal`; a short final window receives `insufficient_duration`. Neither receives a score. Consecutive flagged windows become coarse review intervals, not individual apnea events. Abstained windows are not treated as negative results.

All research results retain `risk_percent: null` and `clinical_validation: false`. Model scores are raw window classifier outputs. The web interface enables the research checkbox only when a compatible `research_only` artifact is present. It snapshots the selection for each recording session. Flagged review intervals appear in the existing playback list.

The mobile application does not yet run this apnea baseline; its existing audio-pattern features remain separate.

## Verification and next dependency

```bash
.venv/bin/python -m unittest discover -s tests -v
node tests/test_web_measurements.cjs
.venv/bin/python tests/smoke_apnea.py
```

The smoke script generates artificial audio in a temporary folder, exercises CSV preparation/training/serialization/inference, confirms synthetic artifacts are rejected for normal use, then removes the files. It does not simulate apnea or train a usable clinical model.

Next required work: acquire a verified clinical audio subset, export and align its ambient channel, create person-separated manifests, train the baseline, examine held-out errors and uncertainty, and test it on external phone recordings. Until that data exists, real training and any validated apnea screening claim remain incomplete.
