---
name: tiktok-upload-ui-recovery
description: TikTok Samsung UI recovery.
tags: [tiktok, upload, uiautomator, adb, battery, recovery]
---

# TikTok Upload UI Recovery

## 1. Nguyên Tắc Cốt Lõi
- **Tra cứu sự cố O(1):** `python D:/Taadaa/tools/inspect_machine.py <N>`. Cấm quét đĩa diện rộng.
- **Không bấm tay ADB:** Lỗi UI phát sinh phải được encode vào script xử lý tự động của `automation-core` hoặc `Tiktok-video`.
- **Chụp ảnh trước khi Teardown:** Luôn screencap và OCR xác nhận kết quả trước khi đưa máy về HOME.

## 2. Quy Trình Khắc Phục Lỗi Upload Thường Gặp
- **Popup Pin Yếu / Dialog che:** Bật giả lập sạc pin qua ADB: `dumpsys battery set ac 1` và `dumpsys battery set level 100`.
- **Kẹt Splash / Màn đen:** Kiểm tra kết nối ADB và khởi động lại package bằng script chuẩn.
- **Che nút Post / Keyboard Overlay:** Gửi lệnh ẩn bàn phím hoặc tap theo tọa độ chuẩn hóa đã được test.

## 3. Danh Mục Tham Khảo Chi Tiết
- Chi tiết các case xử lý UI: xem danh mục tham khảo trong thư mục `references/` của skill.
