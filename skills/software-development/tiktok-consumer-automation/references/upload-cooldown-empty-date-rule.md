# Upload Cooldown Policy: Tài Khoản Để Trống Ngày Tạo (Chốt 2026-09-21)

## Vấn đề
Khi chạy upload hook cho các hàng nick mới (`row_index >= 5`, ví dụ Tik 5, Tik 6), script `upload_preflight.py` gọi hàm `check_upload_cooldown_eligibility(...)` kiểm tra ngày tạo tài khoản từ workbook master `taikhoan_dat_v2_updated .xlsx`.
Nếu cột `NGÀY TẠO` (hoặc các cột fallback 8, 9, 7) có giá trị `None` hoặc rỗng:
- Logic cũ: kích hoạt fail-closed trả về `(False, "account_creation_date_unverifiable", None)` dẫn đến hàng loạt máy bị bỏ qua đăng video (ví dụ ca Row 5 bỏ qua 45 máy).

## Quy định & Hướng xử lý chuẩn của User
- **Tài khoản để trống ngày tạo trong Excel = Cho phép đăng luôn (`return True, "ok", current_date`)**:
  - Lý do: Những nick này đã được reg từ trước đó rất lâu, đã đủ tuổi ngâm an toàn.
  - CẤM chặn đăng hoặc fail-closed với lý do `account_creation_date_unverifiable`.
- **Tài khoản có ngày tạo xác định**:
  - Tuân thủ công thức cooldown 3 ngày tuổi (`created_date + timedelta(days=3)`).
