---
name: airdrop-referral-automation
description: Automate Web3 airdrops, ref links, Privy & OTP on Android.
tags: [airdrop, referral, android, web3, otp, appsflyer, privy]
---
# Airdrop & Referral Automation Suite

Kỹ năng điều phối, tự động hóa quy trình cày Referral, Airdrop Web3 và Testnet/Mainnet đa tài khoản trên dàn máy thật Android Phone Farm.

---

## 1. Trích xuất OneLink / Deep-Link từ Android Clipboard (Không dùng Logcat)
Nhiều ứng dụng Web3/Airdrop (React Native, Flutter) khi bấm "Copy Link / Share" không hiển thị text link trên giao diện mà ghi ngầm vào Android clipboard.
Lệnh `service call clipboard 1` trên Android 7/8 trả về Parcel thô rất khó giải mã. 

### Kỹ thuật Paste & Read qua Trình duyệt:
1. Mở Samsung Browser / Chrome vào trang trắng:
   ```bash
   adb -s <SERIAL> shell am start -a android.intent.action.VIEW -d "about:blank" -p com.sec.android.app.sbrowser
   ```
2. Tap vào thanh URL (`x=429, y=149` trên màn S7 1080x1920).
3. Gửi keyevent Paste: `adb -s <SERIAL> shell input keyevent 279`
4. Chụp ảnh màn hình và chạy WinRT OCR đọc chuỗi URL OneLink / Invite link chính xác 100%.

### Kỹ thuật trích xuất trọn vẹn qua Native Share Sheet:
Nhiều app khi bấm "Invite Friends / Share" sẽ kích hoạt `android.intent.action.SEND` mở ứng dụng Tin nhắn (Messages) hoặc bộ chia sẻ hệ thống:
1. Tap vào nút "Invite Friends" / "Share".
2. Chụp màn hình khung soạn thảo tin nhắn / share sheet.
3. OCR sẽ đọc được toàn văn mẫu tin nhắn mời (bao gồm cả invite code tường minh lẫn link OneLink đầy đủ trước khi bị rút gọn `...` trên UI app).

---

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
