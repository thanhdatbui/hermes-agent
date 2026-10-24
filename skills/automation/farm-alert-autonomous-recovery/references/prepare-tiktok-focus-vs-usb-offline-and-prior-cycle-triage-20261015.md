# Triage Quy Trình: prepare-tiktok Focus Failure vs USB Transport Offline & Bẫy Cảnh Báo Lệch Chu Kỳ (2026-10-15)

## 1. Hiện Tượng & Căn Nguyên Kỹ Thuật

### A. Lỗi Focus `prepare-tiktok failed to focus TikTok after launch` thực chất là USB Offline
- **Triệu chứng:** Batch alert báo lỗi cụm: `Signature: focus-device-issue:prepare-tiktok failed to focus TikTok after launch` trên hàng loạt máy (ví dụ: M2, M8, M11, M43, M53, M60, M63, M67, M69, M77, M80).
- **Căn nguyên:** Khi runner gọi `am start` hoặc yêu cầu kiểm tra window focus qua `dumpsys window windows`, vi điều khiển USB 2.0 EHCI của host gặp micro-spike hoặc nghẽn bus khiến kết nối ADB bị ngắt giữa chừng. Lệnh shell ADB bị timeout hoặc đứt gãy socket trước khi TikTok kịp lấy focus, dẫn đến runner phân loại nhầm thành lỗi app focus (`focus-device-issue`).
- **Xác minh O(1):** Chạy `python D:/Taadaa/tools/inspect_machine.py <N>`. Nếu kết quả là `adb.exe: device '<serial>' not found`, thiết bị thực chất đã rớt vào cụm phần cứng `DEVICE_OFFLINE`, không phải lỗi app hay logic kịch bản.

### B. Bẫy Cảnh Báo Lệch Chu Kỳ (Prior-Cycle Stale Alarm Trap)
- **Triệu chứng:** Cảnh báo P0 khẩn cấp báo lỗi mất phiên: `[ACCOUNT_SWITCHER_FAILED] ACCOUNT_READY verify failed: ACCOUNT_VERIFY_MISMATCH: Profile did not show the expected account. Cần MANUAL_REVIEW: kiểm tra TikTok đã login chưa...` (ví dụ: Máy 55).
- **Cạm bẫy:** Batch alert hoặc watchdog gom lỗi có thể chậm pha, kích hoạt sau khi đợt chạy trước đó (ví dụ ca 12:00 row-3-120011) thất bại. Tuy nhiên, farm runner hoặc scheduler có thể đã tự động retry hoặc chạy tiếp lượt bổ sung kế tiếp (ví dụ 14:03 row-3-140050) và đã xử lý thành công hoàn toàn (`status: success`, `post_verified: true`).
- **Quy tắc điều tra O(1):**
  1. Kiểm tra danh sách thư mục chạy mới nhất trong `D:/Taadaa/runtime/kibe/live/<YYYY-MM-DD>/`: sắp xếp theo thời gian để lấy run folder mới nhất.
  2. Đọc file `upload_result.json` hoặc `report.json` của máy trong run folder mới nhất trước khi kết luận trạng thái.
  3. Nếu run mới nhất đã đạt `status: success` và có bằng chứng post/profile sạch, P0 alert là **STALE FALSE ALARM**, đã được hệ thống tự phục hồi.

## 2. Kỷ Luật Phản Hồi & Bằng Chứng
- **Không vội vàng can thiệp:** Khi gặp `ACCOUNT_VERIFY_MISMATCH`, tuyệt đối không xóa nick, không reset app, không đổi mật khẩu khi chưa đối soát thư mục run mới nhất.
- **Thẩm định bằng chứng:** Chạy WinRT OCR (`ocr_tool.py`) và `evidence_gate_verifier.py --pre-image <path> --allow-single-inspection --max-age 86400` lên ảnh kết quả (`post-published-surface.png` hoặc `account-switcher-profile.png`) để có bằng chứng cơ học xác thực.
- **Device Lock Safety:** Kiểm tra `recovery_lock_handoff.json` để chắc chắn lock đã được giải phóng (`lock_status: released`).
