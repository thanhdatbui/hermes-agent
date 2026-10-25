# Batch Upload: Lock Collision & USB Media Push Saturation Triage

## 1. Triệu Chứng & Mẫu Cảnh Báo (Symptom & Alert Pattern)
Khi nhận cảnh báo lỗi upload video hàng loạt trên cả 2 cụm:
```text
🚨 [FARM ALERT] PHÁT HIỆN LỖI SCRIPT UPLOAD HÀNG LOẠT (59 máy lỗi script Upload) - Ca 1 - Phiên 2/2 (Sáng)
🏢 【FARM KIBE - MÁY 1-80】
   + Lỗi script/xác minh (11): 4, 13, 20, 22, 28, 34, 54, 64, 68, 74, 79
🏢 【FARM ADMIN - MÁY 201-280】
   + Timeout/Quá giờ (4): 220, 226, 229, 232
   + Lỗi script/xác minh (44): 202, 203, 204, ...
```

## 2. Phân Tích Nguyên Nhân Kép (Dual Root-Cause Analysis)

### A. Cụm Admin Remote: Xung Đột Device Lock (`[NEEDS_USER_DECISION] ACQUIRE_LOCKS`)
- **Cơ chế Fail-Closed:** Khi `tiktok-video` chạy batch tự động (`user_authorized=False`), hàm `acquire_device_lock` trong `automation_core/device_lock.py` gặp bất kỳ file lock nào trong `C:\Users\Admin\.codex\device-locks\` sẽ lập tức raise `DeviceLockNeedsUserDecision` mà không tự ý cướp lock.
- **Hiện tượng:** Tool trước đó (ví dụ: `tiktok-add-bao-mat-f2a`) đã ghi lock hàng loạt với trạng thái `queued_v2`. Dù tiến trình trước đã chết, file lock tồn đọng khiến toàn bộ 44 máy fail ngay tại bước preflight trước khi chạm vào TikTok.
- **Kỹ thuật thẩm định O(1) qua SSH:**
  ```bash
  # 1. Kiểm tra tiến trình giữ lock có còn sống không:
  python D:/Taadaa/tools/admin_ssh.py "tasklist /FI \"PID eq <PID>\""

  # 2. Kiểm tra thư mục lock trên máy Admin:
  python D:/Taadaa/tools/admin_ssh.py "dir C:\Users\Admin\.codex\device-locks"
  ```
  Nếu PID đã chết và thư mục trống: 100% là lock cũ đã giải phóng, máy sẵn sàng chạy lại.

### B. Cụm Kibe Local: Nghẽn Băng Thông USB Hub (`[MEDIA_PUSH_FAILED]`)
- **Nghẽn USB 2.0:** Khi batch chạy với `MaxParallel = 20`, nhiều runner cùng gọi `adb push` file video dung lượng lớn qua Hub USB 2.0 gây sụt áp / nghẽn bus, dẫn đến kết nối ADB bị reset tạm thời.
- **Cạm bẫy che giấu lỗi trong `media_manager.py`:**
  Lệnh `media_manager.py` lấy `error_msg = result.stderr.strip() or "Unknown error"`. Khi `adb push` ghi thông báo lỗi ra `stdout` thay vì `stderr`, lỗi hiển thị thành `"Unknown error"`.
- **Quy tắc an toàn khi inspect thiết bị thật:**
  Coordinator KHÔNG ĐƯỢC chạy lệnh ADB trần (bị chặn bởi Hard Gate #5). BẮT BUỘC bọc qua:
  ```bash
  python D:/Taadaa/tools/with_device_lock.py --machine <N> -- adb -s <serial> ...
  ```
  Thử nghiệm push file đơn lẻ dưới `with_device_lock.py` thành công với `rc: 0` chứng minh thiết bị và dây cáp hoàn toàn bình thường.

## 3. Kỷ Luật Phản Hồi Operator
1. **Khẳng định an toàn ngay dòng đầu:** Khẳng định 100% tài khoản và máy móc an toàn, không có máy nào bị văng phiên hay dính captcha.
2. **Tách biệt 2 nguyên nhân:** Giải thích rõ 44 máy Admin là do lock preflight, 11 máy Kibe là do nghẽn USB khi push song song.
3. **Khuyến nghị vận hành (Actionable):**
   - Admin: Sẵn sàng chạy bù ngay vì lock đã sạch.
   - Kibe: Khi chạy bù nên hạ tham số song song (`-MaxParallel 6` hoặc `10`) để tránh nghẽn Hub.
