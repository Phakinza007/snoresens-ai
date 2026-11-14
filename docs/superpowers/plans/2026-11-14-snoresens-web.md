# Snoresens web implementation plan

Goal: implement the user's Figma reference with real existing audio inference.
Spec: `docs/superpowers/specs/2026-11-14-snoresens-web-design.md`
Execution: direct in the existing non-Git project, preserving the original interface at `/lab`.

- [x] Add a mobile-first app shell and safe static routes; preserve original `/lab` functionality.
- [x] Implement local record storage and WAV conversion; verify persistence and encoding boundaries.
- [x] Build home/report/history/profile, real upload/record/analyze, playback and JSON/CSV export.
- [x] Compare rendered 390px screens against prototype and adapt desktop layout.
- [x] Run original regression checks plus real-browser app flow, reload/delete/export/error and simulated-microphone tests.
- [x] Document reference limitations, local-data behavior, recording limits and how to open the app.

Completed 14 November 2026. Evidence: `results/snoresens-web-checks/checks.json` (46/46 checks), original lab browser checks (28/28), Python 47 tests, Node 7 tests. Real phone/bedroom/overnight capture remains a separate physical validation, explicitly documented rather than counted as a passing check.
