# Cross-Farm Feature Parity & Preflight Auto-Reg (Kibe vs Admin)

## 1. NGUYÊN TẮC BẤT BIẾN: PARITY 100% GIỮA CÁC CỤM FARM
- **Quy tắc cốt lõi**: Mọi tính năng, preflight, tự động bù tài khoản (auto-reg ensure accounts), watchdog, heal, dọn dẹp... hoạt động trên cụm Kibe (`machine 1-80`) BẮT BUỘC PHẢI HOẠT ĐỘNG HOÀN TOÀN TƯƠNG ĐƯƠNG trên cụm Admin (`machine 200+`).
- **CẤM TUYỆT ĐỐI**:
  - Không được đặt điều kiện loại trừ cụm Admin như `if cluster_name == "kibe"` trong các script điều phối (`tiktok_runner.py`, `feed_session_watchdog.py`, v.v.).
  - Không được tự ý viện cớ "tác vụ dài, sợ xung đột port/lock" để né tránh chạy tự động trên Admin. Tool `ensure_row_accounts.py` và `taadaa_host.py` đã hỗ trợ đầy đủ multi-host config (`admin.yaml` / `kibe.yaml`).

## 2. PREFLIGHT ENSURE ACCOUNTS (TỰ ĐỘNG REG BÙ ROW)
- Trước mỗi ca/phiên chạy nuôi feed (Row 1..8):
  - Hệ thống tự động quét danh sách máy trong `taikhoan_run_safe.xlsx` của cả 2 cụm (`kibe` và `admin`).
  - Nếu phát hiện máy trống tài khoản ở Row đó:
    1. Kiểm tra kho mail `gmail_clean_v2.xlsx` của cụm tương ứng.
    2. Tự động cấp mail Zin (hoặc mua Hotmail bù nếu thiếu).
    3. Kích hoạt batch reg TikTok cho danh sách máy thiếu.
    4. Cập nhật master tracking và đồng bộ vào `taikhoan_run_safe.xlsx` trước khi phiên feed bắt đầu.

## 3. THỐNG KÊ FOLLOW CHÉO (MODULE 1 / MODULE 2) TRONG BÁO CÁO TELEGRAM
- `[Module 2 (Anchor): X | Module 1 (Bù): Y]` đếm số lượt follow thành công thực tế của từng module.
- Khi nick chưa đủ $\ge 10$ video hoặc rơi vào ngày Nghỉ dưỡng sinh (Organic Rest):
  - Feed session chặn an toàn ngay trước khi gọi `run_follow.py` (`under-10-videos-follow-disabled` hoặc `organic-rest-day-pure-feed`).
  - Khi đó cả Module 2 và Module 1 đều ghi nhận 0 lượt, toàn bộ số máy được ghi nhận chính xác tại dòng `Bỏ qua (N): Đang dưỡng sinh (...); Chưa đủ 10 video (...)`.
