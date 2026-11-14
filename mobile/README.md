# Snoresens AI — native Flutter app

แอป iPhone/Android ที่ใช้ YAMNet TFLite และหัวจำแนกกรนรุ่น 2 บนอุปกรณ์โดยตรง ไม่ใช้ WebView และไม่อัปโหลดเสียงไปเซิร์ฟเวอร์

## iPhone

ใช้ [AltServer/AltStore Classic โดยไม่ต้องลง Xcode](ALTSTORE_INSTALL_TH.md) หรือดู [คู่มือติดตั้งฟรีผ่าน Xcode Personal Team](IOS_INSTALL_TH.md) จากโฟลเดอร์นี้:

```sh
./setup.sh
flutter analyze
flutter test
./open-ios.command
```

มีโปรเจกต์ `ios/Runner.xcworkspace` พร้อมชื่อแอป สิทธิ์ไมโครโฟน และไอคอน Snoresens สร้างจาก Flutter 3.50.0 / Dart 3.14.0 ใช้ CocoaPods สำหรับปลั๊กอินที่ยังไม่รองรับ Swift Package Manager ไฟล์ `open-ios.command` จะเตรียม dependencies ผ่าน Flutter ก่อนเปิด Xcode ให้เลือก Personal Team และโทรศัพท์ ไม่เก็บ Apple Account หรือ signing certificate ใน Git

บน Mac ที่เตรียมในแชตนี้ติดตั้ง Flutter ที่ `~/Developer/flutter` และ CocoaPods 1.17.0 แล้ว แต่ยังไม่มี Xcode เต็มชุด จึงยัง build หรือติดตั้งจาก Mac เครื่องนี้ไม่ได้

Workflow **Build iPhone app (unsigned)** ใน GitHub Actions ใช้ runner มาตรฐาน `xcode-27` และรันเมื่อสั่งเองเท่านั้น ตรวจโค้ด ทดสอบ แล้ว build iOS release แบบไม่ลงชื่อ ผล build/IPA ต้องตรวจสถานะของ workflow ก่อนอ้างว่าสำเร็จ ไฟล์ unsigned ยังต้องลงชื่อด้วยบัญชีของผู้ติดตั้งก่อนใช้งานบน iPhone

## พฤติกรรมและข้อจำกัด

- หัวจำแนกรุ่น `snore-v2-breathing-negatives`, บริบท 0.975 วินาที / ผลโมเดลทุก 0.1 วินาที และขอบเขตย่อย 0.02 วินาทีร่วมกับ activity gate เหมือนเว็บ ดู [วิธีและข้อจำกัด](../docs/SNORE_V2_SEGMENTATION_TH.md)
- เปิด WAV PCM16 16 kHz mono/stereo หรืออัดไมโครโฟนเป็น WAV แล้วฟังย้อน เลือกช่วง ดู dBFS/สเปกตรัม/ช่วงเงียบ และส่งออก JSON/Timeline CSV
- ประวัติต้นฉบับมือถือเก็บในหน่วยความจำ และไฟล์ฟังย้อนใช้ temporary storage ควร export ก่อนปิดแอป
- ยังไม่รองรับหรือยืนยันการอัดขณะล็อกจอ/การอัดข้ามคืน ยังต้องตรวจไมโครโฟน โมเดลจริง และ export บน iPhone จริง
- การแบ่งช่อง 20 ms ไม่ใช่หลักฐานว่าแยกกรน/หายใจถูกต้องทุกช่อง และอาจตัดกรนเบาออกได้

ทดสอบ Flutter 9 ข้อผ่าน และ analyzer ไม่พบปัญหา รวม fixture ตัดสินใจ 2,250 ช่องจาก Python, ช่องเงียบ, partial cell, ตำแหน่งโมเดลที่ cache, label ทศนิยม และตรวจพิกเซลไม่ให้กราฟขยายช่วงกรน การทดสอบนี้ไม่ใช่การรัน TFLite บน iPhone จริง

ไอคอนใช้ moon จาก Lucide Static 0.468.0 ดัดแปลงบนสีของโครงการ ดู [license](../web/snoresens/LUCIDE-LICENSE.txt) และซอร์ส `app-icon.svg` สร้าง PNG ซ้ำได้ด้วย `docs/generate_mobile_icons.py` (ใช้ Python/Playwright)

หากต้องสร้าง Android source เพิ่ม: `SANOR_PLATFORMS=android,ios ./setup.sh` แล้วติดตั้ง Android SDK ที่เหมาะสมก่อน build
