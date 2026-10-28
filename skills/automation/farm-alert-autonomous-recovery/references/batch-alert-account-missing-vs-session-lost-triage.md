# Batch Alert: ACCOUNT_MISSING False Positive on P0 Session Lost Classification

## 1. Hiện Tượng & Triệu Chứng (Symptom Pattern)
Khi kết thúc một ca chạy batch Nuôi Feed hoặc Upload Hook, watchdog phát cảnh báo khẩn cấp:
```text
🚨 [BATCH ALERT: LỖI HỆ THỐNG] PHÁT HIỆN LỖI LAN RỘNG - 【FARM ADMIN / KIBE】
...
⚠️ [P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]: Phát hiện 1 máy dính lỗi login/mất phiên:
   • Máy M261: UploadHook: 2026-10-28 06:25:36,883 [ERROR] scripts.tiktok_workflow.state_machine: [ACCOUNT_SWITCHER_FAILED] select account failed: ACCOUNT_MISSING: expected account was not found...
```

## 2. Nguyên Nhân Gốc (Root Cause)
1. **Bẫy từ khóa `SESSION_LOST_KEYWORDS` trong `batch_aggregator.py`:**
   Danh sách `SESSION_LOST_KEYWORDS` chứa các từ khóa: `"account_missing"`, `"account-missing"`, `"account missing"`.
2. **Cơ chế phát sinh lỗi:**
   - Ca chạy được phân bổ cho một hàng tài khoản (ví dụ Row 2: `thuthanh2911`) mà máy đó chưa từng đăng nhập (chưa nạp đủ 8 slot vào Switcher).
   - Feed runner phát hiện thiếu nick, kích hoạt luồng auto-login recovery. Nếu tài khoản chưa có password (`PASS: None` trong workbook) và Hotmail không kịp trả OTP về hộp thư (`mailbox_otp_not_received`), tiến trình login recovery fail và máy kết thúc phiên.
   - Tiếp theo, ca upload hook chạy cùng hàng cũng không tìm thấy tài khoản trong Switcher, ghi nhận:
     `[ACCOUNT_SWITCHER_FAILED] select account failed: ACCOUNT_MISSING: expected account was not found.`
   - Watchdog bắt trúng từ khóa `"account_missing"`, hiểu nhầm là tài khoản vừa bị TikTok logout / văng phiên, và bắn alert P0.

## 3. Quy Trình Đối Soát & Triage Hiện Trường O(1)
Để xác minh đây là Báo động giả hay Mất phiên thật:

1. **Kiểm tra trạng thái phần cứng:**
   ```bash
   python D:/Taadaa/tools/inspect_machine.py <N>
   ```
   Xác nhận máy nghỉ an toàn (`Màn hình: OFF (Sleep/Dozing)`, `Focus: null`), Wi-Fi/Proxy kết nối chuẩn.

2. **Soi mắt đọc Switcher bằng WinRT OCR:**
   - Tìm file screenshot Switcher tại artifact của ca chạy gần nhất:
     `D:\Taadaa\runtime\<cluster>\live\<date>\<batch>\machines\machine_<N>\<run_id>\artifacts\...\feed-session-smoke\profile_preflight_switcher_3_guard\attempt_1\screen.png`
   - Chạy WinRT OCR (Lưu ý: truyền đường dẫn Windows backslash `\` để tránh lỗi Stream OpenAsync trên PowerShell):
     ```bash
     python D:/Taadaa/tools/run_winrt_ocr.py "D:\Taadaa\runtime\...\screen.png"
     ```
   - **Tiêu chuẩn kết luận:**
     - Nếu OCR trả về danh sách các nick khác vẫn đang đăng nhập bình thường trong Switcher (ví dụ 7 nick hiển thị đầy đủ, không có dialog lỗi/bắt đăng nhập lại) -> **BÁO ĐỘNG GIẢ (FALSE POSITIVE)**. Toàn bộ tài khoản hiện hữu trên máy hoàn toàn an toàn, chỉ là nick mục tiêu chưa từng được nạp vào máy.
     - Nếu màn hình là form "Đăng nhập vào TikTok" (0 nick trong switcher, session expired dialog) -> **MẤT PHIÊN THẬT (TRUE POSITIVE)**.

## 4. Hướng Xử Lý Khắc Phục (Remediation)
- Báo cáo rõ ràng cho User: Khẳng định ngay câu đầu tiên là **Báo động giả**, toàn bộ các nick hiện có trên máy không bị văng phiên.
- Đính kèm ảnh hiện trường qua `MEDIA:<path>` sau khi đã soi mắt kiểm tra qua WinRT OCR.
- Với nick bị thiếu (chưa nạp): Đối soát thông tin trong `taikhoan_dat_v2_updated .xlsx`. Nếu `PASS: None`, bổ sung password hoặc kiểm tra hòm thư Hotmail, sau đó nạp bù nick bằng script chuyên dụng:
  ```bash
  python D:/Taadaa/tiktok-log-in/scripts/reconcile_tiktok_accounts.py \
      --workbook "D:/OneDrive/TaadaaData/admin/taikhoan_run_safe.xlsx" \
      --machines <N> \
      --expected-username <nick> \
      --adb-path "C:/Program Files (x86)/xiaowei/tools/adb.exe" \
      --login-project "D:/Taadaa/Tiktok_Reg" \
      --allow-live-reconcile
  ```
