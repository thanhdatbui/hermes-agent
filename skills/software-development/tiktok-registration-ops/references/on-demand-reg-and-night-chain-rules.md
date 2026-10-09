# Quy trình Reg TikTok On-Demand theo Ca & Chuỗi Đêm Tuần Tự (11/09/2026)

## 1. Kiến trúc Chuỗi Ban Đêm Mới (Sequential Night Chain)
Bỏ hoàn toàn việc chạy batch Reg TikTok ồ ạt ban đêm (Phase 2a cũ). Chuỗi đêm chạy tuần tự hoàn toàn:
1. **00:00:** Phase 1 - Ca 4 Feed Row 7/8 (chạy 2 phiên: P1 lúc 00:00 và P2 lúc 01:30, kết thúc ~02:20).
2. **Ngay sau khi Ca 4 hoàn tất:** Phase 2 - Reg Gmail tự động (`run_all.ps1`).
3. **Ngay sau khi Reg Gmail hoàn tất:** Phase 3 - Add 2FA TikTok (`run_batch_live_2fa.py`).
- Mọi phase nối tiếp nhau tự động, không phụ thuộc giờ cứng.

## 2. Quy trình On-Demand Reg TikTok theo từng Ca nuôi
Thay vì reg tập trung ban đêm, hệ thống chuyển sang cơ chế cấp phát theo nhu cầu (Just-in-Time):
1. **Preflight kiểm tra slot Row của Ca đó:**
   - Khi bắt đầu Ca (ví dụ Ca 1 chạy Row 1/2), runner đọc `taikhoan_run_safe.xlsx` để phát hiện máy nào bị trống acc (`ID is None` hoặc rỗng).
   - Máy đã có acc -> chạy Feed + Follow bình thường.
   - Máy thiếu acc -> tách ra đưa vào luồng reg bù.
2. **Auto Hotmail Fallback:**
   - Kiểm tra kho `gmail_clean_v2.xlsx` của máy đó.
   - Nếu máy chưa có sẵn mail hoặc hết mail chưa dùng -> gọi tool `buy_hotmail.py` (ưu tiên BoxTaiKhoan, fallback CloneFBIG) tự mua mail OAuth2 và nạp vào workbook cho máy.
3. **Reg TikTok cho máy thiếu:**
   - Gọi `Tiktok_Reg` (`social_reg_v1.py`) nhắm đúng các máy đang thiếu acc.
   - Reg thành công -> ghi nhận vào `taikhoan_dat_v2_updated .xlsx` -> sync sang `taikhoan_run_safe.xlsx`.
   - Nick mới sẵn sàng cho phiên 2 hoặc ca kế tiếp.

## 3. Pitfall quan trọng khi đếm slot máy (Bug fix)
- Trong `scripts/tiktok_target_eligibility.py`: Khi đếm `machine_counts[m]`, **chỉ đếm các dòng có TikTok ID thật** (`if email and tiktok_id`). 
- Tuyệt đối KHÔNG đếm dòng trống (`ID is None`) vì sẽ khiến các máy đã tạo sẵn 8 dòng slot trong Excel bị hiểu nhầm là đã đủ 8 acc và bị bỏ qua không bao giờ reg thêm.
