"""Compare snore estimates across WAV recordings using the existing models."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def analyze(path: Path) -> dict:
    command = [sys.executable, str(Path(__file__).with_name("predict.py")), str(path)]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError(f"Could not analyze {path}:\n{result.stderr or result.stdout}")
    return json.loads(result.stdout)


def comparison_row(name: str, result: dict) -> dict:
    summary = result['summary']
    hours = summary['recording_seconds'] / 3600
    patterns = result.get('audio_patterns', {})
    return dict(file=name, recording_minutes=round(summary['recording_seconds'] / 60, 2),
                snore_percent_of_recording=summary['snore_percent_of_recording'],
                snore_minutes_per_recording_hour=round(summary['detected_snore_seconds'] / hours / 60, 2) if hours else 0,
                snore_events_per_recording_hour=round(summary['snore_event_count'] / hours, 2) if hours else 0,
                snore_median_rms_dbfs=summary.get('snore_median_rms_dbfs'),
                snore_mean_rms_dbfs=summary.get('snore_mean_rms_dbfs'),
                snore_max_rms_dbfs=summary.get('snore_max_rms_dbfs'),
                louder_returns_count=sum(item['is_louder'] for item in patterns.get('post_gap_loudness', [])),
                quiet_gap_count=len(patterns['quiet_gaps']) if 'quiet_gaps' in patterns else None,
                **{key: patterns.get('frequency_summary', {}).get(key)
                   for key in ('median_dominant_frequency_hz', 'median_spectral_centroid_hz', 'median_pitch_hz')},
                interval_cv=patterns.get('rhythm_summary', {}).get('interval_cv'))


def session_summary(parts: list[dict]) -> dict:
    """Combine observed durations; unknown joins never become measured intervals."""
    import numpy as np
    from audio_patterns import build_patterns, summarize_rhythm, detect_quiet_gaps, compare_gap_loudness, loudness_statistics
    if not parts or len({p.get('session_id') for p in parts}) != 1 or not parts[0].get('session_id'):
        raise ValueError('Select parts from one recording session')
    if len({p['part'] for p in parts}) != len(parts):
        raise ValueError('Duplicate recording part')
    ordered = sorted(parts, key=lambda p: p['part'])
    events, timeline, runs = [], [], []
    offset, snore_seconds = 0.0, 0.0
    continuous = True
    run = []
    timeline_runs, run_timeline = [], []
    for index, part in enumerate(ordered):
        duration = float(part['summary']['recording_seconds'])
        if not np.isfinite(duration) or duration <= 0:
            raise ValueError('Recording parts must have positive finite durations')
        joined = index == 0 or (part.get('contiguous_with_previous') is True
                                and part['part'] == ordered[index - 1]['part'] + 1)
        if not joined:
            continuous = False
            runs.append(run)
            timeline_runs.append(run_timeline)
            run, run_timeline = [], []
        for event in part['snore_events']:
            shifted = dict(event, start_seconds=event['start_seconds'] + offset,
                           end_seconds=event['end_seconds'] + offset)
            if (joined and run and abs(run[-1]['end_seconds'] - shifted['start_seconds']) < 1e-6):
                run[-1]['end_seconds'] = shifted['end_seconds']
                run[-1]['duration_seconds'] = run[-1]['end_seconds'] - run[-1]['start_seconds']
            else:
                run.append(shifted)
        shifted_rows = [dict(row, start_seconds=row['start_seconds'] + offset) for row in part.get('timeline', [])]
        timeline.extend(shifted_rows)
        run_timeline.extend(shifted_rows)
        snore_seconds += part['summary']['detected_snore_seconds']
        offset += duration
    runs.append(run)
    timeline_runs.append(run_timeline)
    events = [event for run in runs for event in run]
    levels = [r['rms_dbfs'] for r in timeline if r.get('prediction') == 'snore' and r.get('rms_dbfs') is not None]
    settings = ordered[0].get('audio_patterns', {}).get('config', {})
    threshold = settings.get('quiet_threshold_dbfs', -45)
    min_gap = settings.get('min_quiet_gap_seconds', 10)
    configs_match = all(p.get('audio_patterns', {}).get('config', {}) == settings for p in ordered)
    patterns = build_patterns(timeline, events, threshold, min_gap)
    if not continuous:
        # Preserve gaps across confirmed joins inside each continuous run.
        patterns['quiet_gaps'] = [gap for rows, run_events in zip(timeline_runs, runs)
                                 for gap in detect_quiet_gaps(rows, run_events, threshold, min_gap)]
    patterns['post_gap_loudness'] = [item for rows, run_events in zip(timeline_runs, runs)
                                    for item in compare_gap_loudness(rows, run_events, patterns['quiet_gaps'])]
    intervals = [b['start_seconds'] - a['start_seconds'] for run in runs for a, b in zip(run, run[1:])]
    # Synthetic starts retain within-run intervals without manufacturing joins.
    starts = np.concatenate(([0.0], np.cumsum(intervals))) if intervals else []
    patterns['rhythm_summary'] = summarize_rhythm([dict(start_seconds=float(x)) for x in starts])
    if not configs_match:
        patterns['quiet_gaps'] = []
        patterns['post_gap_loudness'] = []
        patterns['config']['mixed_settings'] = True
    snore_rows = [row for row in timeline if row.get('prediction') == 'snore']
    loudness = loudness_statistics([row['rms_dbfs'] for row in snore_rows], [row['duration_seconds'] for row in snore_rows])
    return dict(summary=dict(recording_seconds=round(offset, 3), detected_snore_seconds=round(snore_seconds, 3),
                             snore_percent_of_recording=round(100 * snore_seconds / offset, 2),
                             snore_event_count=len(events),
                             longest_snore_event_seconds=max((e['duration_seconds'] for e in events), default=0),
                             snore_median_rms_dbfs=round(float(np.median(levels)), 2) if levels else None,
                             snore_p95_rms_dbfs=round(float(np.percentile(levels, 95)), 2) if levels else None,
                             **{f'snore_{key}': value for key, value in loudness.items()}),
                snore_events=events, timeline=timeline, audio_patterns=patterns,
                session_continuous=continuous, session_id=ordered[0]['session_id'])


def compare(paths: list[Path]) -> list[dict]:
    return [comparison_row(str(path), analyze(path)) for path in paths]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wavs", nargs="+", type=Path, help="WAV recordings to compare")
    parser.add_argument("--json", type=Path, help="Save comparison as JSON")
    args = parser.parse_args()
    if any(not path.is_file() for path in args.wavs):
        parser.error("Every WAV path must be an existing file")
    rows = compare(args.wavs)
    print("File | minutes | snore % | snore min/hour | events/hour | median dBFS")
    for row in rows:
        print(
            f"{row['file']} | {row['recording_minutes']:.2f} | "
            f"{row['snore_percent_of_recording']:.2f} | "
            f"{row['snore_minutes_per_recording_hour']:.2f} | "
            f"{row['snore_events_per_recording_hour']:.2f} | "
            f"{row['snore_median_rms_dbfs']}"
        )
    print("Values are model estimates per recording hour, not sleep hours or a health score.")
    print('Additional audio measurements:')
    for row in rows:
        print(f"{row['file']} | quiet gaps: {row['quiet_gap_count']} | dominant Hz: {row['median_dominant_frequency_hz']} | rhythm CV: {row['interval_cv']}")
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()
