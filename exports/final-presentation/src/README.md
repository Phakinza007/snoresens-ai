# สไลด์ Final

- `SnoresensAI-Final.pptx` / `SnoresensAI-Final.pdf`: สไลด์ 15 หน้า (PDF export จาก Keynote)
- `src/charts.py`: สร้างกราฟ `chart-split.png`, `chart-accuracy.png` จาก `results/model-comparison/metrics.json`
- `src/build.js`: สร้าง PPTX ด้วย pptxgenjs (`npm install pptxgenjs react react-dom react-icons sharp`)
  ต้องมี `apply_theme.js` (ตั้ง `APPLY_THEME_JS`) แล้วรัน `python src/fix_fonts.py SnoresensAI-Final.pptx` เพื่อตั้งฟอนต์ไทย Tahoma ใน theme
- ผลเทียบโมเดล: `.venv/bin/python docs/compare_snore_models.py --data <โฟลเดอร์ที่มี "Snoring Dataset">`
