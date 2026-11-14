# ร่วมพัฒนา Snoresens AI

Repository นี้เป็น public ทุกคน clone, pull และ fork ได้ GitHub กำหนดให้ push เข้า repository ต้นทางโดยตรงได้เฉพาะเจ้าของและ collaborator ที่ได้รับสิทธิ์ การตั้งค่า public ไม่ได้ให้สิทธิ์เขียนแก่ทุกบัญชี

## ทุกคนส่งการแก้ไขได้ผ่าน Pull Request

1. กด **Fork** ที่ [Phakinza007/snoresens-ai](https://github.com/Phakinza007/snoresens-ai/fork)
2. Clone fork ของคุณเอง แล้วสร้าง branch สำหรับงาน
3. แก้ไขและทดสอบ จากนั้น commit และ push ไปยัง fork ของคุณ
4. เปิด **Pull Request** โดยเลือกปลายทาง `Phakinza007/snoresens-ai`, branch `main`

```sh
git clone https://github.com/YOUR_USERNAME/snoresens-ai.git
cd snoresens-ai
git remote add upstream https://github.com/Phakinza007/snoresens-ai.git
git switch -c your-change
# แก้ไขและทดสอบงานก่อน commit
git add path/to/changed-file
git commit -m "Describe your change"
git push -u origin your-change
```

ดึงการเปลี่ยนแปลงล่าสุดจากต้นทาง:

```sh
git fetch upstream
git switch main
git merge --ff-only upstream/main
```

ดูวิธีรันและตรวจโค้ดใน [README](README.md) และ [คู่มือติดตั้ง iPhone](mobile/IOS_INSTALL_TH.md) กรุณาไม่ commit รหัสผ่าน, token, ไฟล์ `.env`, signing certificate, provisioning profile หรือเสียงส่วนตัว/ชุดข้อมูลฝึกที่ไม่ได้ตั้งใจเผยแพร่

สมาชิกทีมที่ต้อง push เข้า repository ต้นทางโดยตรงต้องได้รับคำเชิญ collaborator และกดยอมรับก่อน
