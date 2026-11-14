"""Train a preliminary cough-vs-other TFLite head on extracted Coswara WAVs.

Coswara recordings are prompted clips, not timestamped cough events. The
resulting model must not be interpreted as a validated bedside cough counter.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
import tensorflow as tf
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.model_selection import GroupShuffleSplit

from predict import FRAME_SAMPLES, YAMNET_SAMPLES, interpreter, load_wave


SEED = 42
COUGH = {"cough-heavy.wav", "cough-shallow.wav"}
OTHER = {
    "breathing-deep.wav", "breathing-shallow.wav",
    "counting-fast.wav", "counting-normal.wav",
}


def quality_scores(folder: Path) -> dict[str, int]:
    scores = {}
    for csv_path in folder.glob("*_labels.csv"):
        with csv_path.open(newline="", encoding="utf-8") as stream:
            for row in csv.DictReader(stream, skipinitialspace=True):
                scores[row["FILENAME"].strip()] = int(row["QUALITY"])
    return scores


def collect(root: Path, annotations: Path | None = None) -> tuple[list[Path], np.ndarray, np.ndarray]:
    paths, labels, groups = [], [], []
    scores = quality_scores(annotations) if annotations else None
    if annotations and not scores:
        raise ValueError(f"No quality labels found in {annotations}")
    for path in sorted(root.rglob("*.wav")):
        name = path.name.lower()
        if name not in COUGH | OTHER:
            continue
        # Coswara extracts to Extracted_data/<date>/<participant>/<type>.wav.
        if path.parent == root or path.parent.parent == root:
            raise ValueError(f"Expected participant folder above {path}")
        if scores is not None and scores.get(f"{path.parent.name}_{path.stem}", 0) < 1:
            continue
        paths.append(path)
        labels.append(int(name in COUGH))
        groups.append(path.parent.name)
    if not paths or set(labels) != {0, 1} or len(set(groups)) < 5:
        raise ValueError("Need cough and other WAVs from at least 5 participants")
    return paths, np.asarray(labels, dtype=np.int32), np.asarray(groups)


def split_people(labels: np.ndarray, groups: np.ndarray):
    ids = np.arange(len(labels))
    first = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=SEED)
    fit_ids, test_ids = next(first.split(ids, labels, groups))
    second = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=SEED + 1)
    train_local, val_local = next(
        second.split(fit_ids, labels[fit_ids], groups[fit_ids])
    )
    train_ids, val_ids = fit_ids[train_local], fit_ids[val_local]
    for a, b in [(train_ids, val_ids), (train_ids, test_ids), (val_ids, test_ids)]:
        assert not set(groups[a]) & set(groups[b])
    for name, selection in [("train", train_ids), ("validation", val_ids), ("test", test_ids)]:
        if set(labels[selection]) != {0, 1}:
            raise ValueError(f"{name} has one class; add more people or try another split seed")
    return train_ids, val_ids, test_ids


def loudest_window(audio: np.ndarray) -> np.ndarray:
    """Take the loudest 1 s from each prompted recording, avoiding long silence."""
    if len(audio) <= FRAME_SAMPLES:
        return np.pad(audio, (0, max(0, FRAME_SAMPLES - len(audio))))
    hop = FRAME_SAMPLES // 2
    starts = list(range(0, len(audio) - FRAME_SAMPLES + 1, hop))
    if starts[-1] != len(audio) - FRAME_SAMPLES:
        starts.append(len(audio) - FRAME_SAMPLES)
    start = max(starts, key=lambda s: float(np.mean(np.square(audio[s:s + FRAME_SAMPLES]))))
    return audio[start:start + FRAME_SAMPLES]


def extract_scores(paths: list[Path], base_path: Path) -> tuple[np.ndarray, list[str]]:
    base, input_index, output_index = interpreter(base_path, [YAMNET_SAMPLES], [1, 521])
    features, kept_paths = [], []
    for n, path in enumerate(paths, 1):
        try:
            audio = load_wave(path)
        except Exception as error:
            raise ValueError(f"Cannot read {path}: {error}") from error
        if not len(audio):
            raise ValueError(f"Empty audio: {path}")
        frame = loudest_window(audio)[:YAMNET_SAMPLES].astype(np.float32)
        base.set_tensor(input_index, frame)
        base.invoke()
        features.append(base.get_tensor(output_index).reshape(521))
        kept_paths.append(str(path))
        if n % 250 == 0:
            print(f"Features: {n}/{len(paths)}", flush=True)
    return np.stack(features), kept_paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True, help="Coswara Extracted_data folder")
    parser.add_argument("--annotations", type=Path,
                        help="Coswara quality-label folder; defaults to sibling annotations folder")
    parser.add_argument("--out", type=Path, default=Path("artifacts"))
    parser.add_argument("--epochs", type=int, default=30)
    args = parser.parse_args()
    tf.keras.utils.set_random_seed(SEED)
    if args.annotations and not args.annotations.is_dir():
        parser.error(f"Quality-label folder not found: {args.annotations}")
    annotations = args.annotations or args.data.parent / "annotations"
    paths, labels, groups = collect(args.data, annotations if annotations.is_dir() else None)
    train_ids, val_ids, test_ids = split_people(labels, groups)
    features, names = extract_scores(paths, args.out / "yamnet_base.tflite")

    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(521,)),
        tf.keras.layers.Dense(64, activation="relu"),
        tf.keras.layers.Dropout(0.2),
        tf.keras.layers.Dense(1, activation="sigmoid"),
    ])
    model.compile(optimizer=tf.keras.optimizers.Adam(1e-3),
                  loss="binary_crossentropy", metrics=["accuracy"])
    model.fit(features[train_ids], labels[train_ids],
              validation_data=(features[val_ids], labels[val_ids]),
              epochs=args.epochs, batch_size=32,
              class_weight={
                  c: len(train_ids) / (2 * int(np.sum(labels[train_ids] == c)))
                  for c in (0, 1)
              },
              callbacks=[tf.keras.callbacks.EarlyStopping(
                  monitor="val_loss", patience=5, restore_best_weights=True)],
              verbose=2)

    val_prob = model.predict(features[val_ids], verbose=0).ravel()
    thresholds = np.arange(0.20, 0.81, 0.01)
    threshold = float(max(thresholds, key=lambda t: f1_score(labels[val_ids], val_prob >= t)))
    test_prob = model.predict(features[test_ids], verbose=0).ravel()
    predicted = test_prob >= threshold
    args.out.mkdir(parents=True, exist_ok=True)
    model.save(args.out / "cough_score_head.keras")
    tflite_path = args.out / "cough_score_head.tflite"
    tflite_path.write_bytes(tf.lite.TFLiteConverter.from_keras_model(model).convert())
    head, input_index, output_index = interpreter(tflite_path, [1, 521], [1, 1])
    sample = features[test_ids[0]:test_ids[0] + 1].astype(np.float32)
    head.set_tensor(input_index, sample)
    head.invoke()
    if abs(float(head.get_tensor(output_index)[0, 0]) - float(model(sample)[0, 0])) > 1e-4:
        raise RuntimeError("Keras and TFLite predictions differ")

    metrics = {
        "source": "IISc Coswara prompted sound recordings",
        "class_0": "breathing or counting speech",
        "class_1": "prompted cough recording",
        "selection": "loudest one-second window per recording",
        "quality_filter": "manual quality 1 or 2" if annotations.is_dir() else "not available",
        "split": "participant-disjoint train/validation/test",
        "recordings": len(paths),
        "people": len(set(groups)),
        "train": len(train_ids), "validation": len(val_ids), "test": len(test_ids),
        "threshold": threshold,
        "test_confusion_matrix": confusion_matrix(labels[test_ids], predicted).tolist(),
        "test_report": classification_report(labels[test_ids], predicted,
                                             output_dict=True, zero_division=0),
        "limitations": "Prompted clips, no cough timestamps, no snore or bedside negatives; not a validated cough counter or health diagnosis.",
        "test_files": [names[i] for i in test_ids],
    }
    (args.out / "cough_metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in metrics.items() if k != "test_files"}, indent=2))


if __name__ == "__main__":
    main()
