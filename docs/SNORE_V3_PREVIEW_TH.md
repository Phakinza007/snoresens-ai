# เว็บทดสอบตัวตรวจกรนรุ่น 3

URL: https://snoresens-ai-v3-test.vercel.app

เป็นโปรเจกต์ Vercel แยกชื่อ `snoresens-ai-v3-test` เว็บหลัก `snoresens-ai-int182.vercel.app` ยังใช้รุ่น 2

- รัน YAMNet + Dense head รุ่น 2 ตามเดิม แล้วกรองผลบวกด้วย acoustic verifier 200 ms ของรุ่นทดลอง 3 ในเบราว์เซอร์
- มี banner รุ่นทดลองและ label รุ่นโมเดลในรายงาน เก็บ raw v2 prediction, local verifier score และ threshold ใน JSON/CSV
- เก็บเช็กลิสต์การหายใจ 5 ข้อจาก branch สำหรับ deploy ไว้ด้วย
- ผลเก่าไม่เปลี่ยนเอง: เลือกไฟล์ WAV ใหม่หรือกดวิเคราะห์ใหม่ ผลและเสียงอยู่ใน browser storage ของโดเมนทดสอบ ซึ่งแยกจากเว็บหลัก
- ข้อจำกัด: positive cores ใช้ป้ายระดับคลิป ยังไม่มี human onset/offset validation และอาจตัดกรนบางช่วงออก ดู [ผลทดลอง](SNORE_V3_PLAN_RESULTS_TH.md)

## ตรวจ

Node 17 tests ผ่าน รวม synthetic fixture ที่เทียบ feature 80 ค่าและคะแนน local verifier กับ Python Browser 13 checks บนเสียงเดโม 45 วินาทีที่ทำนายจริง: 2,250 ช่อง, labels และ event boundaries ตรง Python, คะแนน local verifier ต่างไม่เกิน 1e-4, ไม่มีกรนเพิ่มจาก v2-negative, export/reload/มือถือ และไม่มี JavaScript errors หรือ audio POST

ดู `results/snore-v3/web-preview-checks.json` เพื่อยืนยัน URL ที่ตรวจจริง ข้อมูลบน `model-info.json` แยกผลหัวจำแนกรุ่น 2 ออกจากผลตัวกรองรุ่น 3 ไม่ใช้คะแนน classifier ระดับคลิปเป็นความแม่นยำการแบ่งช่วง

## สร้างซ้ำ

```sh
git fetch origin deploy/risk-assessment-20ms
.venv/bin/python docs/build_v3_preview.py
cd deployments/snoresens-v3-preview
vercel link --yes --project snoresens-ai-v3-test
vercel deploy --prod --yes
```

`dist` และข้อมูลเชื่อม Vercel ไม่รวมใน Git สคริปต์คัดลอกเฉพาะไฟล์เว็บ โมเดล และ config ไม่คัดลอก `.env` จากเว็บหลัก
