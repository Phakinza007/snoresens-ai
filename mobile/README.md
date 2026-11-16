# Snoresens AI — native Flutter app

แอป iPhone ที่ใช้ YAMNet TFLite และหัวจำแนกกรนรุ่น 2 บนอุปกรณ์โดยตรง ไม่อัปโหลดเสียงไปเซิร์ฟเวอร์ รุ่นแอป **0.2.0+2** เพิ่มการอัดเบื้องหลัง ปุ่มพัก/ต่อ ประวัติถาวร และการวิเคราะห์ไฟล์ยาวทีละส่วน ดู [วิธีใช้ ขอบเขต และการทดสอบบน iPhone](RELEASE_0.2.0_TH.md)

## ติดตั้งและพัฒนา

ใช้ [AltServer/AltStore Classic](ALTSTORE_INSTALL_TH.md) เพื่อลงชื่อและติดตั้ง IPA ที่ build ด้วย GitHub Actions โดยไม่ต้องลง Xcode ใน Mac หรือใช้ [Xcode และ Personal Team](IOS_INSTALL_TH.md) หากมี Xcode เต็มชุด

Flutter SDK ใน Mac เครื่องที่เตรียมอยู่ที่ `~/Developer/flutter` และ CocoaPods ผ่าน Homebrew ไม่มี Xcode เต็มชุดในเครื่อง จึงใช้ workflow **Build iPhone app (unsigned)** บน runner `xcode-27` ที่เรียกเองเท่านั้น โค้ด ทดสอบ และตรวจ archive ก่อนปล่อย artifact `SnoresensAI-iOS-unsigned` ดู [ไฟล์ติดตั้งและหลักฐาน build](../exports/ios/README.md)

```sh
./setup.sh
flutter analyze
flutter test
```

`setup.sh` เตรียม assets รุ่น 2 และค่าของ iOS ไม่ใส่ Apple Account, team ID หรือ provisioning profile ลง Git โฟลเดอร์ iOS และ custom Swift file protection bridge อยู่ใน source แล้ว

## พฤติกรรม

- โมเดล `snore-v2-breathing-negatives` ใช้บริบท 0.975 วินาที / ผลโมเดลทุก 0.1 วินาที และขอบเขตย่อย 0.02 วินาทีร่วมกับ activity gate เหมือนเว็บ ดู [ข้อจำกัดของ segmentation](../docs/SNORE_V2_SEGMENTATION_TH.md)
- รับ WAV PCM16 16 kHz mono/stereo หรืออัดไมโครโฟนเป็น WAV mono เก็บต้นฉบับใน Documents และวิเคราะห์ทีละไม่เกิน 5 นาที เก็บสรุปรวมและรายงานส่วนย่อย
- ฟังย้อน เลือกเวลา ดู dBFS/สเปกตรัม/ช่วงเงียบ ส่งออก JSON/Timeline CSV และลบพร้อมยืนยันได้
- การอัดใช้ native audio session พร้อม `UIBackgroundModes: audio` ส่วนการวิเคราะห์ทำเมื่อเปิดแอป หากถูกพักกลับมากดวิเคราะห์ต่อได้
- ประวัติที่ค้างจากการปิดแอปถูกเปลี่ยนเป็นรอวิเคราะห์ พร้อมคงไฟล์เดิมไว้ ไม่ได้หมายความว่าอัดต่อหลัง force-quit หรือซ่อม WAV ที่เสียได้ทุกกรณี
- ยังต้องตรวจการอัดขณะล็อกจอ สายโทรเข้า การรันโมเดลและ export บน iPhone จริงก่อนยืนยันใช้งานข้ามคืน

ชุดทดสอบครอบคลุมการเก็บข้อมูล การพัก/ต่อ การกดซ้ำ การประมวลผลต่อ และ UI รวม fixture ตัดสินใจ 2,250 ช่องจาก Python และตรวจพิกเซลกราฟที่ขอบเขต 20 ms การทดสอบด้วย fake recorder/analyzer ไม่ใช่การรันไมโครโฟนหรือ TFLite บน iPhone จริง

ไอคอนใช้ moon จาก Lucide Static 0.468.0 ดู [license](../web/snoresens/LUCIDE-LICENSE.txt) และ `app-icon.svg` สร้าง PNG ซ้ำด้วย `docs/generate_mobile_icons.py`

หากต้องสร้าง Android source เพิ่มใช้ `SANOR_PLATFORMS=android,ios ./setup.sh` แล้วติดตั้ง Android SDK ก่อน build การอัดเบื้องหลังของ Android ต้องเตรียม foreground service เพิ่มแยกจาก iOS
