# Snore duration score evidence

The user requested a numeric description of snoring without evaluating sleep or medical risk. The chosen score is the complement of detected snore duration percentage, using actual recorded duration as denominator.

RED: `node tests/test_snore_score.cjs` ran and failed because `snoreScore` was missing. GREEN: the same target passed after implementation, covering 0/100 boundaries, a partial-length recording, equal ratios across different recording lengths, missing fields, invalid durations and nonfinite input. Existing measurement and sleep-audio UI calculation checks also passed; `node --check web/app.js` passed.

Browser verification: loaded the eight-hour synthetic fixture. The comparison table and detail card displayed 36.7% detected snoring and 63.3/100, with the formula and nonmedical interpretation visible. This is a display check, not a real-night model evaluation. JSON/CSV export fields were added; automated browser download interception timed out, so download completion was not verified during this check.

No Git checkpoints were applicable because the project folder is not a Git repository. This change does not add a validated loudness, rhythm or apnea score.
