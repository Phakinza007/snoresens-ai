# จุดย้อนกลับ Snoresens AI

บันทึก 16 พฤศจิกายน 2026 (Asia/Bangkok) ก่อนเปลี่ยนจากการทดสอบรุ่น 3 กลับรุ่น 2 ตามคำขอผู้ใช้ รุ่น 3 ยังเก็บเป็นงานทดลอง ไม่ใช่ default ที่ได้รับการยอมรับ

| รุ่นที่เก็บ | Git tag | Commit ของเว็บ | สถานะปัจจุบัน |
|---|---|---|---|
| รุ่น 2 ก่อนตัวกรอง local | `snore-web-v2-2026-11-16` | `cb5705a5dbbbc3d4145cac0ae5d8eed8e5186aa0` | ใช้งานทั้งเว็บหลักและลิงก์ทดสอบ |
| รุ่นทดลอง 3 | `snore-web-v3-preview-2026-11-16` | `c1996b52ddc25f4547d7393e351f5a46624b1ec6` | เก็บไว้ ไม่เปิดใช้ซ้ำหากผู้ใช้ยังไม่ร้องขอ |

[Snapshot manifest](2026-11-16-web-snapshots.json) บันทึก deployment ID, immutable URL, hash ของ runtime/โมเดล และ SHA256 ของ static archive ที่เก็บในเครื่อง ตรวจไฟล์กับเว็บจริงแล้วก่อนบันทึก Manifest นี้เป็นสถานะตอนเก็บ snapshot ไม่ใช่แหล่งอ้างอิงว่าลิงก์ alias ปัจจุบันใช้โมเดลใด

## หลัง rollback

- เว็บหลัก: https://snoresens-ai-int182.vercel.app ใช้ `snore-v2-breathing-negatives` ตามเดิม
- ลิงก์ทดสอบเดิม: https://snoresens-ai-v3-test.vercel.app เปลี่ยนเป็นรุ่น 2 แล้ว แม้ชื่อโดเมนยังมี v3
- Deployment หลังกลับรุ่น 2 บนโปรเจกต์ทดสอบ: `dpl_6JQ3nMsWUVhV2n9wQ6nTEZrUhQKP`
- ใช้ static snapshot ของรุ่น 2 ตรวจ hash ก่อน deploy ไม่ได้ย้อนเป็น deployment รุ่น 3 ที่เก่ากว่าโดยเข้าใจผิดว่าเป็นรุ่น 2
- ผลเก่าใน browser storage ไม่ถูกเขียนทับ กด **วิเคราะห์ใหม่แบบละเอียด** เพื่อสร้างผลจากรุ่น 2 หลัง refresh เว็บ
- แอป iPhone ที่ build ไว้ก่อนหน้าเป็นรุ่น 2 อยู่แล้ว

## วิธีคืนจาก snapshot ที่เก็บในเครื่อง

ไฟล์อยู่ที่ `exports/version-backups/<git-tag>.tar.gz` (ไม่รวมใน Git เพราะเป็นสำเนา runtime/models ที่มีอยู่แล้ว) ตรวจ SHA256 เทียบ manifest ก่อนใช้ แตกในโฟลเดอร์ใหม่แล้ว link ให้ตรงโปรเจกต์:

```sh
# ตัวอย่างคืนรุ่น 2 ไปยังโปรเจกต์ทดสอบ ไม่ใช่เว็บหลัก
mkdir -p /tmp/snoresens-restore-v2
tar -xzf exports/version-backups/snore-web-v2-2026-11-16.tar.gz -C /tmp/snoresens-restore-v2
cd /tmp/snoresens-restore-v2
vercel link --yes --project snoresens-ai-v3-test
vercel deploy --prod --yes
```

หาก static archive ในเครื่องหาย ใช้ Git tag สร้าง checkout แยกเพื่อเรียกคืน source/model รุ่นนั้นได้ รุ่น 2 มี `deployments/snoresens-vercel/dist` อยู่ใน Git ครบ ส่วนรุ่น 3 ให้ดู builder ใน commit ที่ tag ชี้ และใช้ UI base commit `8604a4adecf02984303bedaadb8f4e71b090c269` ตาม snapshot ที่บันทึกไว้ อย่าใช้ remote branch ที่อาจเปลี่ยนแล้วแทนโดยไม่ตรวจ hash

Deployment เก่าบนผู้ให้บริการอาจมี retention จึงเก็บ Git tag และ static archive ควบคู่กัน ไม่อาศัย URL เก่าอย่างเดียว การ restore ไปเว็บหลักต้องเลือก project `snoresens-ai-int182` ให้ถูกต้อง

## รุ่นแอป iPhone

- รุ่นแอป 0.1.0+1 ก่อนเพิ่ม background recording: tag `snore-ios-v0.1.0` ชี้ source `b798350ef039a333bafcb03be0f01a649513e1d9` หลักฐานเดิมอยู่ใน `results/native-ios/0.1.0/` และ IPA เดิมสำรองในเครื่องที่ `exports/ios/versions/Snoresens-AI-0.1.0-unsigned.ipa`
- รุ่นแอป 0.2.0+2 เพิ่มอัดเบื้องหลัง พัก/ต่อ ประวัติถาวร และประมวลผลต่อ ดู [release notes](../../mobile/RELEASE_0.2.0_TH.md) กับ [ไฟล์ build](../../exports/ios/README.md) ทั้งสองรุ่นแอปใช้หัวจำแนกเสียงกรนรุ่น 2 เหมือนเดิม
- IPA ต้องลงชื่อผ่าน AltStore/Xcode รุ่นแอปกับรุ่นโมเดลเป็นคนละเลข การ build ผ่านไม่ยืนยันการอัดข้ามคืนบนโทรศัพท์

### 0.3.0+4 — หน้าตาเว็บบน iPhone

เพิ่ม UI ตามเว็บปัจจุบันโดยคง native recorder และหัวจำแนกรุ่น 2: tag `snore-ios-v0.3.0` ชี้ source `d9e0cf085492fae623d9f53508011eff7ecd7e8d` ดู [release notes](../../mobile/RELEASE_0.3.0_TH.md), [การออกแบบ](../../mobile/DESIGN.md) และ [ไฟล์ build](../../exports/ios/README.md) หลักฐาน 0.2.0 ถูกสำรองแยกใน `results/native-ios/0.2.0/` ก่อนสร้างรุ่นนี้
