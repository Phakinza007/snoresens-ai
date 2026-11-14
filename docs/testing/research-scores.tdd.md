# Research-informed score criteria — TDD evidence

Journeys: show measured duration and interval criteria as separate numeric points; show unavailable PSS without inventing a value; preserve raw research-derived measures and export metadata. No plan file or Git checkpoints (workspace has no Git repository).

## RED / GREEN

- Initial `node tests/test_research_scores.cjs`: failed with missing research-scores.js.
- Added research measures, then added scoring assertions: RED `TypeError: Cannot read properties of undefined (reading score)` for duration_points.
- Implemented duration and interval-fraction points; GREEN `Research scores: PASS`. Implementation was subsequently integrated into measurements.js because the running server only serves known static files.
- Final command: `node --test --experimental-test-coverage tests/test_research_scores.cjs tests/test_web_measurements.cjs tests/test_snore_score.cjs tests/test_sleep_audio_web.cjs tests/test_audio_charts.cjs`. Result: 5 files passed, 0 failed. measurements.js line coverage 80.43%, branch coverage 83.16%, function coverage 90%. Existing audio-charts.js line coverage 46.30%; it is unchanged in this task.
- `node --check web/app.js`: passed.

| Guarantee | Evidence | Result |
|---|---|---|
| 25% detected snoring yields 75 duration points | test_research_scores.cjs | PASS |
| Two of four qualifying start intervals yield 50 pattern points | test_research_scores.cjs | PASS |
| Exact 10 and 100 second boundaries excluded | test_research_scores.cjs | PASS |
| All/no qualifying intervals yield 0/100; fewer than two events has no pattern score | test_research_scores.cjs | PASS |
| Missing, unordered, overlapping, nonfinite and out-of-bounds event data does not produce an interval index | test_research_scores.cjs | PASS |
| Adapted STII uses recording hours; PSS remains null | test_research_scores.cjs | PASS |
| Live 8-hour synthetic demo shows duration 63.3, pattern 90.0, adapted STII 60/h and PSS unavailable | Chrome UI, research-scores-ui.png | PASS |

Known gaps: no clinical validation, true sleep-time measurement, calibrated psychoacoustic measurements or fine-grained individual-snore validation. Pattern points are our transformation of the STII interval criterion, not the published STII score. No combined score. Export code includes metadata and score fields; actual downloaded CSV/JSON contents were not verified in this run.

## Combined score follow-up

User requested a single score. Added 50/50 composite, fixed weights, null when either category unavailable, PSS excluded. RED: `node tests/test_research_scores.cjs` failed at scores.combined.score (undefined). GREEN: same command passed after implementation. Final five-file coverage run passed 5/5; measurements.js lines 81.12%, branches 83.67%, functions 90%. Tests cover weighted result 62.5, bounds 0/100, missing category and invalid events/duration. Browser confirms synthetic demo composite 76.7 in table and main card, with deductions 18.3 and 5.0. Category detail collapsed. Screenshot: combined-score-ui.png. Combined score is project-defined, not clinically validated. Downloaded file contents not verified in this run.
