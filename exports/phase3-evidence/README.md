# Phase 3 slide assets

Generated 14 Nov 2026 with `docs/prepare_phase3_evidence.py`. PNG files are high-resolution; SVG files are vector.

- 01: deployed web snore classifier confusion matrix (saved result).
- 02: both snore confusion matrices side by side (saved results).
- 03: snore model comparison table; CSV is also supplied.
- 04–05: supplementary cough task, freshly reevaluated using its saved 42-file test list and threshold.

Snore results are NOT freshly reevaluated. Both report 149 test clips, but the missing original split manifest prevents verification of exact shared test identities. Do not present these as Phase 2 → Phase 3 improvement.
Cough is a different task/dataset and must not be ranked against snore classifiers. The cough rerun confirms the saved paths and currently available audio, but original audio hashes were not saved.
Rows of all confusion matrices = actual labels; columns = predictions. Class 0 is non-snore/other; class 1 is snore/cough.
No snore ROC curve is generated: original per-example scores are unavailable.
Full fresh cough evidence, predictions, split manifest, hashes and data audit: `results/phase3-evidence/`.
