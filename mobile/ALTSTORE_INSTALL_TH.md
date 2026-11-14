# ติดตั้งบน iPhone โดยไม่ต้องติดตั้ง Xcode ใน Mac

ใช้ไฟล์ native IPA ที่ build จาก source ด้วย GitHub Actions และให้ AltServer/AltStore Classic ลงชื่อด้วย Apple Account ของคุณ เป็นการติดตั้งเพื่อใช้ส่วนตัว ไม่ใช่การเผยแพร่ผ่าน App Store

## บน Mac

1. ติดตั้ง AltServer จาก [altstore.io](https://altstore.io/) หรือ Homebrew cask `altserver` ซึ่งดาวน์โหลดจาก CDN ของ AltStore
2. เปิด AltServer ไอคอนจะอยู่บนแถบเมนู
3. เชื่อม iPhone ด้วย USB ปลดล็อกและกดเชื่อถือคอมพิวเตอร์
4. ใน Finder เลือก iPhone และเปิด Show this iPhone when on Wi-Fi หากต้องการ refresh ผ่าน Wi-Fi
5. คลิกไอคอน AltServer > Install AltStore > เลือก iPhone กรอก Apple Account และยืนยันด้วยตัวเองในแอป ไม่ส่งรหัสผ่านหรือรหัส 2FA ผ่านแชต

## บน iPhone

1. เปิด Settings > General > VPN & Device Management แล้วเชื่อถือ developer ของบัญชีคุณ หากระบบร้องขอ
2. เปิด Settings > Privacy & Security > Developer Mode แล้วทำตามขั้นตอนบนหน้าจอ
3. เปิด AltStore Classic ให้ Mac ที่รัน AltServer เชื่อมต่อด้วย USB หรืออยู่ Wi-Fi เดียวกัน
4. ส่งไฟล์ `Snoresens-AI-unsigned.ipa` ที่ build สำเร็จแล้วไปเก็บใน Files บน iPhone เช่น ผ่าน AirDrop
5. ใน AltStore ไป My Apps > ปุ่ม + > เลือกไฟล์ IPA รอให้ลงชื่อและติดตั้ง จากนั้นเปิด Snoresens AI และอนุญาตไมโครโฟน

ยังต้องรอ GitHub Actions build ผ่านก่อนจึงจะมีไฟล์ IPA ให้ใช้ การมี source/project หรือไฟล์ workflow ไม่ได้แปลว่าไฟล์แอป build สำเร็จแล้ว และยังไม่ได้ยืนยันการทำงานบน iPhone จริง

บัญชีฟรีมีอายุ provisioning 7 วัน ต้อง refresh ภายในเวลานั้น (My Apps > Refresh All โดยเชื่อมต่อ AltServer) และมีข้อจำกัดจำนวนแอปที่ติดตั้งพร้อมกัน ไม่ควรลบ AltStore/AltServer จนกว่าจะเลือกวิธีลงชื่ออื่น

## แหล่งทางการ

- [ติดตั้ง AltStore Classic ผ่าน Mac](https://faq.altstore.io/altstore-classic/how-to-install-altstore-macos)
- [การ refresh และข้อจำกัดบัญชีฟรี](https://faq.altstore.io/altstore-classic/your-altstore)
- [Apple Personal Team](https://developer.apple.com/help/account/basics/about-your-developer-account)
