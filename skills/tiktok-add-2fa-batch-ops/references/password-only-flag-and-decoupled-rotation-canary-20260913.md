# Cờ `--password-only` trong `run_capture_phase_b.py`: Tách Biệt Hoàn Toàn Luồng Đổi Mật Khẩu Khỏi Flow 2FA (13/09/2026)

## Bối cảnh & Vấn đề
- Trong các đợt chạy 2FA, bước `ensure_account_password_saved()` ban đầu được thiết kế như một bước phụ chạy cuối flow `execute_phase_b()`.
- Khi tài khoản đã có sẵn 2FA trong Workbook hoặc trên thiết bị, `execute_phase_b()` rơi vào nhánh `already-enabled`.
- Khi Operator ra lệnh kiểm chứng (canary) lại quy trình đổi mật khẩu trên tài khoản đã gặp lỗi trước đó (ví dụ máy 46, row 362), nếu chạy toàn bộ flow `run_capture_phase_b.py`, runner phát hiện 2FA đã kích hoạt nên có thể kết thúc sớm hoặc không bóc tách được riêng rẽ kết quả đổi mật khẩu.

## Giải pháp: Bổ sung cờ `--password-only`
- Thêm cờ CLI `--password-only` vào `run_capture_phase_b.py`:
  ```bash
  python python_runner/run_capture_phase_b.py \
    --machine <M> --serial <SERIAL> --expected-username <ID> --source-row <EXCEL_ROW> \
    --workbook-path "D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx" \
    --workbook-sheet "Tài Khoản" --password-only --live
  ```
- **Hành vi:**
  + Khởi tạo đầy đủ thiết bị, VPN gate, và adapter.
  + Nhảy thẳng vào `adapter.ensure_account_password_saved()`.
  + Gặp màn "Xác minh danh tính" ➔ Bấm Tiếp ➔ Gọi module đọc OTP Gmail/Outlook trên máy ➔ Gõ OTP ➔ Vào màn đổi pass ➔ Tạo pass ngẫu nhiên mạnh và cập nhật trực tiếp vào cột D (PASS) của file Excel.
  + Bỏ qua hoàn toàn việc kiểm tra/bật lại Authenticator 2FA, giúp kiểm chứng dứt điểm và độc lập 100% luồng đổi mật khẩu.
