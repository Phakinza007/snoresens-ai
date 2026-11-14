# Snoresens AI — Vercel production

Primary deployment requested by the user: https://snoresens-ai-int182.vercel.app

Deploy: `vercel deploy --prod --yes` from this folder.
`dist/` contains the verified static app, local runtime assets and model files. `vercel.json` sets a buildless static deployment and the WebAssembly MIME header.

Audio inference runs in the browser with the unchanged YAMNet TFLite base and Dense heads exported from trained weights. User audio is not uploaded. History stays in the browser. The original Python app at localhost:8765 remains available separately.

Production deployment: `dpl_LfyhWJMT7eHMfJMUkJpRuHybzcsV`.
Detailed parity and browser-flow evidence: `../../results/hosted-browser-checks/`.
Screenshots for the presentation: `../../exports/demo-presentation/`.

`.env*` and `.vercel/` are explicitly excluded from uploads by `.vercelignore`. Do not copy CLI credentials into static output.
