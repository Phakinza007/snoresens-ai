# Audio-only apnea research baseline

## Agreed scope

Use overnight microphone audio only. Defer questionnaires. Build separately from the snoring classifier. The first deliverable is an executable local training/evaluation/inference pipeline, not a claimed clinical risk score.

## Current data dependency

The existing Kaggle snoring and Coswara cough datasets have no sleep-study apnea labels and cannot train this task. PSG-Audio is a candidate source containing ambient microphone audio synchronized to clinical annotations. Its access and annotation/audio alignment must be checked before using a subset. Source: https://doi.org/10.1038/s41597-021-00977-w and https://doi.org/10.11922/sciencedb.00345. No clinical audio has been acquired for this project.

## Target and input contract

Classify full 30-second microphone windows as containing an annotated apnea/hypopnea event versus explicitly reviewed event-free sleep audio. This target covers respiratory-event review, not patient-level OSA diagnosis or subtype classification. No AHI or sleep-duration estimate is derived from recording hours.

A normalized CSV provides `audio_path,person_id,night_id,start_seconds,duration_seconds,label,split,reference,alignment_verified`. `label` is 0 or 1; `split` is train/validation/test; `reference` is PSG or HSAT; `alignment_verified` is true. These declarations describe supplied provenance; software cannot verify that they are truthful. Every row is exactly 30 seconds with confirmed alignment. Positive labels require at least 10 seconds of union overlap with clinically annotated apnea/hypopnea events; event-free negatives require full scored-sleep coverage and no respiratory-event overlap. Boundary, wake, unscored, artifact, and ambiguous windows are excluded during label preparation. Do not treat an empty annotation list as evidence of event-free sleep.

People and nights must not cross splits, and intervals from one source recording cannot overlap. Exact waveform duplicates crossing splits are rejected. Every split needs both classes and at least two people. This is a software minimum for a baseline, not a sufficient clinical validation sample.

## Baseline architecture

Extract log-mel MFCC summary statistics and per-second energy/zero-crossing features using NumPy/SciPy. Train a standardized logistic regression baseline with patient-balanced weights. Select a review threshold using validation only; report test window precision, recall, specificity, AUROC, Brier score, per-person performance, and false-positive windows per scored hour. Export numeric weights/scaler arrays to NPZ plus a JSON model card, avoiding executable pickle models. No training uses questionnaire or physiological channels.

## Inference and interface

Run full non-overlapping 30-second windows of ordinary WAV audio. Abstain on completely silent windows and on a short final window. Show raw model scores and coarse review intervals only when an actual research artifact exists and the user explicitly enables research analysis. Scores are not calibrated personal risk percentages, and flagged windows are not individual apnea counts. The default interface reports not_trained when there is no artifact. Training cannot mark clinical validation complete.

## Verification

Test alignment/provenance requirements, split leakage, duplicate signals, finite silent features, serialization parity, test-label isolation from threshold selection, missing/corrupt model states, short/silent inference, and existing snoring regression. Synthetic data may exercise the pipeline only; artifacts must retain synthetic_only status and never load into normal research inference.

## Limits

Clinical validation and a calibrated patient-level risk score require real held-out sleep-study data and external validation on target phone/bedroom recordings. Questionnaire inputs and Flutter apnea-model deployment are deferred. Existing Flutter audio-pattern source remains unbuilt without SDK/devices.
