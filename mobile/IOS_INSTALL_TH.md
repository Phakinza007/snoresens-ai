# ติดตั้ง Snoresens AI บน iPhone ผ่าน Mac

แอปนี้เป็น Flutter application ที่รันเป็นแอป iOS และใช้ TFLite บนอุปกรณ์ ไม่ใช่ Safari shortcut หรือ WebView ครอบเว็บไซต์ ต้อง build ด้วย Xcode ก่อนติดตั้งได้

## เตรียมเครื่องมือ

- Flutter SDK: ติดตั้งไว้ที่ `~/Developer/flutter` และมีคำสั่ง `flutter`, `dart` ผ่าน `/opt/homebrew/bin`
- CocoaPods: ใช้ `pod --version` ตรวจ
- ติดตั้ง Xcode ผ่าน Mac App Store เปิด Xcode หนึ่งครั้งเพื่อยอมรับข้อตกลงและติดตั้ง iOS components ตามที่ตัวโปรแกรมแจ้ง การยืนยันบัญชีและสิทธิ์ผู้ดูแลต้องทำบนเครื่องเอง

## เตรียมโค้ด

จากโฟลเดอร์ `mobile`:

```sh
./setup.sh
flutter analyze
flutter test
./open-ios.command
```

`setup.sh` สร้างแพลตฟอร์ม iOS เมื่อยังไม่มี คัดลอก YAMNet กับหัวจำแนกรุ่น 2 ตั้งชื่อแอป และเพิ่มคำอธิบายสิทธิ์ไมโครโฟน ไม่ใส่ Apple Account, team ID หรือ provisioning profile ลง Git

## ติดตั้งบนโทรศัพท์

1. ต่อ iPhone เข้ากับ Mac ด้วยสาย เลือก **Trust / เชื่อถือ** บนโทรศัพท์
2. ใน Xcode ไป **Settings > Accounts** เพิ่ม Apple Account ของคุณเอง
3. เปิด `ios/Runner.xcworkspace` เลือก target **Runner > Signing & Capabilities** เปิด **Automatically manage signing** และเลือก **Personal Team**
4. ถ้า bundle identifier ชนกับบัญชีอื่น ให้เปลี่ยนเป็นชื่อที่คุณเป็นเจ้าของ เช่น `com.yourname.snoresens`
5. เลือก iPhone ของคุณเป็นปลายทางแทน simulator เปิด **Developer Mode** บน iPhone หาก Xcode ร้องขอ แล้วกด **Run**
6. หาก iPhone ร้องขอให้เชื่อถือ developer ให้ทำตามหน้าจอใน **Settings > General > VPN & Device Management**

บัญชีฟรีติดตั้งเพื่อทดสอบบนอุปกรณ์ส่วนตัวได้ Provisioning หมดอายุใน 7 วัน ต้อง build และติดตั้งใหม่ การส่งขึ้น App Store/TestFlight ต้องใช้สิทธิ์โปรแกรมนักพัฒนาที่เกี่ยวข้อง ไม่ได้เกิดขึ้นจากขั้นตอนนี้

## ตรวจบน iPhone จริง

- เปิดแอปแล้วโมเดลโหลดสำเร็จ และอนุญาตไมโครโฟนได้
- อัดสั้น ๆ หยุด ฟังย้อน เลือก WAV 16 kHz และส่งออก JSON/CSV ได้
- รายงานระบุโมเดลรุ่น 2 และขอบเขต 0.02 วินาที
- เปรียบเทียบช่วงจากไฟล์เดโมกับผลเว็บ/Python

รุ่นแอป 0.2.0 ตั้งค่า native background audio และเก็บเสียง/ประวัติใน Documents แล้ว ยังต้องตรวจการล็อกจอและใช้งานต่อเนื่องบน iPhone จริง ดู [ขั้นตอนทดสอบและข้อจำกัด](RELEASE_0.2.0_TH.md)

## เอกสารทางการ

- [ตั้งค่า Flutter สำหรับ iOS](https://docs.flutter.dev/platform-integration/ios/setup)
- [Apple Personal Team และข้อจำกัดบัญชีฟรี](https://developer.apple.com/help/account/basics/about-your-developer-account)
