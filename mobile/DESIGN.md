# Snoresens native interface

User-confirmed direction (2026-11-16): match the existing Snoresens website, including composition and flows. Canonical preference entry remains in the local feedback-memory skill; this file records implementation decisions.

Reference: https://snoresens-ai-int182.vercel.app, mobile content viewport 390 × 844. Live production HTML/CSS/JS and rendered home/history/profile/prepare/consent/record/report screens inspected. Source web assets are in `web/snoresens/`; production also includes morning-checklist UI. Reference captures in local `experiments/native-web-parity/` are review material, not clinical/device-test evidence.

Preserve Flutter native audio recording, interruption policy, background audio, file protection, Documents storage, resumable analysis, frozen v2 weights and metadata compatibility. No web deployment or model change is part of this task.

Reuse Noto Sans Thai and Lucide SVGs from the web with their licenses. Match blue #3157f5, navy #152d59, text #182f58, muted #7387a6, background #f5f7ff, white cards, 18/24 px mobile margins, 16 px buttons and 22–28 px card radii. Recreate the web's CSS moon, wave and bedside artwork with native drawing/layout; these are reproductions of web artwork, not Figma exports.

Four bottom tabs: home/report/history/profile. Guided prepare/consent and dark recording pages hide tabs. Native-specific copy describes local processing and background recording rather than the browser's screen-on requirement. Recording wave remains decorative/flat unless driven by real microphone data; never simulate live measured amplitude.

Report values use actual persisted results; sample audio is explicitly labeled and runs the real model. Timelines preserve 20 ms boundaries. Morning checklist ports the existing project's rules with an explicit unvalidated-screening note; it does not turn snore classification into a medical diagnosis. Device recording and audio export still require physical-device verification.
