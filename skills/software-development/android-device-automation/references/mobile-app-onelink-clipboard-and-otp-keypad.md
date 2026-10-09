# Mobile App Referral, OneLink Attribution & Numeric OTP Keypad Automation

Kỹ thuật và cạm bẫy thực chiến khi tự động hóa ứng dụng Android mới (Airdrop, Web3 Privy Auth, AppsFlyer OneLink) trên dàn máy Samsung Galaxy S7 (SM-G930F).

---

## 1. Trích xuất OneLink / Deep-Link từ Android Clipboard

### Vấn đề:
- Các app mobile hiện đại (React Native, Flutter) khi bấm "Share / Copy Referral Link" không hiển thị link đầy đủ trên textview mà ghi thẳng vào hệ thống clipboard của Android hoặc mở ShareSheet Intent.
- Lệnh `adb shell service call clipboard 1` trên Samsung Android 7/8 trả về Parcel byte stream phức tạp, rất khó decode chuỗi UTF-16 an toàn qua bash một dòng.

### Giải pháp O(1) Thực chiến:
Mượn trình duyệt Samsung Browser (`com.sec.android.app.sbrowser`) hoặc ô nhập bất kỳ để dán và OCR:
```bash
# 1. Mở Samsung Browser vào trang trắng
adb -s <SERIAL> shell am start -a android.intent.action.VIEW -d "about:blank" -p com.sec.android.app.sbrowser
sleep 2

# 2. Tap vào URL Bar (toạ độ Samsung S7 màn 1080x1920: x=429, y=149)
adb -s <SERIAL> shell input tap 429 149
sleep 1

# 3. Gửi keyevent PASTE (279)
adb -s <SERIAL> shell input keyevent 279
sleep 1

# 4. Chụp màn hình và chạy WinRT OCR đọc chuỗi URL OneLink hoàn chỉnh
adb -s <SERIAL> shell screencap -p /sdcard/pasted.png
adb -s <SERIAL> pull /sdcard/pasted.png ./pasted.png
python winrt_ocr.py ./pasted.png
```

---

## 2. Bắt mã OTP và nhập Numeric Keypad (Privy Auth Web3)

### Ma trận toạ độ bàn phím số Samsung Keypad (SM-G930F 1080x1920):
Khi màn hình yêu cầu nhập mã OTP (6 số) của Privy / Web3 Auth, bàn phím số nổi lên cố định ở nửa dưới màn hình:
```python
SAMSUNG_KEYPAD_COORDS = {
    "1": (140, 1266), "2": (410, 1266), "3": (672, 1266),
    "4": (147, 1444), "5": (411, 1444), "6": (672, 1444),
    "7": (146, 1620), "8": (409, 1620), "9": (672, 1620),
    "0": (409, 1800),
}

def enter_numeric_otp(adb, otp_code: str):
    for digit in otp_code:
        if digit in SAMSUNG_KEYPAD_COORDS:
            x, y = SAMSUNG_KEYPAD_COORDS[digit]
            adb.tap(x, y, delay=0.35)
```

### Chiến lược Polling OTP:
- **Gmail IMAP SSL (`imap.gmail.com:993`)**: Thời gian trả OTP gần như tức thì (<5s) từ sender `privy.io`.
- **Hotmail Microsoft Graph API**: BẮT BUỘC query cả hai folder `inbox` và `junkemail` với tham số `$orderby=receivedDateTime desc` vì email đăng ký mới từ hệ thống Web3 thường xuyên bị Microsoft phân loại nhầm vào Spam/Junk.

---

## 3. Reverse Engineering React Native Bundle từ APK
Khi cần xác định app có ô nhập referral code trực tiếp hay chỉ ăn attribution qua OneLink:
1. Kéo `base.apk` về: `adb pull /data/app/<package>-*/base.apk`
2. Đọc trực tiếp `assets/index.android.bundle`:
```python
import zipfile

with zipfile.ZipFile("base.apk") as z:
    for name in z.namelist():
        if "bundle" in name:
            content = z.read(name).decode("utf-8", errors="ignore")
            # Tìm kiếm từ khóa referral / promo code
            # ...
```
- Nếu chỉ tìm thấy `Have a referral code?` trong chuỗi onboarding mà không có endpoint redeem riêng, app phụ thuộc 100% vào dynamic link / deep link OneLink khi install lần đầu.

---

## 4. Cô lập thiết bị Farm khi chạy Ad-hoc Automation
- Tránh xung đột với các ca nuôi nick tự động (Feed/Follow/Upload cron):
  - Luôn kiểm tra danh sách máy rảnh: kiểm tra thư mục `C:/Users/Kibe/.codex/device-locks/`.
  - Khởi động `device_lock_keeper.py start --machine <N> --project "..." --ttl 120` để duy trì lock heartbeat trước khi thao tác APK.
