"""Train research and mobile snore classifiers using frozen YAMNet.

Run in Google Colab or a Python environment with requirements.txt installed.
This model detects snoring sounds; it does not detect sleep apnea.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import kagglehub
import numpy as np
import soundfile as sf
import tensorflow as tf
from scipy.signal import resample_poly
from sklearn.metrics import classification_report, confusion_matrix, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split


SAMPLE_RATE = 16_000
SAMPLES = SAMPLE_RATE  # Kaggle clips are one second long.
DATASET = "tareqkhanemu/snoring"
YAMNET = "https://tfhub.dev/google/yamnet/1"
YAMNET_LITE = "google/yamnet/tfLite/classification-tflite"
SEED = 42


def label_for(path: Path) -> int | None:
    """The Khan dataset uses folder 0 for non-snore and 1 for snore."""
    for part in reversed(path.parts[:-1]):
        normalized = part.lower().replace("_", "-").replace(" ", "-")
        if normalized in {"0", "non-snoring", "no-snoring", "nonsnoring"}:
            return 0
        if normalized in {"1", "snoring", "snore"}:
            return 1
    return None


def load_audio(path: Path) -> np.ndarray:
    audio, rate = sf.read(path, dtype="float32", always_2d=True)
    audio = audio.mean(axis=1)
    if rate != SAMPLE_RATE:
        from math import gcd

        divisor = gcd(rate, SAMPLE_RATE)
        audio = resample_poly(audio, SAMPLE_RATE // divisor, rate // divisor)
    if len(audio) < SAMPLES:
        audio = np.pad(audio, (0, SAMPLES - len(audio)))
    return np.asarray(audio[:SAMPLES], dtype=np.float32)


def collect_data(root: Path) -> tuple[np.ndarray, np.ndarray, list[str], int]:
    clips: list[np.ndarray] = []
    labels: list[int] = []
    names: list[str] = []
    seen: set[str] = set()
    duplicates = 0
    for path in sorted(root.rglob("*.wav")):
        label = label_for(path)
        if label is None:
            continue
        audio = load_audio(path)
        digest = hashlib.sha256(audio.tobytes()).hexdigest()
        if digest in seen:
            duplicates += 1
            continue
        seen.add(digest)
        clips.append(audio)
        labels.append(label)
        names.append(str(path.relative_to(root)))
    if not clips or set(labels) != {0, 1}:
        raise ValueError(
            "Expected WAV files in class folders 0 and 1 (or non-snoring and snoring). "
            f"Found {len(clips)} usable clips and labels {set(labels)} under {root}."
        )
    return np.stack(clips), np.asarray(labels, dtype=np.int32), names, duplicates


def split_indices(labels: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    all_ids = np.arange(len(labels))
    train_ids, holdout_ids = train_test_split(
        all_ids, test_size=0.30, random_state=SEED, stratify=labels
    )
    val_ids, test_ids = train_test_split(
        holdout_ids,
        test_size=0.50,
        random_state=SEED,
        stratify=labels[holdout_ids],
    )
    return train_ids, val_ids, test_ids


def extract_embeddings(yamnet: object, clips: np.ndarray) -> np.ndarray:
    features = []
    for index, clip in enumerate(clips, start=1):
        _, embeddings, _ = yamnet(tf.convert_to_tensor(clip))
        features.append(tf.reduce_mean(embeddings, axis=0).numpy())
        if index % 100 == 0:
            print(f"YAMNet embeddings: {index}/{len(clips)}")
    return np.asarray(features, dtype=np.float32)


def extract_mobile_scores(model_path: Path, clips: np.ndarray) -> np.ndarray:
    interpreter = tf.lite.Interpreter(model_path=str(model_path))
    interpreter.allocate_tensors()
    input_info = interpreter.get_input_details()[0]
    output_info = interpreter.get_output_details()[0]
    if input_info["shape"].tolist() != [15600] or output_info["shape"].tolist() != [1, 521]:
        raise ValueError("Unexpected YAMNet TFLite input/output shapes")
    scores = []
    for index, clip in enumerate(clips, start=1):
        interpreter.set_tensor(input_info["index"], clip[:15600])
        interpreter.invoke()
        scores.append(interpreter.get_tensor(output_info["index"]).reshape(-1))
        if index % 100 == 0:
            print(f"Mobile YAMNet scores: {index}/{len(clips)}")
    return np.asarray(scores, dtype=np.float32)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, help="Local dataset root; omit to download from Kaggle")
    parser.add_argument("--out", type=Path, default=Path("artifacts"))
    parser.add_argument("--epochs", type=int, default=30)
    args = parser.parse_args()
    tf.keras.utils.set_random_seed(SEED)
    root = args.data or Path(kagglehub.dataset_download(DATASET))
    output = args.out.resolve()
    output.mkdir(parents=True, exist_ok=True)
    clips, labels, names, duplicates = collect_data(root)
    train_ids, val_ids, test_ids = split_indices(labels)
    print(f"Loaded {len(clips)} clips from {root}; removed {duplicates} exact duplicates")
    print("Split sizes:", len(train_ids), len(val_ids), len(test_ids))

    import tensorflow_hub as hub
    yamnet = hub.load(YAMNET)
    features = extract_embeddings(yamnet, clips)
    classifier = tf.keras.Sequential(
        [
            tf.keras.layers.Input(shape=(1024,)),
            tf.keras.layers.Dense(64, activation="relu"),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.Dense(1, activation="sigmoid"),
        ]
    )
    classifier.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
        loss="binary_crossentropy",
        metrics=[tf.keras.metrics.BinaryAccuracy(name="accuracy"), tf.keras.metrics.AUC(name="auc")],
    )
    classifier.fit(
        features[train_ids],
        labels[train_ids],
        validation_data=(features[val_ids], labels[val_ids]),
        epochs=args.epochs,
        batch_size=32,
        callbacks=[
            tf.keras.callbacks.EarlyStopping(
                monitor="val_loss", patience=5, restore_best_weights=True
            )
        ],
        verbose=2,
    )

    # Choose the decision threshold on validation data only.
    val_probability = classifier.predict(features[val_ids], verbose=0).ravel()
    candidates = np.arange(0.20, 0.81, 0.01)
    val_f1 = [
        2 * np.sum((val_probability >= t) & (labels[val_ids] == 1))
        / max(
            1,
            2 * np.sum((val_probability >= t) & (labels[val_ids] == 1))
            + np.sum((val_probability >= t) & (labels[val_ids] == 0))
            + np.sum((val_probability < t) & (labels[val_ids] == 1)),
        )
        for t in candidates
    ]
    threshold = float(candidates[int(np.argmax(val_f1))])
    probability = classifier.predict(features[test_ids], verbose=0).ravel()
    predicted = (probability >= threshold).astype(np.int32)
    report = classification_report(labels[test_ids], predicted, output_dict=True, zero_division=0)
    metrics = {
        "dataset": DATASET,
        "source_path": str(root),
        "classes": {"0": "non_snoring", "1": "snoring"},
        "samples": {"total": len(labels), "train": len(train_ids), "validation": len(val_ids), "test": len(test_ids)},
        "exact_duplicates_removed": duplicates,
        "decision_threshold": threshold,
        "test_auc": float(roc_auc_score(labels[test_ids], probability)),
        "test_confusion_matrix_rows_true_cols_predicted": confusion_matrix(labels[test_ids], predicted).tolist(),
        "test_classification_report": report,
        "limitation": "Source recording/person IDs are absent; random clip split may overestimate real-world performance.",
    }
    (output / "test_files.json").write_text(
        json.dumps([names[i] for i in test_ids], indent=2), encoding="utf-8"
    )
    classifier.save(output / "snore_head.keras")
    (output / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    # The official mobile YAMNet exposes 521 class scores rather than the
    # 1024-D embeddings. Train a separate head on exactly those mobile outputs.
    model_root = Path(kagglehub.model_download(YAMNET_LITE))
    model_files = list(model_root.rglob("*.tflite"))
    if len(model_files) != 1:
        raise ValueError(f"Expected one YAMNet TFLite model, found {model_files}")
    base_path = output / "yamnet_base.tflite"
    shutil.copy2(model_files[0], base_path)
    mobile_features = extract_mobile_scores(base_path, clips)
    mobile_head = tf.keras.Sequential(
        [
            tf.keras.layers.Input(shape=(521,)),
            tf.keras.layers.Dense(64, activation="relu"),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.Dense(1, activation="sigmoid"),
        ]
    )
    mobile_head.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
        loss="binary_crossentropy",
        metrics=["accuracy"],
    )
    mobile_head.fit(
        mobile_features[train_ids],
        labels[train_ids],
        validation_data=(mobile_features[val_ids], labels[val_ids]),
        epochs=args.epochs,
        batch_size=32,
        callbacks=[
            tf.keras.callbacks.EarlyStopping(
                monitor="val_loss", patience=5, restore_best_weights=True
            )
        ],
        verbose=2,
    )
    mobile_val = mobile_head.predict(mobile_features[val_ids], verbose=0).ravel()
    mobile_threshold = float(
        candidates[
            np.argmax([f1_score(labels[val_ids], mobile_val >= t) for t in candidates])
        ]
    )
    mobile_probability = mobile_head.predict(mobile_features[test_ids], verbose=0).ravel()
    mobile_predicted = (mobile_probability >= mobile_threshold).astype(np.int32)
    mobile_head.save(output / "snore_score_head.keras")
    head_path = output / "snore_score_head.tflite"
    head_path.write_bytes(tf.lite.TFLiteConverter.from_keras_model(mobile_head).convert())
    head_interpreter = tf.lite.Interpreter(model_path=str(head_path))
    head_interpreter.allocate_tensors()
    input_info = head_interpreter.get_input_details()[0]
    output_info = head_interpreter.get_output_details()[0]
    sample = mobile_features[test_ids[0] : test_ids[0] + 1]
    head_interpreter.set_tensor(input_info["index"], sample)
    head_interpreter.invoke()
    lite_probability = float(head_interpreter.get_tensor(output_info["index"]).ravel()[0])
    keras_probability = float(mobile_head(sample).numpy().ravel()[0])
    if abs(lite_probability - keras_probability) > 1e-4:
        raise RuntimeError("Mobile classifier TFLite output differs from Keras")
    mobile_metrics = {
        "source": DATASET,
        "base": YAMNET_LITE,
        "features": "521 YAMNet class scores",
        "samples": len(labels),
        "train": len(train_ids),
        "validation": len(val_ids),
        "test": len(test_ids),
        "threshold": mobile_threshold,
        "auc": float(roc_auc_score(labels[test_ids], mobile_probability)),
        "confusion_matrix": confusion_matrix(labels[test_ids], mobile_predicted).tolist(),
        "report": classification_report(
            labels[test_ids], mobile_predicted, output_dict=True, zero_division=0
        ),
        "base_bytes": base_path.stat().st_size,
        "head_bytes": head_path.stat().st_size,
        "keras_tflite_sample": {"keras": keras_probability, "tflite": lite_probability},
        "caveat": "Random clip split. Source person and recording IDs unavailable; no bedside phone validation.",
    }
    (output / "mobile_metrics.json").write_text(
        json.dumps(mobile_metrics, indent=2), encoding="utf-8"
    )
    print(json.dumps(mobile_metrics, indent=2))


if __name__ == "__main__":
    main()
