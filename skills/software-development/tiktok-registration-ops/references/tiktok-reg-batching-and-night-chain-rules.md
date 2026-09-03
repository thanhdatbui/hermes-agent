# TikTok Registration Batching & Night Chain Rules (2026-08-28)

## 1. Quy tắc giới hạn tài khoản & Lọc Target
- **Giới hạn cứng 6 acc/máy**:
  - Quét bảng tracking (`taikhoan_dat_v2_updated .xlsx`), đếm số lượng TikTok ID hiện có của từng máy.
  - Máy đã có **$\ge 6$ TikTok ID** $\rightarrow$ **Loại vĩnh viễn** khỏi mọi đợt reg tiếp theo cho tới khi xuất lô và reset máy.
- **Điều kiện Target kép (Bắt buộc)**:
  - Máy chưa đủ 6 acc (`< 6 TikTok ID`).
  - Phải còn mail nguồn trong `gmail_clean_v2.xlsx` **chưa từng xuất hiện** trong tracking.
  - Thiếu 1 trong 2 điều kiện $\rightarrow$ Bỏ qua (Skip).
- **Daily Cooldown & Khóa nguyên tử**:
  - 1 máy chỉ reg tối đa **1 lần thành công/ngày**.
  - Áp dụng cơ chế **Check-and-Reserve nguyên tử** (`reserve_machine_reg_slot()`) kèm UUID token trước khi khởi chạy runner để chống xung đột giữa các worker.

---

## 2. Chuỗi Pipeline Ban Đêm (Night Chain 01:00 AM)
- **Cơ chế tuần tự (Sequential Blocking)**:
  - **Phase 1 (01:00 AM)**: Chạy reg nguồn Gmail mới (`run_gmail_batch`) và đợi hoàn tất 100%.
  - **Phase 2**: Tự động gọi `_run_all_targets.py` chỉ sau khi Phase 1 đã kết thúc hoàn toàn (không chạy song song, không hẹn giờ cố định trùng nhau).
- **Cấu hình an toàn Farm**:
  - `--max-targets 30`: Giới hạn tối đa 30 acc/đợt chạy đêm để tránh TikTok quét đột biến lưu lượng.
  - `--max-workers 6`: Chạy cuốn chiếu 6 máy song song (giãn cách 2–8s/máy), hoàn thành 30 máy trong ~25–35 phút trước 01:45 AM (trước khi cron nuôi acc hoạt động).
