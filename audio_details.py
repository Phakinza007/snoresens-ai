"""Descriptive loudness, pitch, spectrogram, and audio-envelope measurements."""
from __future__ import annotations

import math
from bisect import bisect_left, bisect_right
import numpy as np
from scipy.signal import find_peaks, resample_poly


def loudness_statistics(levels: list[float | None], durations: list[float]) -> dict:
    if len(levels) != len(durations):
        raise ValueError('Loudness levels and durations must have equal lengths')
    if any(not math.isfinite(d) or d <= 0 for d in durations):
        raise ValueError('Window durations must be positive and finite')
    if any(level is not None and not math.isfinite(level) for level in levels):
        raise ValueError('Loudness levels must be finite or null for digital silence')
    if not levels:
        return dict(mean_rms=None, max_rms=None, mean_rms_dbfs=None, max_rms_dbfs=None)
    rms = np.array([10 ** (level / 20) if level is not None else 0 for level in levels])
    mean = float(np.average(rms, weights=durations))
    maximum = float(rms.max())
    return dict(mean_rms=round(mean, 10), max_rms=round(maximum, 10),
                mean_rms_dbfs=round(20 * math.log10(mean), 2) if mean > 0 else None,
                max_rms_dbfs=round(20 * math.log10(maximum), 2) if maximum > 0 else None)


def estimate_pitch(audio: np.ndarray, sample_rate: int, min_hz: float = 50, max_hz: float = 1000) -> dict:
    missing = dict(pitch_hz=None, pitch_confidence=None, voiced_frame_fraction=0.0)
    if sample_rate <= 0 or not 0 < min_hz < max_hz <= 1000:
        raise ValueError('Pitch search requires 0 < min < max <= 1000 Hz and a positive sample rate')
    signal = np.asarray(audio, dtype=np.float64)
    if signal.ndim != 1 or not np.isfinite(signal).all():
        raise ValueError('Pitch input must be finite mono audio')
    if len(signal) / sample_rate < 0.08 or not len(signal) or np.ptp(signal) <= 1e-12:
        return missing
    if sample_rate != 4000:
        divisor = math.gcd(sample_rate, 4000)
        signal = resample_poly(signal, 4000 // divisor, sample_rate // divisor)
    frame_size, hop, rate = 320, 160, 4000
    frames = np.lib.stride_tricks.sliding_window_view(signal, frame_size)[::hop].copy()
    frames -= frames.mean(axis=1, keepdims=True)
    frames *= np.hanning(frame_size)
    transform = np.fft.rfft(frames, n=1024, axis=1)
    corr = np.fft.irfft(np.abs(transform) ** 2, n=1024, axis=1)[:, :frame_size]
    prefix = np.concatenate((np.zeros((len(frames), 1)), np.cumsum(frames ** 2, axis=1)), axis=1)
    lags = np.arange(frame_size)
    denominator = np.sqrt(np.maximum(prefix[:, frame_size - lags] * (prefix[:, -1:] - prefix[:, lags]), 0))
    corr = np.divide(corr, denominator, out=np.zeros_like(corr), where=denominator > 1e-20)
    low, high = math.ceil(rate / max_hz), min(math.floor(rate / min_hz), frame_size - 2)
    estimates, confidence = [], []
    for curve in corr:
        peaks = find_peaks(curve)[0]
        peaks = peaks[(peaks >= low) & (peaks <= high)]
        if not len(peaks):
            continue
        best = float(np.max(curve[peaks]))
        if best < 0.6:
            continue
        lag = int(peaks[curve[peaks] >= max(0.6, best * 0.9)][0])
        left, center, right = curve[lag - 1:lag + 2]
        curvature = left - 2 * center + right
        offset = float(np.clip(0.5 * (left - right) / curvature, -0.5, 0.5)) if abs(curvature) > 1e-12 else 0
        hz = rate / (lag + offset)
        if min_hz <= hz <= max_hz:
            estimates.append(hz)
            confidence.append(float(np.clip(center, 0, 1)))
    voiced = len(estimates) / len(frames)
    if len(estimates) < 3 or voiced < 0.5:
        return dict(missing, voiced_frame_fraction=round(voiced, 3))
    return dict(pitch_hz=round(float(np.median(estimates)), 3),
                pitch_confidence=round(float(np.median(confidence)), 3),
                voiced_frame_fraction=round(voiced, 3))


def compare_gap_loudness(timeline: list[dict], events: list[dict], gaps: list[dict],
                         context_seconds: float = 3, rise_threshold_db: float = 3) -> list[dict]:
    if not math.isfinite(context_seconds) or context_seconds <= 0 or not math.isfinite(rise_threshold_db) or rise_threshold_db < 0:
        raise ValueError('Invalid post-gap loudness settings')
    ordered_events = sorted(events, key=lambda event: event['start_seconds'])
    event_starts = [event['start_seconds'] for event in ordered_events]
    starts = [row['start_seconds'] for row in timeline]

    def context_level(start, end):
        levels, durations = [], []
        left = max(0, bisect_right(starts, start) - 1)
        right = bisect_left(starts, end)
        for row in timeline[left:right]:
            overlap = min(end, row['start_seconds'] + row['duration_seconds']) - max(start, row['start_seconds'])
            if overlap > 0 and row.get('prediction') == 'snore':
                levels.append(row['rms_dbfs'])
                durations.append(overlap)
        return loudness_statistics(levels, durations)['mean_rms_dbfs']

    results = []
    for gap in gaps:
        index = bisect_right(event_starts, gap['start_seconds']) - 1
        if not 0 <= index < len(ordered_events) - 1:
            continue
        before, after = ordered_events[index:index + 2]
        if abs(before['end_seconds'] - gap['start_seconds']) > 0.001 or abs(after['start_seconds'] - gap['end_seconds']) > 0.001:
            continue  # Do not bridge intervening speech/noise or an unmeasured join.
        start = max(before['start_seconds'], before['end_seconds'] - context_seconds)
        end = min(after['end_seconds'], after['start_seconds'] + context_seconds)
        pre, post = context_level(start, before['end_seconds']), context_level(after['start_seconds'], end)
        change = round(post - pre, 2) if pre is not None and post is not None else None
        results.append(dict(start_seconds=round(start, 3), end_seconds=round(end, 3), duration_seconds=round(end-start, 3),
                            gap_start_seconds=gap['start_seconds'], gap_end_seconds=gap['end_seconds'],
                            before_rms_dbfs=pre, after_rms_dbfs=post, rise_db=change,
                            is_louder=change is not None and change >= rise_threshold_db))
    return results


def rhythm_autocorrelation(audio: np.ndarray, sample_rate: int, timeline: list[dict] | None = None) -> dict:
    if sample_rate < 10:
        raise ValueError('Rhythm analysis requires a sample rate of at least 10 Hz')
    signal = np.asarray(audio)
    if signal.ndim != 1 or not np.isfinite(signal).all():
        raise ValueError('Rhythm input must be finite mono audio')
    block = round(sample_rate / 10)
    count = len(signal) // block
    envelope = np.empty(count)
    for start in range(0, count, 512):
        frames = signal[start*block:min(count, start+512)*block].reshape(-1, block).astype(np.float64)
        envelope[start:start+len(frames)] = np.sqrt(np.mean(frames ** 2, axis=1))
    envelope_rate = sample_rate / block
    if timeline is not None:
        mask = np.zeros(count, dtype=bool)
        for row in timeline:
            if row.get('prediction') == 'snore':
                first = max(0, math.ceil(row['start_seconds'] * envelope_rate))
                end = min(count, math.ceil((row['start_seconds'] + row['duration_seconds']) * envelope_rate))
                mask[first:end] = True
        envelope[~mask] = 0
    result = dict(dominant_period_seconds=None, autocorrelation_strength=None, analyzed_seconds=round(count/envelope_rate, 3),
                  envelope_rate_hz=round(envelope_rate, 6), lags_seconds=[], correlation=[],
                  method='normalized autocorrelation of 10 Hz RMS envelope' + (' inside snoring-positive windows' if timeline is not None else ''),
                  minimum_strength=0.3, minimum_cycles=3)
    if count < 10 * envelope_rate:
        return result
    envelope -= envelope.mean()
    if np.max(np.abs(envelope)) <= 1e-12:
        return result
    maximum_lag = min(round(15 * envelope_rate), count // 3)
    size = 1 << (2*count - 1).bit_length()
    transform = np.fft.rfft(envelope, n=size)
    corr = np.fft.irfft(np.abs(transform) ** 2, n=size)[:maximum_lag+1]
    lags = np.arange(maximum_lag+1)
    prefix = np.concatenate(([0], np.cumsum(envelope ** 2)))
    denominator = np.sqrt(np.maximum(prefix[count-lags] * (prefix[-1] - prefix[lags]), 0))
    corr = np.clip(np.divide(corr, denominator, out=np.zeros_like(corr), where=denominator > 1e-20), -1, 1)
    peaks = find_peaks(corr)[0]
    peaks = peaks[(peaks >= math.ceil(envelope_rate)) & (corr[peaks] >= 0.3)]
    if len(peaks):
        best = float(np.max(corr[peaks]))
        lag = int(peaks[corr[peaks] >= best * 0.9][0])
        result.update(dominant_period_seconds=round(lag/envelope_rate, 3), autocorrelation_strength=round(float(corr[lag]), 4))
    result.update(lags_seconds=np.round(lags/envelope_rate, 3).tolist(), correlation=np.round(corr, 4).tolist())
    return result


def bounded_spectrogram(audio: np.ndarray, sample_rate: int, max_columns: int = 600) -> dict:
    if sample_rate <= 0 or not isinstance(max_columns, int) or max_columns < 1:
        raise ValueError('Invalid spectrogram settings')
    signal = np.asarray(audio)
    if signal.ndim != 1 or not np.isfinite(signal).all():
        raise ValueError('Spectrogram input must be finite mono audio')
    result = dict(status='insufficient_duration', values_db=[], frequencies_hz=[], time_edges_seconds=[],
                  units='dBFS/Hz', fft_samples=512, hop_samples=256, aggregation='mean power per time/frequency bin')
    if len(signal) < 512:
        return result
    frames = np.lib.stride_tricks.sliding_window_view(signal, 512)[::256]
    columns = min(max_columns, len(frames))
    duration = len(signal) / sample_rate
    sums, counts = np.zeros((columns, 128)), np.zeros(columns)
    window = np.hanning(512)
    scale = np.sum(window ** 2) * sample_rate
    for start in range(0, len(frames), 256):
        batch = frames[start:start+256].astype(np.float64)
        batch -= batch.mean(axis=1, keepdims=True)
        power = np.abs(np.fft.rfft(batch * window, axis=1)) ** 2 / scale
        power[:, 1:-1] *= 2  # One-sided power spectral density; Nyquist is not doubled.
        reduced = power[:, 1:].reshape(len(batch), 128, 2).mean(axis=2)
        times = ((np.arange(start, start+len(batch))*256 + 256) / sample_rate)
        indices = np.minimum(columns-1, np.floor(times/duration*columns).astype(int))
        np.add.at(sums, indices, reduced)
        np.add.at(counts, indices, 1)
    # Empty time bins have no measured spectral data, represented as null rather than silence.
    mean = np.divide(sums, counts[:, None], out=np.zeros_like(sums), where=counts[:, None] > 0)
    db = np.maximum(-120, 10*np.log10(np.maximum(mean, 1e-12)))
    values = [[round(float(db[t, f]), 1) if counts[t] else None for t in range(columns)] for f in range(128)]
    result.update(status='available', values_db=values,
                  frequencies_hz=np.round((np.arange(128)*2+1.5)*sample_rate/512, 3).tolist(),
                  time_edges_seconds=np.round(np.linspace(0, duration, columns+1), 6).tolist(),
                  sample_rate=sample_rate, floor_db=-120)
    return result


def rhythm_over_time(audio: np.ndarray, sample_rate: int, timeline: list[dict],
                     window_seconds: int = 60, step_seconds: int = 30) -> list[dict]:
    """Local rhythm estimates without crossing recording boundaries."""
    if not isinstance(window_seconds, int) or not isinstance(step_seconds, int) or window_seconds < 10 or step_seconds <= 0:
        raise ValueError('Use rhythm windows of at least 10 seconds and a positive step')
    duration = len(audio) / sample_rate
    starts = [row['start_seconds'] for row in timeline]
    results = []
    for start in range(0, math.ceil(duration), step_seconds):
        end = min(duration, start + window_seconds)
        if end - start < 10:
            continue
        selected = []
        first = max(0, bisect_right(starts, start) - 1)
        for row in timeline[first:bisect_left(starts, end)]:
            left, right = max(start, row['start_seconds']), min(end, row['start_seconds'] + row['duration_seconds'])
            if right > left:
                selected.append(dict(row, start_seconds=left-start, duration_seconds=right-left))
        result = rhythm_autocorrelation(audio[round(start*sample_rate):round(end*sample_rate)], sample_rate, selected)
        results.append(dict(start_seconds=start, duration_seconds=round(end-start, 3),
                            dominant_period_seconds=result['dominant_period_seconds'],
                            autocorrelation_strength=result['autocorrelation_strength']))
    return results
