"""Train an audio-only apnea/hypopnea window baseline from clinical label manifests."""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import warnings

import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, brier_score_loss
from sklearn.preprocessing import StandardScaler

from apnea_research import FEATURE_NAMES, SAMPLE_RATE, WINDOW_SECONDS, collect_features, load_manifest, save_model


def checked_predictions(labels, scores):
    y, p = np.asarray(labels), np.asarray(scores, dtype=np.float64)
    if (y.ndim != 1 or p.shape != y.shape or not len(y) or not set(y).issubset({0, 1})
            or not np.isfinite(p).all() or np.any((p < 0) | (p > 1))):
        raise ValueError('Expected binary labels and equally sized finite scores in [0, 1]')
    return y, p


def choose_threshold(validation_labels: np.ndarray, validation_scores: np.ndarray) -> float:
    y, scores = checked_predictions(validation_labels, validation_scores)
    if set(y) != {0, 1}:
        raise ValueError('Validation requires both classes')
    candidates = np.unique(np.clip(np.concatenate(([0.5], scores)), 1e-9, 1 - 1e-9))
    order = np.argsort(scores, kind='stable')
    ordered_scores, ordered_labels = scores[order], y[order]
    positive_prefix = np.concatenate(([0], np.cumsum(ordered_labels == 1)))
    negative_prefix = np.concatenate(([0], np.cumsum(ordered_labels == 0)))
    first_positive = np.searchsorted(ordered_scores, candidates, side='left')
    recall = (positive_prefix[-1] - positive_prefix[first_positive]) / positive_prefix[-1]
    specificity = negative_prefix[first_positive] / negative_prefix[-1]
    balanced = (recall + specificity) / 2
    best = np.lexsort((candidates, specificity, balanced))[-1]
    return float(candidates[best])


def evaluate_windows(labels: np.ndarray, scores: np.ndarray, threshold: float, people: list[str]) -> dict:
    y, p = checked_predictions(labels, scores)
    if len(people) != len(y) or not np.isfinite(threshold) or not 0 < threshold < 1:
        raise ValueError('Invalid metric inputs')
    predicted = p >= threshold
    tp, fp = int(np.sum(predicted & (y == 1))), int(np.sum(predicted & (y == 0)))
    tn, fn = int(np.sum(~predicted & (y == 0))), int(np.sum(~predicted & (y == 1)))
    result = dict(windows=len(y), people=len(set(people)), true_positive=tp, false_positive=fp,
                  true_negative=tn, false_negative=fn,
                  precision=tp / (tp + fp) if tp + fp else None,
                  recall=tp / (tp + fn) if tp + fn else None,
                  specificity=tn / (tn + fp) if tn + fp else None,
                  roc_auc=float(roc_auc_score(y, p)) if len(set(y)) == 2 else None,
                  brier_score=float(brier_score_loss(y, p)),
                  false_positive_windows_per_scored_hour=fp / (len(y) * WINDOW_SECONDS / 3600),
                  scored_hours=len(y) * WINDOW_SECONDS / 3600)
    # Per-person results expose uneven performance and undefined single-class metrics.
    if len(set(people)) > 1:
        result['per_person'] = {}
        identities = np.asarray(people)
        for person in sorted(set(people)):
            selected = identities == person
            result['per_person'][person] = evaluate_windows(y[selected], p[selected], threshold, [person] * int(selected.sum()))
    return result


def fit_baseline(rows: list[dict], features: np.ndarray, directory: Path, *, synthetic: bool,
                 manifest_sha256: str) -> dict:
    x = np.asarray(features, dtype=np.float64)
    if x.shape != (len(rows), len(FEATURE_NAMES)) or not np.isfinite(x).all():
        raise ValueError('Feature matrix has incompatible dimensions or non-finite values')
    labels = np.asarray([r['label'] for r in rows])
    split_ids = {split: np.asarray([i for i, r in enumerate(rows) if r['split'] == split])
                 for split in ('train', 'validation', 'test')}
    owners = {}
    for row in rows:
        if row['person_id'] in owners and owners[row['person_id']] != row['split']:
            raise ValueError('A person crosses dataset splits')
        owners[row['person_id']] = row['split']
    for split, ids in split_ids.items():
        if len({rows[i]['person_id'] for i in ids}) < 2 or set(labels[ids]) != {0, 1}:
            raise ValueError(f'{split} requires two people and both classes')
    train = split_ids['train']
    counts = Counter(rows[i]['person_id'] for i in train)
    weights = np.asarray([1 / counts[rows[i]['person_id']] for i in train])
    weights *= len(weights) / weights.sum()
    scaler = StandardScaler().fit(x[train], sample_weight=weights)
    classifier = LogisticRegression(C=1.0, max_iter=2000, solver='lbfgs', random_state=42)
    with warnings.catch_warnings():
        warnings.simplefilter('error', ConvergenceWarning)
        classifier.fit(scaler.transform(x[train]), labels[train], sample_weight=weights)
    scores = {split: classifier.predict_proba(scaler.transform(x[ids]))[:, 1] for split, ids in split_ids.items()}
    threshold = choose_threshold(labels[split_ids['validation']], scores['validation'])
    metrics = {f'{split}_metrics': evaluate_windows(labels[ids], scores[split], threshold,
               [rows[i]['person_id'] for i in ids]) for split, ids in split_ids.items()}
    card = dict(schema_version=1, feature_version=1, feature_names=FEATURE_NAMES,
                window_seconds=WINDOW_SECONDS, sample_rate=SAMPLE_RATE, threshold=threshold,
                validation_status='synthetic_only' if synthetic else 'research_only',
                clinical_validation=False, target='apnea_hypopnea_window', input_modality='ambient_microphone_audio',
                algorithm='patient-weighted StandardScaler + logistic regression',
                threshold_selection='maximum validation window balanced accuracy; ties favor specificity',
                manifest_sha256=manifest_sha256, patient_splits={split: sorted({rows[i]['person_id'] for i in ids})
                                                              for split, ids in split_ids.items()},
                limitations=['No externally validated phone/bedroom performance',
                             'Raw window scores are not calibrated personal risk probabilities',
                             'Minimum dataset checks do not establish clinical validity'], **metrics)
    save_model(directory, scaler.mean_, scaler.scale_, classifier.coef_[0], float(classifier.intercept_[0]), card)
    return dict(validation_status=card['validation_status'], clinical_validation=False, threshold=threshold,
                **metrics, test_scores=scores['test'])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--out', type=Path, required=True, help='New directory for the research model and model card')
    parser.add_argument('--synthetic-test-data', action='store_true', help='Plumbing tests only; exports a model that refuses user audio')
    args = parser.parse_args()
    try:
        rows = load_manifest(args.manifest, synthetic=args.synthetic_test_data)
        features = collect_features(rows)
        result = fit_baseline(rows, features, args.out, synthetic=args.synthetic_test_data,
                              manifest_sha256=sha256(args.manifest.read_bytes()).hexdigest())
    except (OSError, ValueError, ConvergenceWarning) as error:
        parser.error(str(error))
    result.pop('test_scores')
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
