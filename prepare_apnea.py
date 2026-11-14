"""Prepare 30-second training labels from normalized, aligned clinical annotations."""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
import tempfile

import numpy as np
import soundfile as sf
from apnea_research import WINDOW_SECONDS, load_manifest

RESPIRATORY_TYPES = {'obstructive_apnea', 'central_apnea', 'mixed_apnea', 'hypopnea'}


def checked_intervals(intervals, seconds):
    output = []
    for start, end in intervals:
        start, end = float(start), float(end)
        if not np.isfinite([start, end]).all() or not 0 <= start < end <= seconds + 1e-6:
            raise ValueError('Annotation intervals must be finite, nonnegative, and inside the recording')
        output.append((start, end))
    return sorted(output)


def union_overlap(intervals, start, end):
    merged, total = None, 0.0
    for left, right in intervals:
        left, right = max(start, left), min(end, right)
        if right <= left:
            continue
        if merged is None:
            merged = [left, right]
        elif left <= merged[1]:
            merged[1] = max(merged[1], right)
        else:
            total += merged[1] - merged[0]
            merged = [left, right]
    return total + (merged[1] - merged[0] if merged else 0)


def label_windows(recording_seconds: float, scored_sleep: list[tuple], events: list[dict]) -> list[dict]:
    if not np.isfinite(recording_seconds) or recording_seconds <= 0:
        raise ValueError('Recording duration must be positive and finite')
    coverage = checked_intervals(scored_sleep, recording_seconds)
    respiratory, artifacts = [], []
    for event in events:
        kind = event['event_type']
        if kind not in RESPIRATORY_TYPES | {'artifact'}:
            raise ValueError(f'Unsupported event type: {kind}; normalize clinical annotations explicitly')
        interval = checked_intervals([(event['start_seconds'], event['end_seconds'])], recording_seconds)[0]
        (artifacts if kind == 'artifact' else respiratory).append(interval)
    respiratory.sort()
    artifacts.sort()
    rows = []
    for start in range(0, int(recording_seconds // WINDOW_SECONDS) * WINDOW_SECONDS, WINDOW_SECONDS):
        end = start + WINDOW_SECONDS
        if union_overlap(coverage, start, end) < WINDOW_SECONDS - 1e-6 or union_overlap(artifacts, start, end) > 0:
            continue
        duration = union_overlap(respiratory, start, end)
        if 0 < duration < 10 - 1e-6:
            continue  # Ambiguous boundary windows are not labeled as event-free.
        rows.append(dict(start_seconds=start, duration_seconds=WINDOW_SECONDS, label=int(duration >= 10 - 1e-6)))
    return rows


def read_csv(path: Path, columns: set[str]) -> list[dict]:
    with path.open(newline='', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file)
        if not columns.issubset(reader.fieldnames or []):
            raise ValueError(f'{path.name} requires: {", ".join(sorted(columns))}')
        return list(reader)


def prepare(recordings_path: Path, events_path: Path, coverage_path: Path, output: Path) -> int:
    metadata = {'recording_id', 'audio_path', 'person_id', 'night_id', 'split', 'reference', 'alignment_verified'}
    recordings = read_csv(recordings_path, metadata)
    identities = [r['recording_id'] for r in recordings]
    if not identities or len(set(identities)) != len(identities):
        raise ValueError('Unique recording identifiers are required')
    events, coverage = defaultdict(list), defaultdict(list)
    for event in read_csv(events_path, {'recording_id', 'start_seconds', 'end_seconds', 'event_type'}):
        if event['recording_id'] not in identities:
            raise ValueError('Event references an unknown recording')
        events[event['recording_id']].append(event)
    for interval in read_csv(coverage_path, {'recording_id', 'start_seconds', 'end_seconds'}):
        if interval['recording_id'] not in identities:
            raise ValueError('Sleep coverage references an unknown recording')
        coverage[interval['recording_id']].append((interval['start_seconds'], interval['end_seconds']))
    rows = []
    for recording in recordings:
        path = (recordings_path.parent / recording['audio_path']).resolve()
        seconds = sf.info(path).duration
        labels = label_windows(seconds, coverage[recording['recording_id']], events[recording['recording_id']])
        base = {key: recording[key] for key in metadata - {'recording_id'}}
        base['audio_path'] = str(path)
        rows.extend(dict(base, **label) for label in labels)
    if not rows:
        raise ValueError('No fully scored, unambiguous 30-second sleep windows')
    if output.exists():
        raise FileExistsError('Choose a new manifest path; existing labels will not be overwritten')
    output.parent.mkdir(parents=True, exist_ok=True)
    # Validate before exposing a manifest as ready for training.
    with tempfile.TemporaryDirectory(dir=output.parent, prefix='apnea-labels-') as folder:
        staged = Path(folder) / 'windows.csv'
        with staged.open('w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=['audio_path', 'person_id', 'night_id', 'start_seconds',
                                                     'duration_seconds', 'label', 'split', 'reference', 'alignment_verified'])
            writer.writeheader()
            writer.writerows(rows)
        load_manifest(staged)
        staged.replace(output)
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('recordings', type=Path)
    parser.add_argument('events', type=Path)
    parser.add_argument('scored_sleep', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        count = prepare(args.recordings, args.events, args.scored_sleep, args.out)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.error(str(error))
    print(f'Prepared {count} scored windows: {args.out}')


if __name__ == '__main__':
    main()
