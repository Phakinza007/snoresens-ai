# Snoresens AI web implementation

User request: implement the supplied Figma prototype/design as a working web app in Sanor.
Reference: https://www.figma.com/design/CyO0k9yBp1nxGHMsvJhHuk?node-id=3-130
Observed screens: home 3:130, report 4:359, history 4:841, profile 5:694.
Figma MCP session/context requests return no-edit-access. Public prototype is accessible; screenshots in `results/figma-reference/` are the visual source. Exact layer/font/asset export is unavailable. Do not claim pixel-identical reconstruction or original Figma vector assets.

Implementation decision: keep the project's vanilla HTML/CSS/JavaScript and local Python API. Introduce the app at `/`, preserving the original analysis interface at `/lab`. A separate React app would duplicate working infrastructure without helping this request. User chose the Figma appearance; responsive desktop layout and storage implementation are agent decisions.

Visual direction: mobile-first light blue background, navy feature cards, vivid blue primary actions, rounded white cards, Thai typography and four-item bottom navigation. At 390px use 24px content insets and 342px hero cards, matching the prototype's proportions. Adapt wider screens into a spacious two-column dashboard with a side navigation. Do not include fake phone status indicators in the browser.

Flows: home → record/upload → analyze → report; report → play/seek/export/delete; history → stored report; profile → local display name, privacy, measurement explanation and recording guidance. Explicit sample action analyzes existing real sample audio, not synthetic health results. No invented historical nights or medical risk category.

Reuse: `/api/analyze`, `SanorMeasurements.researchScores`, CSV helpers and existing model artifacts. Keep detailed analysis accessible at `/lab`. Persist analysis and audio in local IndexedDB, with a clear warning if storage fails, delete and clear actions. The combined score remains the existing project-defined exploratory score, not medical risk. Display unknown values as unavailable.

Recording: explicit prepare and consent screens precede microphone permission. Capture mono PCM at 16 kHz through AudioWorklet and encode PCM16 WAV, retaining silent frames; split long sessions into 30-minute files; analyze/store each file independently. The timer counts captured audio samples. Stop and cleanup on errors. Warn that browser background/sleep recording is not guaranteed. Test with a simulated microphone and separately identify the remaining physical-device check. This replaces compressed MediaRecorder decoding after browser checks found its decoded duration could be shorter than wall-clock capture time.

Assets: local Noto Sans Thai from existing workspace font; library SVG icons where exact Figma exports are unavailable, explicitly credited as substitutes. No external requests required to use the app after assets are stored.

Validation: existing Python/Node checks; meaningful storage and WAV encoding tests; real Chrome upload, playback, exports, persistence across reload, history deletion, keyboard/dialog behavior, recording with simulated microphone, mobile and desktop screenshots.
