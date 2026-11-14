"""Experimental sound-review events and gated breathing-envelope estimates.

No sleep stages, diagnoses, calibrated risk, or clinical breath counts are inferred.
YAMNet indexes follow TensorFlow's official 521-class map.
"""
from __future__ import annotations

import math
from math import gcd

import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.signal import butter, find_peaks, resample_poly, sosfilt

SOUND_THRESHOLD = 0.5
SOUND_TYPES = ('snore', 'cough', 'speech', 'breathing')


def add_sound_scores(row: dict, scores: np.ndarray) -> None:
    values = np.asarray(scores).reshape(-1)
    if len(values) != 521 or not np.isfinite(values).all():
        raise ValueError('Expected 521 finite YAMNet scores')
    row.update(yamnet_speech_score=round(float(values[0]), 6),
               yamnet_breathing_score=round(float(values[36]), 6))


def _score(row: dict, key: str) -> float | None:
    value = row.get(key)
    return float(value) if isinstance(value, (float, int)) and math.isfinite(value) else None


def _cough_score(row: dict, threshold: float | None) -> tuple[float | None, float, str]:
    trained = _score(row, 'cough_probability')
    if trained is not None:
        # Never silently substitute a threshold for an unconfigured trained head.
        return trained, threshold if threshold is not None else math.inf, 'coswara_review'
    return _score(row, 'yamnet_cough_score'), SOUND_THRESHOLD, 'yamnet_review'


def _labels(row: dict, cough_threshold: float | None) -> dict:
    level = _score(row, 'rms_dbfs')
    if level is None or level < -60:
        return {}
    labels = {}
    if row.get('prediction') == 'snore':
        labels['snore'] = (_score(row, 'snore_probability'), 'snore_classifier')
    cough, threshold, source = _cough_score(row, cough_threshold)
    if cough is not None and cough >= threshold:
        labels['cough'] = (cough, source)
    for kind in ('speech', 'breathing'):
        value = _score(row, f'yamnet_{kind}_score')
        if value is not None and value >= SOUND_THRESHOLD:
            labels[kind] = (value, 'yamnet_review')
    return labels


def build_sound_events(timeline: list[dict], cough_threshold: float | None = None) -> dict:
    events, active = [], {}
    for row in timeline:
        start, duration = float(row['start_seconds']), float(row['duration_seconds'])
        labels = _labels(row, cough_threshold)
        for kind in list(active):
            if kind not in labels or abs(active[kind]['end_seconds'] - start) > .001:
                events.append(active.pop(kind))
        for kind, (score, source) in labels.items():
            if kind not in active:
                active[kind] = dict(sound_type=kind, start_seconds=start, end_seconds=start,
                                    duration_seconds=0, max_score=score, source=source)
            event = active[kind]
            event['end_seconds'] = round(start + duration, 3)
            event['duration_seconds'] = round(event['duration_seconds'] + duration, 3)
            if score is not None:
                event['max_score'] = max(event['max_score'] or 0, score)
    events.extend(active.values())
    events.sort(key=lambda item: (item['start_seconds'], item['sound_type']))
    return dict(schema_version=1, status='experimental', clinical_validation=False,
                supported_types=list(SOUND_TYPES), events=events,
                categories=[dict(sound_type=kind,
                                 review_segment_count=sum(e['sound_type'] == kind for e in events),
                                 detected_seconds=round(sum(e['duration_seconds'] for e in events if e['sound_type'] == kind), 3))
                            for kind in SOUND_TYPES],
                config=dict(yamnet_review_threshold=SOUND_THRESHOLD, cough_review_threshold=cough_threshold,
                            minimum_rms_dbfs=-60),
                note='Overlapping review segments, not clinical event counts. Speech is not proof of sleep talking. '
                     'Unflagged sound is unclassified, not normal breathing. Scores are not calibrated confidence.')


def _estimate_window(signal: np.ndarray, sample_rate: int, rows: list[dict],
                     start: float, duration: float, cough_threshold: float | None) -> dict:
    result = dict(start_seconds=round(start, 3), duration_seconds=round(duration, 3),
                  breaths_per_minute=None, period_seconds=None, correlation_strength=None,
                  interval_cv=None, evidence_fraction=0.0, status='insufficient_duration')
    if duration < 30 - 1e-6:
        return result
    if np.mean(np.abs(signal) >= .999) > .001:
        return dict(result, status='clipped_signal')
    if float(np.sqrt(np.mean(signal.astype(np.float64) ** 2))) < .001:
        return dict(result, status='insufficient_signal')
    evidence, conflicting, snoring = 0.0, 0.0, 0.0
    for row in rows:
        overlap = max(0, min(start + duration, row['start_seconds'] + row['duration_seconds'])
                      - max(start, row['start_seconds']))
        labels = _labels(row, cough_threshold)
        if 'breathing' in labels:
            evidence += overlap
        if 'speech' in labels or 'cough' in labels:
            conflicting += overlap
        if 'snore' in labels:
            snoring += overlap
    result['evidence_fraction'] = round(evidence / duration, 3)
    if evidence / duration < .5:
        return dict(result, status='insufficient_breathing_evidence')
    if conflicting / duration > .1 or snoring / duration > .2:
        return dict(result, status='mixed_sound')
    # Process one 30-second chunk at a time to bound memory for long recordings.
    divisor = gcd(sample_rate, 4000)
    reduced = resample_poly(signal, 4000 // divisor, sample_rate // divisor) if sample_rate != 4000 else signal
    filtered = sosfilt(butter(4, [200, 1800], btype='bandpass', fs=4000, output='sos'), reduced)
    count = len(filtered) // 400
    envelope = np.sqrt(np.mean(filtered[:count*400].reshape(count, 400) ** 2, axis=1))
    envelope = gaussian_filter1d(envelope, 1)
    # Discard filter startup/edge effects before measuring periodicity.
    envelope = envelope[5:-5]
    mean, std = float(envelope.mean()), float(envelope.std())
    if mean < 1e-7 or std / mean < .15:
        return dict(result, status='no_clear_modulation')
    centered = envelope - mean
    # Compare at least three cycles, restricting this exploratory estimator to 6–30/min.
    lags = np.arange(20, min(100, len(centered)//3) + 1)
    correlations = np.array([np.dot(centered[:-lag], centered[lag:]) /
                             max(np.linalg.norm(centered[:-lag])*np.linalg.norm(centered[lag:]), 1e-20)
                             for lag in lags])
    peaks = find_peaks(correlations)[0].tolist()
    if len(correlations) > 1:
        if correlations[0] > correlations[1]: peaks.insert(0, 0)
        if correlations[-1] > correlations[-2]: peaks.append(len(correlations)-1)
    good = [i for i in peaks if correlations[i] >= .65]
    if not good:
        return dict(result, status='no_clear_period')
    maximum = max(correlations[i] for i in good)
    best = next(i for i in good if correlations[i] >= maximum * .95)
    period = float(lags[best]) / 10
    result['correlation_strength'] = round(float(correlations[best]), 4)
    # Reject sparse or irregular bursts even when autocorrelation has a peak.
    breath_peaks = find_peaks(envelope, distance=max(12, int(period*10*.6)), prominence=std*.5)[0]
    intervals = np.diff(breath_peaks) / 10
    if len(intervals) < 3:
        return dict(result, status='insufficient_cycles')
    cv = float(intervals.std() / intervals.mean())
    result['interval_cv'] = round(cv, 4)
    if cv > .25 or abs(float(np.median(intervals)) - period) / period > .15:
        return dict(result, status='irregular_or_ambiguous')
    return dict(result, status='estimated', period_seconds=round(period, 3),
                breaths_per_minute=round(60 / period, 2))


def breathing_rate_over_time(audio: np.ndarray, sample_rate: int, timeline: list[dict],
                             cough_threshold: float | None = None) -> dict:
    signal = np.asarray(audio)
    if signal.ndim != 1 or not np.isfinite(signal).all() or not isinstance(sample_rate, int) or sample_rate < 4000:
        raise ValueError('Breathing analysis requires finite mono audio at >= 4000 Hz')
    windows = []
    index = 0
    for first in range(0, len(signal), 30 * sample_rate):
        chunk = signal[first:first + 30 * sample_rate]
        start, duration = first / sample_rate, len(chunk) / sample_rate
        while index < len(timeline) and timeline[index]['start_seconds'] + timeline[index]['duration_seconds'] <= start:
            index += 1
        stop = index
        while stop < len(timeline) and timeline[stop]['start_seconds'] < start + duration:
            stop += 1
        windows.append(_estimate_window(chunk, sample_rate, timeline[index:stop], start, duration, cough_threshold))
    estimates = [w for w in windows if w['status'] == 'estimated']
    estimated_seconds = sum(w['duration_seconds'] for w in estimates)
    duration = len(signal) / sample_rate
    return dict(schema_version=1, status='experimental', clinical_validation=False,
                median_breaths_per_minute=round(float(np.median([w['breaths_per_minute'] for w in estimates])), 2) if estimates else None,
                estimated_seconds=round(estimated_seconds, 3),
                coverage_percent=round(100 * estimated_seconds / duration, 2) if duration else 0,
                windows=windows,
                config=dict(window_seconds=30, min_breathing_evidence_fraction=.5,
                            max_conflicting_fraction=.1, max_snore_fraction=.2,
                            min_correlation=.65, max_interval_cv=.25, range_breaths_per_minute=[6, 30]),
                note='Experimental envelope-cycle estimate on breathing-like audio only; not validated respiratory rate. '
                     'Missing values mean abstention, never zero breaths or apnea. Regular machine noise may fool this estimator. '
                     'Snore intervals and pitch are not converted to breathing rate.')
