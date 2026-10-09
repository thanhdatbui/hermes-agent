# Quy Tắc Kiểm Tra Ngày Tạo & Cooldown Tuổi Nick Khi Đăng Video (Upload Preflight)

## Ngữ cảnh
- Hệ thống upload hook (`upload_preflight.py` trong `tiktok-luot nuoi acc`) thực hiện kiểm tra điều kiện tuổi tài khoản (`check_upload_cooldown_eligibility`) trước khi cho phép máy đăng video lên TikTok đối với các hàng mới (`row_index >= 5`, ví dụ Tik 5, Tik 6).
- Dữ liệu ngày tạo được đọc từ workbook master `taikhoan_dat_v2_updated .xlsx` (cột `NGÀY TẠO` hoặc fallback cột 8, 9, 7).

## Quy định của User (Chốt 2026-09-21)
1. **Tài khoản để trống ngày tạo:**
   - ĐẶC BIỆT LƯU Ý: Với các tài khoản trong file Excel để trống ngày tạo (`NGÀY TẠO` là `None` hoặc chuỗi rỗng), **ĐƯỢC PHÉP ĐĂNG LUÔN** (`return True, "ok", current_date`).
   - Lý do: Đây là các tài khoản đã được reg từ trước đó rất lâu, đã đủ thời gian ngâm/dưỡng nick.
   - **CẤM:** Không được fail-closed chặn đăng với lý do `account_creation_date_unverifiable` khi ngày tạo bị trống.

2. **Tài khoản có ngày tạo xác định:**
   - Tuân thủ quy tắc cooldown: `min_allowed_date = created_date + timedelta(days=CREATION_COOLDOWN_DAYS)` (mặc định 3 ngày tuổi).
   - Nếu `current_date < min_allowed_date`, chặn với lý do `account_cooling_period_until_<YYYY-MM-DD>`.
   - Nếu `current_date >= min_allowed_date`, cho phép đăng bình thường.
