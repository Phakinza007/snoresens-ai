"""Audio-only apnea/hypopnea window research; never a personal risk calculator."""
from __future__ import annotations

import argparse
import csv
from functools import lru_cache
from hashlib import sha256
import json
from math import gcd
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.fft import dct
from scipy.signal import stft, resample_poly
from scipy.special import expit

SAMPLE_RATE = 16_000
WINDOW_SECONDS = 30
FEATURE_NAMES = ([f'mfcc_{i:02d}_mean' for i in range(13)]
                 + [f'mfcc_{i:02d}_std' for i in range(13)]
                 + [f'log_rms_second_{i:02d}' for i in range(30)]
                 + [f'zcr_second_{i:02d}' for i in range(30)])
MODEL_NAME = 'apnea_research'


@lru_cache(maxsize=1)
def mel_filters() -> np.ndarray:
    frequencies = np.fft.rfftfreq(512, 1 / SAMPLE_RATE)
    edges = 700 * (10 ** (np.linspace(0, 2595 * np.log10(1 + 8000 / 700), 42) / 2595) - 1)
    filters = []
    for left, center, right in zip(edges[:-2], edges[1:-1], edges[2:]):
        filters.append(np.maximum(0, np.minimum((frequencies - left) / (center - left),
                                               (right - frequencies) / (right - center))))
    return np.asarray(filters, dtype=np.float64)


def audio_features(audio: np.ndarray) -> np.ndarray:
    samples = np.asarray(audio, dtype=np.float64)
    if samples.ndim != 1 or len(samples) != SAMPLE_RATE * WINDOW_SECONDS or not np.isfinite(samples).all():
        raise ValueError('Features require exactly 30 seconds of finite mono 16 kHz audio')
    _, _, spectrum = stft(samples, fs=SAMPLE_RATE, nperseg=512, noverlap=352,
                          nfft=512, boundary=None, padded=False)
    mel_power = mel_filters() @ np.abs(spectrum) ** 2
    mfcc = dct(np.log(np.maximum(mel_power, 1e-12)), type=2, axis=0, norm='ortho')[:13]
    seconds = samples.reshape(WINDOW_SECONDS, SAMPLE_RATE)
    log_rms = np.log(np.maximum(np.sqrt(np.mean(seconds ** 2, axis=1)), 1e-8))
    zcr = np.mean(np.diff(np.signbit(seconds), axis=1), axis=1)
    result = np.concatenate((mfcc.mean(axis=1), mfcc.std(axis=1), log_rms, zcr))
    if result.shape != (len(FEATURE_NAMES),) or not np.isfinite(result).all():
        raise ValueError('Audio feature extraction failed')
    return result


def load_manifest(path: Path, *, synthetic: bool = False) -> list[dict]:
    required = {'audio_path', 'person_id', 'night_id', 'start_seconds', 'duration_seconds',
                'label', 'split', 'reference', 'alignment_verified'}
    with path.open(newline='', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file)
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f'Manifest requires columns: {", ".join(sorted(required))}')
        rows = list(reader)
    if not rows:
        raise ValueError('Manifest contains no windows')
    person_splits, night_owners, source_owners, intervals = {}, {}, {}, {}
    for index, row in enumerate(rows, 2):
        try:
            for key in required:
                row[key] = row[key].strip()
            if not row['person_id'] or not row['night_id'] or not row['audio_path']:
                raise ValueError('Audio, person, and night identifiers are required')
            row['start_seconds'] = float(row['start_seconds'])
            row['duration_seconds'] = float(row['duration_seconds'])
            if row['label'] not in ('0', '1'):
                raise ValueError('Label must be 0 or 1')
            row['label'] = int(row['label'])
            if (not np.isfinite(row['start_seconds']) or row['start_seconds'] < 0
                    or row['duration_seconds'] != WINDOW_SECONDS):
                raise ValueError('Use nonnegative start times and full 30-second windows')
            if row['split'] not in ('train', 'validation', 'test'):
                raise ValueError('Split must be train, validation, or test')
            references = {'SYNTHETIC'} if synthetic else {'PSG', 'HSAT'}
            if row['reference'] not in references or row['alignment_verified'].lower() != 'true':
                raise ValueError('Confirmed audio alignment and PSG/HSAT reference labels are required')
            audio_path = Path(row['audio_path'])
            row['audio_path'] = str((path.parent / audio_path).resolve() if not audio_path.is_absolute() else audio_path.resolve())
            person, night, source, split = row['person_id'], row['night_id'], row['audio_path'], row['split']
            if person in person_splits and person_splits[person] != split:
                raise ValueError('A person crosses dataset splits')
            if night in night_owners and night_owners[night] != (person, split):
                raise ValueError('A night has conflicting person/split ownership')
            if source in source_owners and source_owners[source] != (person, night, split):
                raise ValueError('A recording has conflicting person/night/split ownership')
            person_splits[person], night_owners[night], source_owners[source] = split, (person, split), (person, night, split)
            intervals.setdefault(source, []).append((row['start_seconds'], row['start_seconds'] + WINDOW_SECONDS))
        except (ValueError, TypeError, AttributeError) as error:
            raise ValueError(f'Manifest row {index}: {error}') from error
    for source, windows in intervals.items():
        ordered = sorted(windows)
        if any(a[1] > b[0] + 1e-6 for a, b in zip(ordered, ordered[1:])):
            raise ValueError(f'Overlapping or duplicate windows in {source}')
    for split in ('train', 'validation', 'test'):
        selected = [row for row in rows if row['split'] == split]
        if len({row['person_id'] for row in selected}) < 2 or {row['label'] for row in selected} != {0, 1}:
            raise ValueError(f'{split} requires at least two people and both labels')
    return rows


def read_window(path: Path, start_seconds: float, duration: int = WINDOW_SECONDS) -> np.ndarray:
    with sf.SoundFile(path) as file:
        start = round(start_seconds * file.samplerate)
        count = duration * file.samplerate
        if start + count > len(file):
            raise ValueError(f'Window exceeds audio duration: {path}, start={start_seconds}')
        file.seek(start)
        audio = file.read(count, dtype='float32', always_2d=True).mean(axis=1)
        rate = file.samplerate
    if rate != SAMPLE_RATE:
        divisor = gcd(rate, SAMPLE_RATE)
        audio = resample_poly(audio, SAMPLE_RATE // divisor, rate // divisor)
    if not np.isfinite(audio).all():
        raise ValueError(f'Non-finite audio in {path}')
    return np.asarray(audio, dtype=np.float32)


def collect_features(rows: list[dict]) -> np.ndarray:
    features, seen = [], {}
    for row in rows:
        audio = read_window(Path(row['audio_path']), row['start_seconds'])
        if np.max(np.abs(audio)) <= 1e-12:
            raise ValueError('Digital-silence training window must be reviewed as missing/uncertain signal')
        digest = sha256(audio.tobytes()).hexdigest()
        if digest in seen and seen[digest] != row['split']:
            raise ValueError('Exact audio duplicate crosses dataset splits')
        seen[digest] = row['split']
        features.append(audio_features(audio))
    return np.asarray(features, dtype=np.float64)


def save_model(directory: Path, mean: np.ndarray, scale: np.ndarray, coefficient: np.ndarray,
               intercept: float, config: dict, *, overwrite: bool = False) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    weights = directory / f'{MODEL_NAME}.npz'
    metadata = directory / f'{MODEL_NAME}.json'
    if not overwrite and (weights.exists() or metadata.exists()):
        raise FileExistsError('Choose a new output directory; existing research model will not be overwritten')
    np.savez(weights, mean=mean, scale=scale, coefficient=coefficient, intercept=np.asarray([intercept]))
    card = dict(config, weights_sha256=sha256(weights.read_bytes()).hexdigest())
    metadata.write_text(json.dumps(card, indent=2, allow_nan=False) + '\n', encoding='utf-8')


class ResearchModel:
    def __init__(self, directory: Path, *, allow_synthetic: bool = False):
        self.config = json.loads((directory / f'{MODEL_NAME}.json').read_text(encoding='utf-8'))
        card = self.config
        if (card.get('schema_version') != 1 or card.get('feature_version') != 1
                or card.get('feature_names') != FEATURE_NAMES or card.get('window_seconds') != WINDOW_SECONDS
                or card.get('sample_rate') != SAMPLE_RATE or card.get('target') != 'apnea_hypopnea_window'
                or card.get('input_modality') != 'ambient_microphone_audio' or card.get('clinical_validation') is not False
                or card.get('validation_status') not in ('research_only', 'synthetic_only')):
            raise ValueError('Incompatible or incomplete apnea research model card')
        if card['validation_status'] == 'synthetic_only' and not allow_synthetic:
            raise ValueError('Synthetic test model cannot analyze user recordings')
        threshold = card.get('threshold')
        if not isinstance(threshold, (int, float)) or not np.isfinite(threshold) or not 0 < threshold < 1:
            raise ValueError('Invalid review threshold')
        weights = directory / f'{MODEL_NAME}.npz'
        if weights.stat().st_size > 1_000_000 or sha256(weights.read_bytes()).hexdigest() != card.get('weights_sha256'):
            raise ValueError('Research model weights failed integrity check')
        with np.load(weights, allow_pickle=False) as arrays:
            self.mean, self.scale, self.coefficient = (arrays[key].astype(np.float64) for key in ('mean', 'scale', 'coefficient'))
            intercept = arrays['intercept']
        if (any(value.shape != (len(FEATURE_NAMES),) or not np.isfinite(value).all()
                for value in (self.mean, self.scale, self.coefficient))
                or np.any(self.scale <= 0) or intercept.shape != (1,) or not np.isfinite(intercept).all()):
            raise ValueError('Invalid research model arrays')
        self.intercept = float(intercept[0])

    def score(self, features: np.ndarray) -> float:
        if features.shape != self.mean.shape or not np.isfinite(features).all():
            raise ValueError('Invalid research features')
        return float(expit(np.dot((features - self.mean) / self.scale, self.coefficient) + self.intercept))

    def analyze(self, path: Path) -> dict:
        windows, segments = [], []
        with sf.SoundFile(path) as file:
            if not len(file):
                raise ValueError('The WAV file contains no audio')
            seconds = len(file) / file.samplerate
        for start in range(0, int(np.ceil(seconds)), WINDOW_SECONDS):
            duration = min(WINDOW_SECONDS, seconds - start)
            row = dict(start_seconds=start, duration_seconds=round(duration, 6), model_score=None, flagged_for_review=False)
            if duration < WINDOW_SECONDS - 1e-6:
                row['status'] = 'insufficient_duration'
            else:
                audio = read_window(path, start)
                if np.max(np.abs(audio)) <= 1e-12:
                    row['status'] = 'insufficient_signal'
                else:
                    score = self.score(audio_features(audio))
                    row.update(status='scored', model_score=round(score, 6), flagged_for_review=score >= self.config['threshold'])
            if row['flagged_for_review']:
                if segments and segments[-1]['end_seconds'] == start:
                    segments[-1]['end_seconds'] = start + WINDOW_SECONDS
                else:
                    segments.append(dict(start_seconds=start, end_seconds=start + WINDOW_SECONDS))
            windows.append(row)
        return dict(status='research_only', input_modality='audio_only', risk_percent=None,
                    clinical_validation=False, target=self.config['target'], threshold=self.config['threshold'],
                    recording_seconds=seconds, scored_seconds=sum(r['duration_seconds'] for r in windows if r['status'] == 'scored'),
                    score_note='Raw window-model scores; not calibrated personal risk. Review intervals are not apnea counts.',
                    windows=windows, review_segments=segments)


def model_status(directory: Path) -> dict:
    paths = [directory / f'{MODEL_NAME}.{extension}' for extension in ('json', 'npz')]
    if not any(path.exists() for path in paths):
        return dict(status='not_trained', input_modality='audio_only', risk_percent=None,
                    clinical_validation=False, reason='No sleep-study-labeled audio model has been trained')
    try:
        model = ResearchModel(directory, allow_synthetic=True)
        return dict(status=model.config['validation_status'], input_modality='audio_only',
                    risk_percent=None, clinical_validation=False)
    except (OSError, ValueError, KeyError, TypeError) as error:
        return dict(status='invalid_model', input_modality='audio_only', risk_percent=None,
                    clinical_validation=False, reason=str(error))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('wav', type=Path, nargs='?')
    parser.add_argument('--models', type=Path, default=Path('artifacts/apnea'))
    parser.add_argument('--status', action='store_true')
    args = parser.parse_args()
    if args.status:
        output = model_status(args.models)
    elif args.wav:
        try:
            output = ResearchModel(args.models).analyze(args.wav)
        except (OSError, ValueError, KeyError, TypeError) as error:
            parser.error(str(error))
    else:
        parser.error('Supply a WAV file or --status')
    print(json.dumps(output, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
