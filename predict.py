"""Run local audio models with 20 ms boundary refinement and cached 100 ms contexts."""

from __future__ import annotations

import argparse
import csv
import json
from math import ceil, gcd
from pathlib import Path

try:
    import numpy as np
    import soundfile as sf
    import tensorflow as tf
    from scipy.signal import resample_poly
except ModuleNotFoundError as error:
    raise SystemExit(
        "Missing runtime package. In the project folder, activate the Python 3.12 "
        "environment and run: python -m pip install -r requirements-inference.txt"
    ) from error


from audio_patterns import build_patterns, spectral_features, validate_settings, loudness_statistics, estimate_pitch, rhythm_autocorrelation, bounded_spectrogram, rhythm_over_time
from apnea_research import ResearchModel, model_status
from sleep_audio import add_sound_scores, build_sound_events, breathing_rate_over_time
from temporal_segmentation import analysis_windows, decision_mask, activity_threshold


SAMPLE_RATE = 16_000
FRAME_SAMPLES = 16_000
YAMNET_SAMPLES = 15_600
YAMNET_COUGH_INDEX = 42


def load_wave(path: Path) -> np.ndarray:
    audio, rate = sf.read(path, dtype="float32", always_2d=True)
    mono = audio.mean(axis=1)
    if rate != SAMPLE_RATE:
        divisor = gcd(rate, SAMPLE_RATE)
        mono = resample_poly(mono, SAMPLE_RATE // divisor, rate // divisor)
    return np.asarray(mono, dtype=np.float32)


def interpreter(path: Path, expected_input: list[int], expected_output: list[int]):
    model = tf.lite.Interpreter(model_path=str(path))
    model.allocate_tensors()
    input_info = model.get_input_details()[0]
    output_info = model.get_output_details()[0]
    if input_info["shape"].tolist() != expected_input:
        raise ValueError(f"Unexpected input shape in {path}: {input_info['shape']}")
    if output_info["shape"].tolist() != expected_output:
        raise ValueError(f"Unexpected output shape in {path}: {output_info['shape']}")
    return model, input_info["index"], output_info["index"]


def frame_rms_dbfs(frame: np.ndarray) -> float | None:
    """RMS relative to full-scale digital audio; silence has no finite dBFS."""
    rms = float(np.sqrt(np.mean(np.square(frame.astype(np.float64)))))
    return 20.0 * float(np.log10(rms)) if rms > 0 else None


def summarize(
    probabilities: list[float],
    cough_scores: list[float],
    cough_probabilities: list[float | None],
    frame_durations: list[float],
    rms_dbfs_values: list[float | None],
    threshold: float,
    decisions: list[bool] | None = None,
) -> tuple[dict, list[dict], list[dict]]:
    timeline = []
    events = []
    event_start = None
    event_duration = 0.0
    snore_seconds = 0.0
    snore_levels = []
    snore_rms_levels, snore_durations = [], []
    elapsed = 0.0

    masks = decisions if decisions is not None else [p >= threshold for p in probabilities]
    for probability, cough_score, cough_probability, duration, rms_dbfs, is_snore in zip(
        probabilities, cough_scores, cough_probabilities,
        frame_durations, rms_dbfs_values, masks, strict=True
    ):
        timeline.append(
            {
                "start_seconds": round(elapsed, 3),
                "duration_seconds": round(duration, 3),
                "snore_probability": round(probability, 6),
                "yamnet_cough_score": round(cough_score, 6),
                "cough_probability": round(cough_probability, 6)
                if cough_probability is not None else None,
                "rms_dbfs": round(rms_dbfs, 2) if rms_dbfs is not None else None,
                "prediction": "snore" if is_snore else "non_snore",
            }
        )
        if is_snore:
            snore_seconds += duration
            snore_rms_levels.append(rms_dbfs)
            snore_durations.append(duration)
            if rms_dbfs is not None:
                snore_levels.append(rms_dbfs)
            if event_start is None:
                event_start = elapsed
                event_duration = 0.0
            event_duration += duration
        elif event_start is not None:
            events.append(
                {
                    "start_seconds": round(event_start, 3),
                    "end_seconds": round(elapsed, 3),
                    "duration_seconds": round(event_duration, 3),
                }
            )
            event_start = None
            event_duration = 0.0
        elapsed += duration

    if event_start is not None:
        events.append(
            {
                "start_seconds": round(event_start, 3),
                "end_seconds": round(elapsed, 3),
                "duration_seconds": round(event_duration, 3),
            }
        )

    summary = {
        "recording_seconds": round(elapsed, 3),
        "detected_snore_seconds": round(snore_seconds, 3),
        "snore_percent_of_recording": round(100 * snore_seconds / elapsed, 2)
        if elapsed
        else 0.0,
        "snore_event_count": len(events),
        "longest_snore_event_seconds": round(
            max((event["duration_seconds"] for event in events), default=0.0), 3
        ),
        "snore_median_rms_dbfs": round(float(np.median(snore_levels)), 2)
        if snore_levels else None,
        "snore_p95_rms_dbfs": round(float(np.percentile(snore_levels, 95)), 2)
        if snore_levels else None,
        "level_note": "dBFS is relative to this recording, not calibrated sound pressure level.",
        "threshold": threshold,
        "interpretation": "Audio snore estimate only; this is not a medical severity score.",
        "cough_score_note": "Cough scores are review hints, not validated cough counts.",
    }
    summary.update({f'snore_{key}': value for key, value in loudness_statistics(snore_rms_levels, snore_durations).items()})
    return summary, events, timeline


def build_output(file: str, summary: dict, events: list[dict], timeline: list[dict],
                 quiet_threshold: float, min_gap: float, include_timeline: bool, *,
                 audio: np.ndarray | None = None, include_spectrogram: bool = False) -> dict:
    output = dict(file=file, summary=summary, snore_events=events,
                  audio_patterns=build_patterns(timeline, events, quiet_threshold, min_gap))
    cough_threshold = summary.get('cough_review_threshold')
    output['sound_review'] = build_sound_events(timeline, cough_threshold)
    if audio is not None:
        output['breathing_rate'] = breathing_rate_over_time(audio, SAMPLE_RATE, timeline, cough_threshold)
        output['audio_patterns']['rhythm_autocorrelation'] = rhythm_autocorrelation(audio, SAMPLE_RATE, timeline)
        output['audio_patterns']['rhythm_timeline'] = rhythm_over_time(audio, SAMPLE_RATE, timeline)
        if include_spectrogram:
            output['audio_patterns']['spectrogram'] = bounded_spectrogram(audio, SAMPLE_RATE)
    if include_timeline:
        output['timeline'] = timeline
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wav", type=Path, help="WAV file to classify")
    parser.add_argument("--models", type=Path, default=Path(__file__).parent / "artifacts")
    parser.add_argument('--legacy-snore',action='store_true',help='Reproduce original head and one-second decisions')
    parser.add_argument('--hop-seconds',type=float,default=.02,help='Boundary spacing; cached model decisions every 100 ms use 975 ms context')
    parser.add_argument(
        "--timeline-csv", type=Path,
        help="Optionally save the per-cell predictions to a CSV file",
    )
    parser.add_argument(
        "--cough-review-csv", type=Path,
        help="Save windows ranked by raw YAMNet cough score for manual review",
    )
    parser.add_argument(
        "--cough-review-limit", type=int, default=30,
        help="Maximum windows in cough review CSV (default: 30)",
    )
    parser.add_argument('--apnea-research', action='store_true', help='Run a separately trained audio-only respiratory-event research model')
    parser.add_argument('--apnea-models', type=Path, help='Research model directory; default is <models>/apnea')
    parser.add_argument('--include-timeline', action='store_true', help='Include typed per-window rows in JSON')
    parser.add_argument('--quiet-threshold-dbfs', type=float, default=-45.0)
    parser.add_argument('--min-quiet-gap-seconds', type=float, default=10.0)
    parser.add_argument('--include-spectrogram', action='store_true', help='Include a bounded relative-power spectrogram in JSON')
    parser.add_argument('--no-spectral', action='store_true', help='Skip spectral measurements')
    args = parser.parse_args()
    try:
        validate_settings(args.quiet_threshold_dbfs, args.min_quiet_gap_seconds)
    except ValueError as error:
        parser.error(str(error))
    if args.no_spectral and args.include_spectrogram:
        parser.error('--include-spectrogram cannot be combined with --no-spectral')
    if args.cough_review_limit < 1:
        parser.error("--cough-review-limit must be at least 1")

    apnea_directory = args.apnea_models or args.models / 'apnea'
    apnea_model = None
    if args.apnea_research:
        try:
            apnea_model = ResearchModel(apnea_directory)
        except (OSError, ValueError, KeyError, TypeError) as error:
            parser.error(f'Apnea research model unavailable: {error}')
    audio = load_wave(args.wav)
    if len(audio) == 0:
        raise ValueError("The WAV file contains no audio")
    v2=args.models/'snore_v2'
    use_v2=not args.legacy_snore and (v2/'metrics.json').is_file()
    config = json.loads(((v2/'metrics.json') if use_v2 else (args.models/'mobile_metrics.json')).read_text(encoding="utf-8"))
    threshold = float(config["threshold"])
    base, base_in, base_out = interpreter(
        args.models / "yamnet_base.tflite", [YAMNET_SAMPLES], [1, 521]
    )
    head, head_in, head_out = interpreter(
        (v2 if use_v2 else args.models) / "snore_score_head.tflite", [1, 521], [1, 1]
    )
    cough_head_path = args.models / "cough_score_head.tflite"
    cough_head = (
        interpreter(cough_head_path, [1, 521], [1, 1])
        if cough_head_path.is_file() else None
    )
    cough_metrics_path = args.models / "cough_metrics.json"
    cough_review_threshold = (
        float(json.loads(cough_metrics_path.read_text(encoding="utf-8"))["threshold"])
        if cough_head and cough_metrics_path.is_file() else None
    )

    probabilities = []
    cough_scores = []
    cough_probabilities = []
    sound_scores = []
    frame_durations = []
    rms_dbfs_values = []
    contexts=[]
    if args.legacy_snore:
        def legacy_windows():
            for at in range(0,len(audio),FRAME_SAMPLES):
                cell=audio[at:at+FRAME_SAMPLES];context=np.zeros(YAMNET_SAMPLES,dtype=np.float32);context[:min(len(cell),YAMNET_SAMPLES)]=cell[:YAMNET_SAMPLES]
                yield at,cell,context,at
        windows=legacy_windows()
    else:windows=analysis_windows(audio,args.hop_seconds)
    cached_start=None
    cached_scores=None
    for at,frame,waveform,context_start in windows:
        rms_dbfs_values.append(frame_rms_dbfs(frame))
        contexts.append((at,context_start))
        if context_start!=cached_start:
            base.set_tensor(base_in, waveform)
            base.invoke()
            cached_scores=base.get_tensor(base_out)
            cached_start=context_start
        scores=cached_scores
        sound_row = {}
        add_sound_scores(sound_row, scores)
        sound_scores.append(sound_row)
        cough_scores.append(float(scores[0, YAMNET_COUGH_INDEX]))
        if cough_head:
            cough_model, cough_in, cough_out = cough_head
            cough_model.set_tensor(cough_in, scores)
            cough_model.invoke()
            cough_probabilities.append(float(cough_model.get_tensor(cough_out)[0, 0]))
        else:
            cough_probabilities.append(None)
        head.set_tensor(head_in, scores)
        head.invoke()
        probabilities.append(float(head.get_tensor(head_out)[0, 0]))
        frame_durations.append(len(frame) / SAMPLE_RATE)

    parent_levels=[frame_rms_dbfs(audio[at:at+1600]) for at in range(0,len(audio),1600)]
    floor=activity_threshold(parent_levels) if args.hop_seconds<.1 else activity_threshold(rms_dbfs_values)
    decisions=None if args.legacy_snore else decision_mask(probabilities,rms_dbfs_values,threshold,activity_floor=floor)
    if decisions is not None and args.hop_seconds<.1:
        decisions=[positive and parent_levels[at//1600] is not None and parent_levels[at//1600]>=floor
                   for positive,(at,_) in zip(decisions,contexts,strict=True)]
    summary, events, timeline = summarize(
        probabilities, cough_scores, cough_probabilities,
        frame_durations, rms_dbfs_values, threshold,
        decisions
    )
    for second, row in enumerate(timeline):
        at,context_start=contexts[second]
        row.update(sound_scores[second],analysis_hop_seconds=1 if args.legacy_snore else args.hop_seconds,
                   context_start_seconds=round(context_start/SAMPLE_RATE,3),
                   context_end_seconds=round(min(len(audio),context_start+YAMNET_SAMPLES)/SAMPLE_RATE,3))
        if not args.legacy_snore:
            parent_level=parent_levels[at//1600]
            parent_pass=args.hop_seconds>=.1 or (parent_level is not None and parent_level>=floor)
            row.update(activity_floor_dbfs=round(floor,2),activity_pass=parent_pass and rms_dbfs_values[second] is not None and rms_dbfs_values[second]>=floor,
                       parent_rms_dbfs=round(parent_level,2) if parent_level is not None else None)
        features = dict(dominant_frequency_hz=None, spectral_centroid_hz=None)
        if row['prediction'] == 'snore' and not args.no_spectral:
            features = spectral_features(audio[at:at+round(frame_durations[second]*SAMPLE_RATE)], SAMPLE_RATE)
        pitch = dict(pitch_hz=None, pitch_confidence=None, voiced_frame_fraction=0.0)
        if row['prediction'] == 'snore' and not args.no_spectral:
            pitch = estimate_pitch(audio[context_start:context_start+YAMNET_SAMPLES], SAMPLE_RATE)
        row.update(features)
        row.update(pitch)
        row.update(analysis_schema_version=1, quiet_threshold_dbfs=args.quiet_threshold_dbfs,
                   min_quiet_gap_seconds=args.min_quiet_gap_seconds, spectral_enabled=not args.no_spectral)
    summary["cough_review_threshold"] = cough_review_threshold
    summary['model_version']='snore-v2-breathing-negatives' if use_v2 else 'snore-v1'
    summary['analysis_hop_seconds']=1 if args.legacy_snore else args.hop_seconds
    summary['model_context_seconds']=.975
    summary['segmentation_version']='micro-20ms-v1' if not args.legacy_snore and args.hop_seconds==.02 else 'activity-100ms-v1'
    summary['model_hop_seconds']=1 if args.legacy_snore else max(.1,args.hop_seconds)
    if not args.legacy_snore:
        summary['activity_floor_dbfs']=round(floor,2)
        summary['activity_gate_note']='Experimental local activity gate on boundary cells and their 100 ms parent: max(-60, P20 + min(6, (P95-P20)/2)) dBFS over finite cells >= -80 dBFS. May miss soft snoring; not a breathing classifier.'
    summary["cough_review_note"] = (
        "Threshold selected on prompted Coswara clips; do not use it to count coughs in sleep recordings."
        if cough_review_threshold is not None else
        "No trained cough head and threshold available."
    )
    if args.timeline_csv:
        args.timeline_csv.parent.mkdir(parents=True, exist_ok=True)
        with args.timeline_csv.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=list(timeline[0]))
            writer.writeheader()
            writer.writerows(timeline)

    if args.cough_review_csv:
        args.cough_review_csv.parent.mkdir(parents=True, exist_ok=True)
        ranking_key = "cough_probability" if cough_head else "yamnet_cough_score"
        ranked = sorted(timeline, key=lambda row: row[ranking_key], reverse=True)[
            : args.cough_review_limit
        ]
        with args.cough_review_csv.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=list(timeline[0]))
            writer.writeheader()
            writer.writerows(ranked)

    output = build_output(str(args.wav), summary, events, timeline,
                          args.quiet_threshold_dbfs, args.min_quiet_gap_seconds, args.include_timeline,
                          audio=audio, include_spectrogram=args.include_spectrogram)
    output['apnea_research'] = apnea_model.analyze(args.wav) if apnea_model else model_status(apnea_directory)
    output['apnea_research']['enabled'] = apnea_model is not None
    output['audio_patterns']['config']['spectral_enabled'] = not args.no_spectral
    output['timeline_csv'] = str(args.timeline_csv) if args.timeline_csv else None
    output['cough_review_csv'] = str(args.cough_review_csv) if args.cough_review_csv else None
    print(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
