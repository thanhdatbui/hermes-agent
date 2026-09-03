# Nightly Batch Controls & 6 Account Quota per Machine (2026-08-28)

## 1. Giới Hạn Cứng 6 Acc TikTok / Máy (Farm 80 máy = 480 accs)
- **Quy tắc trần**: Mỗi máy vật lý chỉ được tạo tối đa 6 tài khoản TikTok. Đủ 6 tài khoản thì máy bị loại vĩnh viễn khỏi detector (`_detect_clean.py`) cho tới khi reset/re-flash máy.
- **Tiêu chuẩn cấp target kép**:
  1. `machine_account_count < 6`: Đếm số TikTok ID thực tế trong bảng tracking (`taikhoan_dat_v2_updated .xlsx`).
  2. Còn mail nguồn hợp lệ chưa dùng: Mail trong `gmail_clean_v2.xlsx` chưa hề xuất hiện trong cột tracking.
  - Thiếu 1 trong 2 điều kiện $\rightarrow$ Bỏ qua target ngay từ khâu selection.

## 2. Thông Số Vận Hành Batch Đêm (01:00 AM)
- **Chuỗi liên hoàn blocking**: Cron `night-chain-reg-pipeline` (01:00) chạy theo 2 Phase nối đuôi:
  - **Phase 1**: Tạo nguồn Gmail mới (`run_gmail_batch`).
  - **Phase 2**: Tự động gọi `_run_all_targets.py` sau khi Phase 1 hoàn tất và flush CSDL.
- **Giới hạn số lượng**: Cấu hình `--max-targets=30` (mỗi đêm reg tối đa 30 acc để tránh TikTok để ý).
- **Concurrency an toàn**: Hạ xuống `--max-workers=6` chạy cuốn chiếu song song 6 máy, giãn cách 2–8s, không chạy ồ ạt 40 luồng.

## 3. Khóa Liên Tiến Trình & Check-and-Reserve
- **Fail-Closed Cooldown**: Bất kỳ lỗi schema hoặc parse JSON trong file cooldown đều từ chối cấp slot để bảo vệ an toàn farm.
- **Check-and-Reserve bằng Token UUID**:
  - `reserve_machine_reg_slot(stt, serial)`: Lấy token trước khi mở app reg.
  - Thất bại / Crash: Giải phóng qua `release_machine_reg_reservation(stt, token)` trong `finally`.
  - Thành công: Ghi nhận cooldown chính thức bằng `record_machine_reg_success(stt, serial)`.
