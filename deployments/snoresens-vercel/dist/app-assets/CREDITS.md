# Snoresens web assets

- Design reference supplied by the user: https://www.figma.com/design/CyO0k9yBp1nxGHMsvJhHuk?node-id=3-130
- Inspected public prototype screens are stored for review in `results/figma-reference/`.
- Figma MCP `create_session` and `get_design_context` rejected access because the connected account lacked edit access. The implementation follows visible prototype proportions and flows, not exported layer measurements or Code Connect output.
- SVG icons: Lucide Static 0.468.0, downloaded unchanged from `https://unpkg.com/lucide-static@0.468.0/icons/`. See `LUCIDE-LICENSE.txt`. These are matching library substitutes, not exported Figma vectors.
- Typeface: Noto Sans Thai variable font, reused from the existing local workspace font assets. See `FONT-LICENSE.txt` (SIL Open Font License).
- Moon and bedside illustrations are CSS reconstructions of the prototype's geometric artwork. The wave on the home card is decorative; report timelines use actual analysis.
- Sample audio attribution remains in the project README: Tongue base snoring by Langenbergstefan, Wikimedia Commons, CC BY-SA 3.0. The app labels built-in audio as a sample and runs the real local model on it.
- All fonts and icons are served locally; no CDN is required at runtime.
