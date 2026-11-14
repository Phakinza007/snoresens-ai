# Snoresens AI — deployment

## เว็บหลักบน Vercel ตามที่ผู้ใช้ระบุ

URL: https://snoresens-ai-int182.vercel.app

เผยแพร่ production สำเร็จวันที่ 14 พฤศจิกายน 2026 สถานะ Vercel `READY`

- Deployment รุ่น 2: `dpl_B6YRM97CyxyjfFoaav7afsxtTz46`
- Source: `deployments/snoresens-vercel`
- ลิงก์ production เปิดหน้าเว็บและ WASM ได้ HTTP 200 โดยไม่ต้องส่ง Site owner QA credential
- รันโมเดลบนเบราว์เซอร์เช่นเดียวกับเวอร์ชัน static ที่ทดสอบแล้ว

ตรวจ production รุ่น 2 จริงผ่าน `docs/check_snore_v2_browser.py`: ผ่าน 12 ข้อ รวมการเปิดผลรุ่นเดิมแล้ววิเคราะห์เสียงใหม่จริงเป็น 450 ช่อง ช่องละ 0.1 วินาที, ผลตรงกับ Python, เลื่อนฟังทีละ 0.1 วินาที, export JSON, reload และแสดงมือถือโดยไม่ล้นหน้า ไม่พบ JavaScript errors หรือ POST ส่งเสียงออกไป หลักฐานอยู่ที่ `results/segmentation-debug/production-browser-checks.json` พร้อมภาพ `v2-report-desktop.png` และ `v2-zoom-mobile.png`

เดโม 45 วินาทีได้กรน 12.4 วินาที/10 ช่วงจากรุ่น 2 ตัวเลขนี้ยังไม่ใช่ความแม่นยำที่ตรวจเทียบช่วงเสียงด้วยคน ชุดเสียงหายใจ 14 ไฟล์ยังมี false positives รวม 4.6 วินาทีใน 8 ไฟล์ ดูข้อจำกัดและวิธีประเมินใน `docs/SNORE_V2_SEGMENTATION_TH.md`

ภาพ 11 ภาพใน `exports/demo-presentation/` และ ZIP `exports/SnoresensAI-Demo-Screenshots.zip` เป็นภาพก่อนปรับรุ่น 2 (เดโมเดิม 28 วินาที/3 ช่วง) ไม่ควรนำตัวเลขจากภาพเก่ามารายงานเป็นผลรุ่นปัจจุบัน

## ประวัติการเผยแพร่รุ่นเดิม

## การเผยแพร่ผ่าน Sites ก่อนผู้ใช้ระบุ Vercel

เผยแพร่สำเร็จวันที่ 14 พฤศจิกายน 2026 ผ่าน Sites

URL: https://snoresens-ai-int182.wrybarge4.chatgpt.site

- สิทธิ์เริ่มต้นเฉพาะบัญชีเจ้าของเว็บ ไม่ได้เปิดสาธารณะ
- Source: deployments/snoresens-site
- Commit: 5c2db5fa8e65604d821041aa8ad4f9213d35daf3
- Project: appgprj_6af81cf8864881919cb6d9e0c4c5d5f0
- Deployment: appgdep_6af81edb9c088191876907d69f5330dd
- Version: appgprj_6af81cf8864881919cb6d9e0c4c5d5f0~appgver_2616676b1bc08191b7fff7368da0169f
- Native deployment status: succeeded

เวอร์ชันออนไลน์ใช้ YAMNet TFLite ตัวเดิมผ่าน WASM และ Dense heads ที่ส่งออกจากน้ำหนักเดิม โดยไม่ฝึกใหม่ เสียงวิเคราะห์ในเบราว์เซอร์ ไม่ต้องเปิด Mac ทิ้งไว้ ไม่อัปโหลดเสียงไป Python server

ทดสอบก่อนเผยแพร่: เดโม 45 วินาทีได้กรน 28 วินาที/3 ช่วงและ labels ตรงกับ Python ทุกช่วง ความต่าง probability สูงสุด 0.000001; เสียงตัวอย่าง 150.435 วินาทีได้กรน 131 วินาที/19 ช่วงตรงกัน ตรวจอัปโหลด อัดเสียงจำลอง export ประวัติ และ reload แล้ว ไม่พบ POST ส่งเสียงหรือ uncaught JS errors ดู results/hosted-browser-checks

เวอร์ชันในเครื่องยังใช้ Python ที่ http://127.0.0.1:8765 และ /lab ตามเดิม เครื่องมือวิเคราะห์ spectral/breathing ขั้นสูงของ Python ไม่ได้รวมในเว็บ static ออนไลน์ จึงไม่แสดงลิงก์เครื่องมือที่ใช้ไม่ได้

ภาพสำหรับพรีเซนต์เก็บที่ exports/demo-presentation/ พร้อมคำอธิบายที่มาของเสียงและข้อจำกัดของภาพไมโครโฟนจำลอง
