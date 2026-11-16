# รุ่นทดลอง 3: แยกกรนกับหายใจเฉพาะจุด

16 พฤศจิกายน 2026 — ผู้ใช้ขอให้วางแผนและลงมือแก้การนับหายใจเป็นกรน รุ่นนี้เป็นการทดลองในเครื่อง ยังไม่แทนโมเดลบนเว็บหรือแอป iPhone

## สาเหตุและแผนที่ลงมือแล้ว

1. ตรวจ pipeline พบว่าการซอย 20 ms ยังใช้คะแนน YAMNet บริบท 975 ms ที่ cache ทุก 100 ms ส่วนหัวจำแนกรุ่น 2 เคยฝึกเสียงหายใจเพียงหน้าต่างดังที่สุดหนึ่งวินาทีต่อคลิป
2. ทดลองตัวตรวจเพิ่มจากเสียงจริงเฉพาะจุด 200 ms: สเปกตรัม relative log-band 40 ย่าน เก็บ mean/std รวม 80 ค่า, StandardScaler และ Logistic Regression ตัวกรองนี้ทำงานหลังผลบวกของรุ่น 2 จึงไม่เพิ่มช่วงบวกในตำแหน่งที่รุ่น 2 เป็น non-snore
3. ใช้เสียงหายใจเต็มไฟล์ในชุด train เดิม แบ่งคลิปเป็นช่วง 200 ms ส่วน positive ใช้แกนเสียงดัง 200 ms จาก Kaggle train label เดิม น้ำหนักต่อไฟล์และต่อ class สมดุลกัน ตรวจ duplicate ข้าม split และใช้ split เดิมที่แยกผู้บันทึก Coswara
4. เลือก threshold จาก validation เท่านั้น: รักษาอย่างน้อย 95% ของ positive clip cores ที่รุ่น 2 จับถูก แล้วลดเวลาบวกผิดในเสียงหายใจ validation ไม่ปรับ hyperparameters จาก test
5. ประเมินชุด test เดิมในฐานะ diagnostic ที่เคยตรวจมาก่อน และชุดหายใจจากผู้บันทึกที่ไม่อยู่ใน manifest เดิมอีก 4 คน 8 ไฟล์ โดยไม่ใช้กลุ่มนี้เลือก threshold
6. ทำเครื่องมือตรวจฟังและติดป้ายเวลา 23 คลิปจาก train, development-validation และเดโม ไม่เปิด fresh test ให้ติดป้ายในชุดพัฒนานี้

**ขอบเขตหลักฐาน:** ป้าย positive 200 ms ยังสืบทอดจาก label ระดับคลิป ไม่ใช่ป้าย onset/offset ที่คนฟังจริง การทดลองนี้ยังไม่ใช่โมเดล segmentation ที่เรียนรู้ ground truth ราย 20 ms รายชื่อคนของ Kaggle ไม่ครบ จึงรับรอง speaker-disjoint ของส่วนนั้นไม่ได้ และ prompted breathing ไม่ใช่เสียงข้างเตียงจริง

## ผลที่ได้

| ชุดตรวจ | รุ่น 2 | รุ่นทดลอง 3 |
|---|---:|---:|
| หายใจ validation 12 ไฟล์ / 180.22 วินาที — เวลาบวกผิด | 5.38 วิ. | 0.24 วิ. |
| หายใจ test เดิม 14 ไฟล์ / 163.50 วินาที — diagnostic | 4.36 วิ. | 1.88 วิ. |
| หายใจจากคนที่ไม่เคยใช้ฝึก 4 คน / 8 ไฟล์ / 66.80 วินาที | 0.04 วิ. | 0.04 วิ. |
| Kaggle test เดิม: คลิปกรนที่จับถูกจาก 75 คลิป | 71 | 70 |
| Kaggle test เดิม: คลิปไม่กรนที่ทายผิดจาก 74 คลิป | 1 | 0 |

ชุดคลิปใช้แกนเสียงดัง 200 ms ในการตรวจตัวกรอง ยังไม่ใช่ recall ของเหตุการณ์ทั้งไฟล์ เดโม 45 วินาทีจากรุ่น 2 ได้ 11.96 วินาที รุ่นทดลองได้ 11.86 วินาที การลดลงนี้ไม่ได้พิสูจน์ว่าตำแหน่งที่ถูกตัดเป็นหายใจจริง

ฝึกจาก 4,264 หน้าต่าง train / 1,345 หน้าต่าง validation; threshold ของตัวกรอง 0.04 เป็น score ที่เลือกจาก validation ไม่ใช่ความมั่นใจเชิงสุขภาพ ตรวจสูตร JSON portable เทียบ sklearn ต่างไม่เกิน 1e-6 และรันซ้ำหลังถอด dependency cache ส่วนตัวแล้วได้ metrics เดิม

## การตัดสินใจ

**ยังไม่ deploy แทนรุ่นปัจจุบัน** เพราะยังตรวจผิด 1.88 วินาทีในชุดเดิม, ไม่ดีขึ้นในกลุ่มคนใหม่, พลาด positive core เพิ่มหนึ่งคลิป และยังไม่มี human temporal labels ห้ามอ้างว่าแก้หายใจเป็นกรนหมดแล้ว หรืออ้าง accuracy ราย 20 ms จากตัวเลขนี้

ขั้นถัดไปที่ต้องมีคนตรวจจริง: ฟัง 23 คลิปในหน้าตรวจเสียง แบ่งกรน/หายใจ/เสียงอื่น/ไม่แน่ใจให้คลุมคลิป แล้วส่งออก CSV เวลาไฟล์ต้นฉบับ จากนั้นจึงฝึก/เลือกเกณฑ์โดยใช้ป้าย train และ development-validation ที่ตรวจแล้ว ประเมินการลากขอบเขตและกรนที่หลุดจริง ส่วน fresh test ต้องเก็บแยกและไม่ย้ายเข้าฝึกเพื่อให้ตัวเลขดีขึ้น

## ลองใช้งานและทำซ้ำ

```sh
.venv/bin/python docs/train_snore_v3.py
.venv/bin/python docs/predict_snore_v3.py path.wav --out results/snore-v3/local-result.json
.venv/bin/python docs/build_snore_review.py
.venv/bin/python -m http.server 18763 --bind 127.0.0.1 --directory data/snore-v3-review
```

เปิด http://127.0.0.1:18763/ เสียงและคำตอบอยู่ในเครื่อง ผล CSV ต้องเป็นการฟังโดยคน ข้อมูลจาก automated browser test ไม่ใช่ ground truth ชุดข้อมูลเสียงอยู่ในโฟลเดอร์ที่ Git ignore ไม่เผยแพร่เสียงหายใจหรือคำตอบส่วนตัวขึ้น repo

สคริปต์ฝึกต้องมี Kaggle version 1 และ Coswara ตาม manifest เดิมในเครื่อง ผลรวมและนโยบายอยู่ที่ `results/snore-v3/` โมเดล JSON ทดลองอยู่ที่ `artifacts/experimental_snore_v3/`

ตรวจ Python 57 tests, Node 12 tests และหน้า review 10 ข้อผ่าน รวม validation ช่วงซ้อน/ช่วงขาด, persistence, export เวลาเดิม, audio load และมือถือไม่ล้น การตรวจ browser ใช้คำตอบจำลองใน profile แยกและไม่บันทึกเป็น human labels

## ลองรุ่นทดลอง / เตรียมป้ายจริง

```sh
.venv/bin/python docs/train_snore_v3.py
.venv/bin/python docs/predict_snore_v3.py deployments/snoresens-vercel/dist/samples/demo-45s.wav --out results/snore-v3/demo-candidate.json
.venv/bin/python docs/build_snore_review.py
.venv/bin/python -m http.server 18763 --bind 127.0.0.1 --directory data/snore-v3-review
```

การฝึกต้องมี Kaggle version 1 และ Coswara ที่เก็บในเครื่องตาม manifest เดิม ไม่รวมเสียงฝึกหรือเสียงส่วนตัวใน Git ส่วนคำสั่งทำนายใช้ artifact ทดลองที่เก็บใน `artifacts/experimental_snore_v3` โดยตรง ไม่เปลี่ยน default pipeline

เปิด http://127.0.0.1:18763 ฟังเสียงจริง แบ่งช่วงกรน/หายใจ/เงียบหรือเสียงอื่น และระบุช่วงที่ยังไม่แน่ใจ จากนั้นกดตรวจครบคลิปเมื่อแบ่งครอบคลุมทั้งไฟล์แล้วและดาวน์โหลด CSV ป้ายจะอ้างอิงเวลาของไฟล์ต้นฉบับ ป้ายจาก automatic QA ถูกเก็บแยกและไม่ใช่ ground truth ของคน

ตรวจ Python 57 tests, Node 12 tests และ browser ของเครื่องมือติดป้าย 11 ข้อผ่าน รวมการโหลดเสียง, บังคับเลือก label เอง, ป้องกันช่วงซ้อนหรือการระบุว่าตรวจครบทั้งที่ยังมีช่องว่าง, reload, export timestamp กลับไฟล์ต้นฉบับ และมือถือไม่ล้นหน้า ดู `results/snore-v3/review-browser-checks.json`

## งานถัดไปที่ต้องใช้การฟังยืนยัน

ป้ายเวลา 23 คลิปยังว่าง ไม่สร้างป้ายเทียมแล้วอ้างว่าคนยืนยันแล้ว เมื่อมี CSV ที่ตรวจจริง ให้แยก train/validation ตาม partition เดิม ใช้ช่วง `uncertain` เป็นช่วงไม่นับคะแนน และเก็บกลุ่มคนใหม่ไว้ไม่ใช้เลือกเกณฑ์ จากนั้นวัด false-positive duration, missed-snore duration และ boundary overlap บนเสียงที่มีป้ายเวลา ก่อนตัดสินใจแทนโมเดลในเว็บและ build iPhone ใหม่
