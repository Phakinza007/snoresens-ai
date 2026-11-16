# SnoreSense AI — โมเดลตรวจเสียงกรน

โครงการ INT182: เว็บวิเคราะห์เสียงกรน พร้อมอัปโหลด/บันทึกเสียง รายงาน Timeline การย้อนฟัง และประวัติในเบราว์เซอร์ อ่าน [แหล่งที่มาและใบอนุญาตของ assets](THIRD_PARTY_NOTICES.md)

## เริ่มใช้งานในเครื่อง

ใช้ Python 3.12:

```sh
git clone https://github.com/Phakinza007/snoresens-ai.git
cd snoresens-ai
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-inference.txt
.venv/bin/python web_server.py
```

เปิด `http://127.0.0.1:8765/` สำหรับแอป หรือ `/lab` สำหรับเครื่องมือวิเคราะห์ละเอียด เว็บออนไลน์เป็น static app ที่รันโมเดลในเบราว์เซอร์ ไม่ต้องใช้ Python server:

```sh
python3 -m http.server 8000 --directory deployments/snoresens-vercel/dist
```

เปิด `http://localhost:8000/` สำหรับตรวจเวอร์ชัน static ในเครื่อง ส่วน raw training datasets, `.env`, credentials และ `.venv` ไม่รวมใน repository

**เว็บออนไลน์บน Vercel:** https://snoresens-ai-int182.vercel.app — วิเคราะห์เสียงในเบราว์เซอร์ มี [ภาพจากเว็บจริงสำหรับพรีเซนต์](exports/demo-presentation/README.md) และ [ZIP ภาพทั้งหมด](exports/SnoresensAI-Demo-Screenshots.zip)

**รุ่น 2 — แยกช่วงละเอียด:** เพิ่มข้อมูลเสียงหายใจในการฝึก ปรับขอบเขตทุก 0.02 วินาที โดยใช้ผลโมเดลทุก 0.1 วินาทีร่วมกับ activity gate บนเสียงจริงแต่ละช่อง พร้อมกราฟตามขอบเขตและกราฟซูม ดู [ผลตรวจและข้อจำกัดล่าสุด](docs/SNORE_V2_SEGMENTATION_TH.md) คะแนนและภาพก่อนหน้านี้ที่ระบุรุ่น 1 เป็นหลักฐานของรุ่นเดิม

**เว็บ Snoresens AI จาก Figma พร้อมใช้งาน:** เปิด `http://127.0.0.1:8765/` หลังรันเซิร์ฟเวอร์เดิม มีบันทึก/อัปโหลด รายงาน ประวัติในเครื่อง และโปรไฟล์ ส่วนเครื่องมือวิเคราะห์ละเอียดเดิมอยู่ที่ `/lab` ดู [วิธีใช้และผลตรวจเว็บใหม่](docs/SNORESENS_WEB_TH.md)

แนวทาง Final ของ INT182: อ่าน [Feedback อาจารย์ Phase 2 และรายการงานต่อ](docs/PHASE2_INSTRUCTOR_FEEDBACK_TH.md) โดยโฟกัส pipeline กรน/ไม่กรน ผลประเมินจริง และเดโมเสียงสั้น

ผลตรวจล่าสุด 14 พ.ย. 2026 และแผนเตรียมส่ง: [Phase 3 readiness](docs/PHASE3_READINESS_TH.md)

หลักฐานรอบเตรียมสไลด์: [กราฟ ตาราง ตรวจข้อมูล และผลทดสอบเว็บ/export](docs/PHASE3_EVIDENCE_TH.md) · [ไฟล์ภาพสำหรับสไลด์](exports/phase3-evidence/README.md)

ฟีเจอร์วิเคราะห์เสียงเพิ่มเติม: timeline พร้อมเล่นเสียง, ช่วงเงียบระหว่างกรน, ความถี่, จังหวะ และ export/เปรียบเทียบไฟล์ ดูวิธีใช้และสถานะทดสอบใน [AUDIO_ANALYSIS.md](AUDIO_ANALYSIS.md)

เสียงสำหรับภาวะหยุดหายใจ: เพิ่มเครื่องมือเตรียมป้ายกำกับ/ฝึก/ประเมินโมเดลวิจัยแบบใช้เสียงอย่างเดียวแล้ว แต่ยังไม่ได้ฝึกด้วยข้อมูลตรวจการนอนหลับจริง ดู [APNEA_RESEARCH.md](APNEA_RESEARCH.md) แบบสอบถามเลื่อนไปทำภายหลัง

## ใช้งานหน้าเว็บและแอปมือถือ

**เว็บบนคอมพิวเตอร์:**

บน macOS ดับเบิลคลิก [เปิดเว็บ Sanor.command](เปิดเว็บ%20Sanor.command) เพื่อเปิดเว็บและ Terminal พร้อมกัน แล้วเลือก `test_snore_16k.wav` ทดสอบได้ทันที หาก macOS เตือนว่าเปิดไฟล์ไม่ได้ ให้คลิกขวาไฟล์แล้วเลือก Open

```bash
cd snoresens-ai
source .venv/bin/activate
python web_server.py
```

เปิด `http://127.0.0.1:8765` แล้วกด **เริ่มอัดเสียง** บน Chrome คอมพิวเตอร์ เลือกโฟลเดอร์ที่จะเก็บเสียงและอนุญาตไมโครโฟน เว็บอัดเป็นส่วนละ 30 นาที บันทึก WAV mono 16 kHz 16-bit ในโฟลเดอร์ที่เลือก แล้ววิเคราะห์แต่ละไฟล์ให้อัตโนมัติ กด **หยุดอัดเสียง** เพื่อปิดส่วนสุดท้าย เว็บยังรองรับการเลือกไฟล์ WAV เช่น `test_snore_16k.wav` หลายไฟล์เพื่อเทียบผลได้ เซิร์ฟเวอร์รับไฟล์เฉพาะจากเครื่องนี้และลบไฟล์ชั่วคราวที่ใช้วิเคราะห์ ไม่มีการอัปโหลดไปบริการภายนอก เว็บยังไม่ได้เปิดให้โทรศัพท์เครื่องอื่นเข้าใช้งาน

ควรทดลองอัด 10–15 นาทีก่อนใช้งานข้ามคืน ขณะอัดให้เสียบไฟ เปิดเว็บและคอมพิวเตอร์ไว้ อย่าปิดฝา Mac การอัดในเว็บเบราว์เซอร์อาจหยุดหากระบบพักหรือไมโครโฟนถูกตัด จึงยังไม่ถือว่าทดสอบอัดทั้งคืนผ่านแล้ว หากการบันทึกลงโฟลเดอร์ล้มเหลว เว็บจะพยายามดาวน์โหลดไฟล์ WAV นั้นแทน

**แอป Flutter Android/iPhone:** ซอร์สและโมเดลอยู่ใน [mobile/](mobile/) รองรับการเลือก WAV PCM 16-bit 16 kHz หรืออัดเสียงใหม่ แล้วประมวลผลด้วย TFLite บนเครื่อง ดูวิธีสร้างและข้อจำกัดใน [mobile/README.md](mobile/README.md) เครื่องพัฒนาปัจจุบันยังไม่มี Flutter SDK จึงยังไม่ได้ build และทดสอบบนโทรศัพท์จริง

`test_snore.wav` ที่มีอยู่เป็นไฟล์ Ogg แม้นามสกุลเป็น `.wav`; หน้าเว็บและแอปต้องใช้ `test_snore_16k.wav` หรือ WAV ที่แปลงรูปแบบจริงแล้ว

โปรเจกต์นี้มีโมเดลสำหรับตอบว่าเสียงช่วงละ 1 วินาที **กรนหรือไม่กรน** และมีตัวจำแนกเสียงไอขั้นทดลองเพื่อช่วยคัดช่วงให้คนตรวจ พร้อมไฟล์ TFLite สำหรับนำไปใส่แอป Flutter ยังไม่ตรวจภาวะหยุดหายใจขณะหลับ ยังไม่นับจำนวนครั้งที่ไออย่างน่าเชื่อถือ และยังไม่แยกเสียงหายใจกับความเงียบ

แผนพัฒนาฟีเจอร์ที่ใช้เสียงจากโทรศัพท์อย่างเดียวอยู่ใน [PLAN_AUDIO_ONLY.md](PLAN_AUDIO_ONLY.md)
วิธีเก็บและติดป้ายเสียงสำหรับฝึกฟีเจอร์ไออยู่ใน [LABELING.md](LABELING.md)

## ข้อมูลและวิธีฝึก

- ข้อมูล: [Snoring Dataset ของ Tareq Khan บน Kaggle](https://www.kaggle.com/datasets/tareqkhanemu/snoring) มีเสียงกรน 500 คลิป และไม่กรน 500 คลิป โค้ดดาวน์โหลดด้วย `kagglehub` โดยอัตโนมัติ
- เตรียมข้อมูล: แปลงเป็น mono 16 kHz, ใช้ช่วงแรก 1 วินาที, ลบคลิปที่ sample ซ้ำกันตรง ๆ 9 คลิป เหลือ 991 คลิป
- แบ่งข้อมูลแบบรักษาสัดส่วนคลาส: ฝึก 693, validation 149, ทดสอบ 149 คลิป เกณฑ์ตัดสินเลือกจาก validation เท่านั้น
- โมเดลวิจัย: [YAMNet จาก TensorFlow Hub](https://tfhub.dev/google/yamnet/1) ที่ฝึกจาก AudioSet แล้ว → embedding 1,024 ค่า → Dense(64, ReLU) → Dropout(0.2) → Dense(1, sigmoid) ฝึกเฉพาะ Dense classifier และเก็บใน `snore_head.keras`
- โมเดลมือถือ: [YAMNet TFLite ของ Google](https://www.kaggle.com/models/google/yamnet/tfLite/classification-tflite/1) ที่รับเสียง 15,600 sample แล้วส่งออก **521 class scores** → Dense classifier แบบเดียวกันที่ฝึกใหม่บน scores เหล่านั้น → ความน่าจะเป็นเสียงกรน โมเดลมือถือจึงใช้ตัวจำแนกอีกตัวหนึ่ง ไม่ได้นำ `snore_head.keras` ไปต่อกับ YAMNet TFLite โดยตรง

YAMNet ทั้งสองรุ่นถูกตรึงน้ำหนักไว้ โมเดลที่ฝึกเองคือ Dense classifier สองตัวข้างต้น

## ผลทดสอบเดิมของรุ่น 1 และไฟล์ที่ใช้

โมเดลมือถือทำนายถูก **146/149 คลิป (97.99%)** บนชุดทดสอบ Kaggle นี้; เสียงกรนถูก 72/75 คลิป (recall 96%) และคลิปไม่กรนถูก 74/74 คลิป เกณฑ์ตัดสินคือ 0.63 รายละเอียดอยู่ใน `artifacts/mobile_metrics.json` ผลนี้ยังไม่ใช่ผลจากการทดสอบโทรศัพท์ในห้องนอนจริง

| ไฟล์ | หน้าที่ |
| --- | --- |
| `artifacts/yamnet_base.tflite` | รับเสียง mono 16 kHz จำนวน 15,600 sample; ส่งออก scores รูปร่าง `[1, 521]` |
| `artifacts/snore_score_head.tflite` | รับ scores `[1, 521]`; ส่งออกความน่าจะเป็น `[1, 1]` |
| `artifacts/mobile_metrics.json` | เกณฑ์ตัดสินและผลทดสอบ |
| `artifacts/snore_head.keras`, `artifacts/metrics.json` | โมเดลและผลวิจัยที่ใช้ embedding 1,024 ค่า |

ไฟล์ TFLite สองไฟล์รวมกันประมาณ 4.26 MB ใช้ทำงานบนเครื่องโดยไม่ต้องส่งเสียงไปเซิร์ฟเวอร์

## ทดลองกับไฟล์ WAV

ใช้ Python 3.12 แล้วรันจากโฟลเดอร์นี้ (Mac เครื่องนี้มี Python 3.12 ให้เรียกด้วย `python3.12`):

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-inference.txt
python predict.py path/to/audio.wav
```

ผลลัพธ์ JSON สรุปเวลาที่ตรวจพบกรน สัดส่วนเวลาที่กรน จำนวนช่วงกรน ช่วงที่ยาวที่สุด และระดับเสียงกรนแบบสัมพัทธ์ (RMS dBFS) โมเดลประมวลผลทีละวินาที; ใช้ `--timeline-csv` เพื่อบันทึกผลรายวินาทีรวมค่า `rms_dbfs` เช่น:

```bash
python predict.py path/to/audio.wav --timeline-csv results/timeline.csv \
  --cough-review-csv results/cough_review.csv
```

สคริปต์อ่านเสียง stereo เป็น mono และ resample เป็น 16 kHz อัตโนมัติ ช่วงท้ายที่สั้นกว่า 1 วินาทีจะนับตามความยาวจริง ค่า threshold 0.63 ใช้แบ่งผลโมเดลเป็นกรน/ไม่กรน ไม่ใช่คะแนนความรุนแรงหรือการวินิจฉัยโรค

ค่า dBFS เทียบกับระดับสูงสุดของไฟล์ดิจิทัล ค่าใกล้ 0 หมายถึงสัญญาณในไฟล์ดังขึ้น เสียงเงียบสนิทแสดงเป็น `null` เปรียบเทียบข้ามคืนได้เมื่อใช้โทรศัพท์ ตำแหน่งวาง และการตั้งค่าไมค์เดียวกัน; ค่านี้ไม่ใช่ระดับเสียงจริงแบบ dB SPL

### เปรียบเทียบไฟล์เสียงหลายคืน

ใช้โมเดลเดิมวิเคราะห์แต่ละไฟล์และเปรียบเทียบผลโดยไม่ต้องติดป้ายเสียงด้วยมือ:

```bash
source .venv/bin/activate
python compare.py night1.wav night2.wav --json results/night_comparison.json
```

แสดงสัดส่วนเวลาที่โมเดลตรวจพบกรน, นาทีกรนและจำนวนช่วงกรน **ต่อชั่วโมงที่อัดเสียง** รวมถึง dBFS มัธยฐานของช่วงกรน ระยะเวลาอัดเสียงไม่เท่ากันจึงควรดูค่าต่อชั่วโมง ไม่ใช่จำนวนช่วงรวม ใช้โทรศัพท์ ตำแหน่งวาง และการตั้งค่าอัดเหมือนกันเมื่อเทียบข้ามคืน ผลเป็นแนวโน้มจากโมเดล ไม่ใช่ชั่วโมงที่หลับจริงหรือคะแนนสุขภาพ การเปรียบเทียบไฟล์โดยไม่มีป้ายอ้างอิงไม่สามารถบอกความแม่นยำของโมเดลได้

`yamnet_cough_score` เป็นคะแนนดิบของคลาส `Cough` (index 42) จาก [YAMNet class map](https://github.com/tensorflow/models/blob/master/research/audioset/yamnet/yamnet_class_map.csv) ถ้ามี `artifacts/cough_score_head.tflite` โปรแกรมจะเพิ่ม `cough_probability` จากตัวจำแนกที่ฝึกเอง และใช้ค่านี้เรียง `--cough-review-csv`; ถ้าไม่มีจะเรียงด้วยคะแนน YAMNet ค่าเริ่มต้น 30 ช่วง เปลี่ยนด้วย `--cough-review-limit` คะแนนเหล่านี้ใช้ช่วยเลือกช่วงให้คนเปิดฟัง **ยังไม่ใช่จำนวนครั้งที่ไอหรือผลตรวจสุขภาพ** และหากทุกช่วงได้คะแนนใกล้ศูนย์ อันดับใน CSV ก็ไม่ใช่หลักฐานว่ามีเสียงไอ

### ผลกับไฟล์ตัวอย่างในโฟลเดอร์นี้

`test_snore.wav` ที่ดาวน์โหลดมาเป็นไฟล์ Ogg ภายใน แม้ชื่อไฟล์ลงท้าย `.wav` จึงแปลงเป็น `test_snore_16k.wav` ซึ่งเป็น PCM WAV mono 16 kHz จริง แล้วรัน:

```bash
.venv/bin/python predict.py test_snore_16k.wav \
  --timeline-csv results/test_snore_timeline.csv \
  --cough-review-csv results/test_snore_cough_review.csv
```

ผลอยู่ใน `results/test_snore_summary.json`, `results/test_snore_timeline.csv` และ `results/test_snore_cough_review.csv`: ความยาว 150.435 วินาที ตรวจพบกรน 131 วินาที (87.08%) จำนวน 19 ช่วงตามผลรายวินาที ช่วงยาวที่สุด 17 วินาที ค่ากลางของระดับเสียงในช่วงที่ตรวจพบกรน −21.04 dBFS และเปอร์เซ็นไทล์ที่ 95 คือ −11.52 dBFS ช่วงที่มีวินาทีไม่กรนคั่นจะถูกนับเป็นคนละช่วง ตัวเลขนี้เป็นผลจากไฟล์ตัวอย่างหนึ่งไฟล์ ไม่ใช่เกณฑ์สุขภาพหรือคะแนนประสิทธิภาพโมเดล

ไฟล์เสียงต้นฉบับคือ [Tongue base snoring โดย Langenbergstefan บน Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Tongue_base_snoring.ogg) เผยแพร่ภายใต้ [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/) ไฟล์ `test_snore_16k.wav` เป็นไฟล์ที่แปลงจากต้นฉบับ โดยเปลี่ยนรูปแบบเสียงและอัตราสุ่มตัวอย่าง

## ฝึกใหม่

```bash
pip install -r requirements.txt
python train.py --out artifacts
```

ใช้ `--data /path/to/dataset` หากดาวน์โหลดข้อมูลเองแล้ว โดยโฟลเดอร์ย่อยต้องมีป้าย `0` (ไม่กรน) และ `1` (กรน) ถ้าไม่ใส่ `--data` โปรแกรมจะโหลดจาก Kaggle และโหลด YAMNet สองรุ่นตามที่ระบุในโค้ด

## ฝึกตัวจำแนกเสียงไอขั้นต้นจาก Coswara

ดาวน์โหลด [Coswara-Data ของ IISc](https://github.com/iiscleap/Coswara-Data) แล้วใช้ `extract_data.py` ของชุดข้อมูลแตกไฟล์เสียงเป็น `Extracted_data/<date>/<participant>/<type>.wav` โดยติดตั้ง `pandas` ตามที่สคริปต์ต้นทางใช้ จากนั้นรันจากโปรเจกต์นี้:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
python train_cough.py --data /path/to/Coswara-Data/Extracted_data --out artifacts
```

สคริปต์ใช้ `cough-heavy` และ `cough-shallow` เป็นบวก ใช้เสียงหายใจและเสียงนับเลขเป็นลบ; หากมีโฟลเดอร์ `annotations` ของ Coswara อยู่ข้าง `Extracted_data` จะเลือกเฉพาะไฟล์ที่ผู้ตรวจให้คุณภาพ 1 หรือ 2 เลือกช่วง 1 วินาทีที่ดังที่สุดต่อไฟล์ แล้วแบ่ง train/validation/test ตามรหัสผู้บันทึก ไม่ให้คนเดียวกันข้ามชุด ส่งออก `cough_score_head.tflite`, `cough_score_head.keras` และ `cough_metrics.json` ในโฟลเดอร์ `artifacts`

**ผลทดลองปัจจุบัน:** ดาวน์โหลด Coswara เฉพาะวันที่ `20200505` และ `20200604` จากแหล่งทางการไว้ใน `data/coswara/` หลังกรองคุณภาพเหลือ 186 ไฟล์จาก 32 คน แบ่งตามคนเป็นฝึก 104, validation 40, ทดสอบ 42 ไฟล์ โมเดลตอบถูก 39/42 ไฟล์ในชุดทดสอบ (เสียงไอถูก 12/14, เสียงหายใจ/พูดถูก 27/28) เกณฑ์คัดช่วงเพื่อตรวจคือ 0.51 รายละเอียดใน `artifacts/cough_metrics.json` และ log ใน `results/cough_coswara_train.log` [ชุดข้อมูล Coswara ระบุสัญญาอนุญาต CC BY 4.0](https://github.com/iiscleap/Coswara-Data/blob/master/README.md)

เมื่อรันกับ `test_snore_16k.wav` 150.435 วินาที ไม่มีช่วงใดที่คะแนนไอเกิน 0.51 ส่วนคลิปไอ Coswara หนึ่งคลิปมี 6/9 ช่วง 1 วินาทีที่เกินเกณฑ์ ผลตัวอย่างอยู่ใน `results/test_snore_timeline.csv` และ `results/coswara_cough_example_timeline.csv` การตรวจนี้เป็นเพียงการตรวจข้ามไฟล์สองตัวอย่าง ไม่ใช่การวัด false alarms ต่อชั่วโมงบนห้องนอนจริง

ข้อมูล Coswara เป็นการไอ/หายใจตามคำสั่ง ไม่มีป้ายเวลาที่ไอแต่ละครั้งและไม่มีเสียงรบกวนข้างเตียงครบถ้วน คะแนน 39/42 มาจากเพียง 7 คนในชุดทดสอบ ยังใช้เป็นเพียงตัวช่วยเลือกช่วงเสียงให้ตรวจด้วยคน ต้องติดป้ายและทดสอบเสียงจากโทรศัพท์จริงก่อนทำตัวนับไอ

## ขั้นต่อไปสำหรับแอป Flutter

1. ใช้แพ็กเกจอัดเสียง เช่น [`record`](https://pub.dev/packages/record) เก็บ PCM mono 16 kHz เป็นช่วงละ 1 วินาที ตรวจการทำงานเมื่อล็อกหน้าจอบน Android และ iOS จริง
2. ใช้ [`tflite_flutter`](https://pub.dev/packages/tflite_flutter) โหลด TFLite ทั้งสองไฟล์ เรียก base ด้วย 15,600 sample แรกของแต่ละช่วง แล้วส่ง 521 scores ให้ classifier ใช้ threshold จาก `mobile_metrics.json`
3. ทดสอบกับเสียงห้องนอนจริงที่ได้รับความยินยอมและแยกคน/คืนระหว่างชุดฝึกกับทดสอบ แล้วปรับโมเดลก่อนนำไปใช้จริง
4. ถ้าต้องการ 3 คลาส `กรน/หายใจ/เงียบ` ต้องเพิ่มเสียงที่ติดป้าย `หายใจ` และ `เงียบ` แล้วฝึก classifier 3 outputs ใหม่ ชุดข้อมูลปัจจุบันรองรับเพียง 2 คลาส

ข้อมูล Kaggle ไม่มีรหัสบุคคลหรือแหล่งอัดต้นฉบับที่เพียงพอสำหรับการแยกตามคน จึงอาจมีข้อมูลจากแหล่งเดียวกันอยู่ข้ามชุดและทำให้คะแนนสูงเกินการใช้งานจริง ตรวจสิทธิ์ของชุดข้อมูลและโมเดลก่อนเผยแพร่แอปหรือไฟล์ที่เกี่ยวข้อง

ร่วมพัฒนาได้ผ่าน fork และ Pull Request ดู [CONTRIBUTING.md](CONTRIBUTING.md)

รุ่นทดลอง 3: [แผน ผลเปรียบเทียบ และเครื่องมือติดป้ายเวลา](docs/SNORE_V3_PLAN_RESULTS_TH.md) ยังไม่แทนโมเดลที่เผยแพร่
