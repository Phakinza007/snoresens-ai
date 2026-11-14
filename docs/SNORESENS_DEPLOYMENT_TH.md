# Snoresens AI — deployment

## เว็บหลักบน Vercel ตามที่ผู้ใช้ระบุ

URL: https://snoresens-ai-int182.vercel.app

เผยแพร่ production สำเร็จวันที่ 14 พฤศจิกายน 2026 สถานะ Vercel `READY`

- Deployment: `dpl_LfyhWJMT7eHMfJMUkJpRuHybzcsV`
- Source: `deployments/snoresens-vercel`
- ลิงก์ production เปิดหน้าเว็บและ WASM ได้ HTTP 200 โดยไม่ต้องส่ง Site owner QA credential
- รันโมเดลบนเบราว์เซอร์เช่นเดียวกับเวอร์ชัน static ที่ทดสอบแล้ว

ตรวจ production จริงหลัง deploy: อัปโหลดเสียงเดโม 45 วินาทีได้กรน 28 วินาที/3 ช่วง, เสียงตัวอย่างเต็ม, ประวัติ, การอัดไมโครโฟนจำลองและ flow รายงานทำงานได้ ไม่พบ uncaught JavaScript errors หรือ POST ส่งเสียงออกไป เก็บ screenshots จาก Vercel จำนวน 11 ภาพและ manifest ที่ `exports/demo-presentation/` (เดสก์ท็อป 3840 × 2160, มือถือ 780 × 1688) พร้อม ZIP `exports/SnoresensAI-Demo-Screenshots.zip`

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
