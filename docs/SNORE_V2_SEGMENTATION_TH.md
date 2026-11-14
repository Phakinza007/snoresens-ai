# แก้การรวมช่วงหายใจเป็นกรน — รุ่น 2

14 พฤศจิกายน 2026: ผู้ใช้แจ้งว่าแยกช่วงไม่ถี่พอและยังนับหายใจเป็นกรน โดยพบในภาพรวมหลายไฟล์ ไม่มีไฟล์/เวลาที่ติดป้ายโดยผู้ใช้เฉพาะจุด จึงไม่อ้างว่าผ่านการยืนยันด้วยการฟังของผู้ใช้แล้ว

## สาเหตุที่ตรวจพบ

1. ระบบเดิมทำนายทีละ 1 วินาทีและรวมผลบวกที่ติดกัน บริบทโมเดล 15,600 samples หรือ 0.975 วินาทีอาจมีทั้งกรนกับหายใจ จึงลากขอบเขตได้
2. หัวจำแนกเดิมฝึกจาก Kaggle กรน/ไม่กรนเป็นหลัก เมื่อตรวจหน้าต่างดังที่สุด 1 วินาทีจาก Coswara breathing ที่แยกคนไว้เป็น test พบ false positives 6/14 คลิป
3. การเปลี่ยน hop อย่างเดียวไม่ได้แก้ตัวจำแนกหรือระบุเสียงที่ตำแหน่งกลางได้แน่นอน และการย่อ timeline ทั้งไฟล์ทำให้ช่วงเว้นสั้นดูไม่ชัด

## สิ่งที่เปลี่ยน

- ฝึก Dense head ใหม่จากศูนย์บน YAMNet 521 scores เดิม เพิ่ม prompted breathing negatives และแยกคนของ Coswara ตาม train/validation/test เดิม ไม่ warm-start จากหัวเดิม
- กู้ Kaggle dataset version 1 ผ่าน KaggleHub: 1,000 คลิป ลบเสียงซ้ำ 9 เหลือ 991 แบ่ง 693/149/149; เพิ่ม breathing 32/12/14 คลิป รวม train 725 / validation 161 / test 163
- กำหนด breathing sample weight 10, early stopping จาก weighted validation loss และเลือก threshold จาก validation เท่านั้น ตาม max-min snore recall กับ breathing specificity; threshold ได้ 0.44
- ใช้บริบท 0.975 วินาทีเลื่อนทุก 0.1 วินาที แต่แต่ละ decision cell ไม่ซ้อนกัน จึงไม่นับเวลาซ้ำและเก็บส่วนท้ายตามระยะจริง
- ใช้ activity gate บน RMS ของแต่ละ cell เพื่อไม่ให้ความมั่นใจของบริบทรอบข้างถูกยกให้ช่วงเงียบ/เบาโดยอัตโนมัติ: floor = max(-60, P20 + min(6, (P95-P20)/2)) dBFS จาก cell ที่มีค่าจำกัดและ >= -80 dBFS
- ค่า activity gate เป็นเกณฑ์วิศวกรรมทดลอง ไม่ใช่โมเดลหายใจและอาจพลาดกรนเบามาก ไม่เพิ่มกฎซ่อนเพื่อให้คะแนนดูดีขึ้น; เก็บ score เดิม, activity pass และ threshold ใน export
- ไม่รวมข้าม cell ไม่กรน ไม่ปัดเวลาทิ้งเป็นวินาทีเต็ม แสดง event timestamps ถึงทศนิยม 0.1 วินาที
- เพิ่มกราฟซูม 10 วินาทีรอบจุดที่เลือก เลื่อน/กดลูกศรทีละ 0.1 วินาทีได้ และเพิ่มปุ่ม “วิเคราะห์ใหม่แบบละเอียด” สำหรับไฟล์เก่าที่เก็บเสียงไว้
- ผลเก่าไม่ถูกเขียนทับหรือแปลงเป็นความละเอียดใหม่โดยไม่มีการรันโมเดล แจ้งรุ่นและ hop ตามผลที่เก็บจริง

## ผลที่วัดได้

### การจำแนกคลิป: ใช้หน้าต่าง 1 วินาทีและไม่ใช่คะแนนความแม่นยำของขอบเขตเวลา

| ชุดทดสอบ | รุ่นเดิม | หัวจำแนกรุ่น 2 |
|---|---|---|
| Kaggle 149 คลิป | [[74,0],[3,72]], accuracy 97.99%, snore recall 72/75 | [[73,1],[4,71]], accuracy 96.64%, snore recall 71/75 |
| Prompted breathing 14 คลิป จากคนที่ไม่ใช้ฝึก | นับผิดเป็นกรน 6/14 | นับผิดเป็นกรน 0/14 |
| รวม test ใหม่ 163 คลิป | [[82,6],[3,72]], accuracy 94.48% | [[87,1],[4,71]], accuracy 96.93% |

ข้อจำกัดการเปรียบเทียบ: แม้โหลด Kaggle version 1 และใช้ seed เดิมได้แล้ว ยังไม่มี original split manifest ของรุ่น 1 จึงไม่อ้างว่าผลรุ่น 1 บน Kaggle เป็น unbiased benchmark ใหม่ หัวรุ่น 2 ฝึกใหม่และใช้ manifest/hash ที่บันทึกในรอบนี้ ส่วน Coswara แยกคนระหว่าง train/validation/test และไม่ได้อยู่ในข้อมูลฝึกหัวกรนรุ่น 1

### ทั้ง pipeline บนไฟล์ breathing เต็ม

ตรวจ 14 ไฟล์ prompted breathing รวม 163.498875 วินาที โดยถือป้ายไฟล์ breathing เป็น reference ไม่ได้มีคนติดป้ายเสียงราย 0.1 วินาที

- เวลาที่ถูกนับเป็นกรน: **58.475 → 4.600 วินาที**
- ไฟล์ที่ยังมีกรนผิดอย่างน้อยหนึ่ง cell: **10/14 → 8/14** หมายความว่ายังมี false positives สั้น ๆ ไม่ใช่แก้หมดทุกไฟล์
- การวัดนี้ใช้รุ่น 2 + overlapping inference + activity gate รวมกัน ไม่ได้แยกผล causal ของแต่ละส่วน
- ห้ามเรียก 0/14 จากหน้าต่างดังที่สุดว่าไม่มี false positives บนทั้งไฟล์

### เดโม 45 วินาที

- เดิม: 45 decision rows, ตรวจกรน 28 วินาที / 3 ช่วง
- รุ่น 2 ทั้ง pipeline: 450 decision rows, ตรวจกรน 12.4 วินาที / 10 ช่วง
- ตัวอย่างขอบเขตใหม่: 5.3–6.9, 9.0–10.4, 12.4–14.1 วินาที พร้อมช่องว่างระหว่างช่วง
- ผล Python และ browser เทียบแล้ว label และ event boundaries ตรงกัน การลดเวลาหรือเพิ่มจำนวนช่วงไม่ได้เป็นหลักฐานความแม่นยำด้วยตัวเอง ยังไม่มี human timestamps ของเดโมนี้ครบทุกช่วง

## หลักฐานและการทำซ้ำ

- `docs/train_snore_v2.py`: ฝึกและเลือก threshold ด้วย validation
- `artifacts/snore_v2/`: หัวรุ่นใหม่และ metrics; รุ่นเดิมใน artifacts หลักคงอยู่
- `experiments/snore-v2/split-manifest.json`: รายชื่อชุดข้อมูล, person IDs ของ Coswara และ SHA-256 เสียงหลัง preprocessing
- `results/segmentation-debug/full-breathing-v1-v2.json`: ผลทั้งไฟล์รายรายการ
- `results/segmentation-debug/demo-v2-python.json`, `demo-v2-browser.json`: ผลละเอียดและ parity
- `results/segmentation-debug/browser-checks.json`: zoom/reanalysis/persistence และไม่มี JS errors
- `docs/build_vercel_app.py`: รวม UI และ model metadata สำหรับ Vercel โดยไม่แตะ credentials

Python tests 52 และ Node tests 11 ผ่านในรอบปรับนี้ รวม partial cell, การไม่นับ padding, ช่องว่างย่อย, low-activity exclusion และเวลาทศนิยม ยังไม่ใช่การทดสอบกับห้องนอนจริง

คำสั่งทำซ้ำ:

```sh
.venv/bin/python predict.py path.wav --include-timeline
.venv/bin/python predict.py path.wav --legacy-snore --include-timeline
.venv/bin/python -m unittest discover -s tests -v
node --test tests/test_temporal_segmentation.mjs
```

การขยับทุก 0.1 วินาทีไม่เท่ากับยืนยัน localization accuracy 0.1 วินาที: YAMNet ยังใช้บริบทประมาณ 1 วินาที ดูโมเดลต้นทางที่ https://www.tensorflow.org/tutorials/audio/transfer_learning_audio


## ปรับตาม feedback รอบถัดไป — ขอบเขต 20 ms

ผู้ใช้ขอให้ถี่กว่า 0.1 วินาทีและแสดงเฉพาะจังหวะกรน จึงปรับ default เป็น 0.02 วินาที (50 ช่องต่อวินาที) โดยไม่อ้างว่าโมเดลมีความแม่นยำระดับ 20 ms:

- เก็บบริบทและผลหัวจำแนกเดิมทุก 100 ms; ใช้ cache เพื่อไม่รัน YAMNet เพิ่มห้าเท่า ไม่ฝึกหรือเปลี่ยน threshold โมเดล
- แต่ละช่อง 20 ms ต้องผ่านทั้ง classifier, activity gate ของ parent 100 ms และ RMS ของตัวเอง ช่องเบาย่อยจึงไม่รับผลบวกจากเสียงข้างเคียง ไม่ขยาย parent ที่เดิมเป็น non-snore ให้กลายเป็นกรน
- แก้กราฟภาพรวมจากระบายทั้ง bucket เมื่อมีกรนบางส่วน เป็นวาดขอบเขตเหตุการณ์จริง กราฟซูมวาดเหตุการณ์ต่อเนื่อง ไม่ให้รอยต่อพิกเซลของช่องย่อยดูเหมือนมีช่องเงียบปลอม
- เลื่อนฟังด้วยคีย์บอร์ดทีละ 0.02 วินาที แสดงเวลาและความยาวเหตุการณ์สองตำแหน่งทศนิยม Export เก็บ analysis hop 0.02, model hop 0.1 และ segmentation version แยกจากรุ่นโมเดล
- เดโม 45 วินาที: 2,250 ช่อง ได้ 11.96 วินาที/11 เหตุการณ์ (เดิม 12.4 วินาที/10 เหตุการณ์) เช่น 9.00–10.40 เหลือ 9.08–10.36 การลดเวลาอย่างเดียวไม่พิสูจน์ว่าแยกถูกต้อง
- เสียงหายใจ held-out เดิม 14 ไฟล์: false-positive duration จาก 4.60 เหลือ 4.36 วินาที ยังคงตรวจผิดในบางไฟล์ จึงไม่อ้างว่าเหลือเฉพาะกรนทั้งหมด หรือใช้ผลชุดนี้เลือก threshold เพิ่ม
- ข้อจำกัด: ยังเป็น classifier ที่ดูบริบท 0.975 วินาทีร่วมกับ energy gate ไม่ใช่โมเดลติดป้ายกรน/หายใจราย 20 ms กรนเบาอาจถูกตัดออก ต้องมีข้อมูลที่คนระบุ onset/offset เพื่อวัด event precision/recall และ temporal overlap จริง

ตรวจ Python 53 tests และ Node 12 tests ผ่าน ตรวจเบราว์เซอร์รวมการวิเคราะห์ใหม่, parity กับ Python, ไม่มีการขยายช่วง negative, ตรวจพิกเซลสีช่องเว้น, export, persistence และมือถือผ่าน 14 ข้อ สคริปต์ `docs/check_snore_boundaries_browser.py` และ `docs/evaluate_micro_boundaries.py` ใช้ทำซ้ำ หลักฐานชื่อ `*micro20*` ใน `results/segmentation-debug/`
