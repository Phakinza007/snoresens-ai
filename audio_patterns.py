"""Deterministic, local audio measurements; independent of the ML runtime."""
from __future__ import annotations

from bisect import bisect_right
import math
import numpy as np


def validate_settings(quiet_threshold_dbfs: float, min_gap_seconds: float) -> None:
    if not math.isfinite(quiet_threshold_dbfs) or quiet_threshold_dbfs > 0:
        raise ValueError('Quiet threshold must be finite and at most 0 dBFS')
    if not math.isfinite(min_gap_seconds) or min_gap_seconds <= 0:
        raise ValueError('Minimum quiet gap must be a positive finite duration')


def detect_quiet_gaps(timeline: list[dict], snore_events: list[dict],
                      quiet_threshold_dbfs: float = -45.0,
                      min_gap_seconds: float = 10.0) -> list[dict]:
    validate_settings(quiet_threshold_dbfs, min_gap_seconds)
    events = sorted(snore_events, key=lambda event: event['start_seconds'])
    starts = [event['start_seconds'] for event in events]
    gaps = []
    run_start = run_end = None

    def finish():
        if run_start is None or run_end - run_start + 1e-6 < min_gap_seconds:
            return
        preceding = bisect_right(starts, run_start) - 1
        if (0 <= preceding < len(events) - 1
                and events[preceding]['end_seconds'] <= run_start + 1e-6
                and run_end <= events[preceding + 1]['start_seconds'] + 1e-6):
            gaps.append(dict(start_seconds=round(run_start, 3), end_seconds=round(run_end, 3),
                             duration_seconds=round(run_end - run_start, 3)))

    for row in timeline:
        start, duration = float(row['start_seconds']), float(row['duration_seconds'])
        level = row['rms_dbfs']
        quiet = row.get('prediction') != 'snore' and (
            level is None or math.isfinite(level) and level <= quiet_threshold_dbfs)
        if run_end is not None and abs(start - run_end) > 1e-6:
            finish()
            run_start = run_end = None
        if quiet:
            if run_start is None:
                run_start = start
            run_end = start + duration
        else:
            finish()
            run_start = run_end = None
    finish()
    return gaps


def spectral_features(frame: np.ndarray, sample_rate: int) -> dict:
    missing = dict(dominant_frequency_hz=None, spectral_centroid_hz=None)
    samples = np.asarray(frame, dtype=np.float64)
    if sample_rate <= 0 or len(samples) < 4 or not np.all(np.isfinite(samples)):
        return missing
    samples = samples - samples.mean()
    if np.max(np.abs(samples)) <= 1e-12:
        return missing
    magnitude = np.abs(np.fft.rfft(samples * np.hanning(len(samples)), n=1 << (len(samples) - 1).bit_length()))
    magnitude[0] = 0
    total = float(magnitude.sum())
    if total <= 1e-12:
        return missing
    frequencies = np.fft.rfftfreq(1 << (len(samples) - 1).bit_length(), 1 / sample_rate)
    return dict(dominant_frequency_hz=round(float(frequencies[np.argmax(magnitude)]), 3),
                spectral_centroid_hz=round(float(np.dot(frequencies, magnitude) / total), 3))


def summarize_rhythm(snore_events: list[dict]) -> dict:
    starts = sorted(float(event['start_seconds']) for event in snore_events)
    intervals = np.diff(starts)
    mean = float(intervals.mean()) if len(intervals) else None
    std = float(intervals.std()) if len(intervals) >= 2 else None
    return dict(interval_count=len(intervals),
                mean_start_interval_seconds=round(mean, 6) if mean is not None else None,
                std_start_interval_seconds=round(std, 6) if std is not None else None,
                interval_cv=round(std / mean, 6) if std is not None and mean > 0 else None)


def build_patterns(timeline: list[dict], snore_events: list[dict],
                   quiet_threshold_dbfs: float = -45.0, min_gap_seconds: float = 10.0) -> dict:
    def median(key):
        values = [row[key] for row in timeline if row.get('prediction') == 'snore'
                  and row.get(key) is not None and math.isfinite(row[key])]
        return round(float(np.median(values)), 3) if values else None
    gaps = detect_quiet_gaps(timeline, snore_events, quiet_threshold_dbfs, min_gap_seconds)
    return dict(schema_version=1,
                config=dict(quiet_threshold_dbfs=quiet_threshold_dbfs, min_quiet_gap_seconds=min_gap_seconds,
                            window_seconds=1, frequency_method='mean-removed Hann rFFT magnitude; DC excluded; next-power-of-two padding',
                            rhythm_method='consecutive snoring-segment start intervals; population std',
                            pitch_method='normalized autocorrelation; 80 ms frames, 40 ms hop; 50–1000 Hz; confidence >= 0.6',
                            post_gap_context_seconds=3, louder_return_threshold_db=3),
                quiet_gaps=gaps,
                post_gap_loudness=compare_gap_loudness(timeline, snore_events, gaps),
                frequency_summary=dict(median_dominant_frequency_hz=median('dominant_frequency_hz'),
                                       median_spectral_centroid_hz=median('spectral_centroid_hz'),
                                       median_pitch_hz=median('pitch_hz')),
                rhythm_summary=summarize_rhythm(snore_events))

# Re-export the extended measurements alongside the original analysis helpers.
from audio_details import loudness_statistics, estimate_pitch, compare_gap_loudness, rhythm_autocorrelation, bounded_spectrogram, rhythm_over_time
