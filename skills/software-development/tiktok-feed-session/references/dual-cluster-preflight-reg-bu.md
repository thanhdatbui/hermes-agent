# Dual-Cluster Preflight Reg Bù & Watchdog Reporting Rules

## 1. Cơ chế Tự Động Preflight Reg Bù (On-Demand Account Provisioning)
Trước mỗi ca nuôi feed (Ca 1..4), `tiktok_runner.py` (Phase 9 runner) bắt buộc phải kiểm tra và tự động kích hoạt reg bù nếu cụm máy thiếu tài khoản ở Row mục tiêu:
- **Nguyên tắc vận hành:** Thiếu acc ở Row nào -> Tự động gọi `python D:/Taadaa/tools/ensure_row_accounts.py <row>`.
- **Luồng xử lý trong `ensure_row_accounts.py`:**
  1. Quét file `taikhoan_run_safe.xlsx` của cụm tương ứng để tìm danh sách máy trống nick ở Row đó.
  2. Kiểm tra kho mail `gmail_clean_v2.xlsx`. Nếu thiếu, tự động mua Hotmail OAuth2 qua `buy_hotmail.py`.
  3. Kích hoạt `_run_all_targets.py` để reg TikTok chỉ riêng cho các máy thiếu này.
  4. Merge kết quả vào `taikhoan_dat_v2_updated .xlsx` và đồng bộ sang `taikhoan_run_safe.xlsx`.
  5. Bắn thông báo Telegram `📋 [PREFLIGHT REG BÙ ROW N]`.
  6. Sau khi có nick, runner mới khởi chạy nuôi feed cho cụm.

## 2. Cạm bẫy Host-Awareness trong Multi-Cluster Runner
- **Nguyên nhân bug fallback mù:**
  `ensure_row_accounts.py` chạy độc lập ngoài repo, cần nạp `taadaa_host.py` để đọc biến môi trường `TAADAA_HOST_CONFIG` (trỏ tới `kibe.yaml` hoặc `admin.yaml`).
  Nếu `sys.path` thiếu thư mục chứa `taadaa_host.py` (`D:/Taadaa/tools` hoặc `D:/Taadaa/tiktok-luot nuoi acc/python_runner`), `import taadaa_host` sẽ bị `ImportError` âm thầm.
  -> Hậu quả: `get_host_info()` fallback cứng về `kibe`, kiểm tra nhầm file Excel của Kibe thay vì Admin. Kibe đã đủ nick thì báo "Toàn bộ máy đã đầy đủ tài khoản" và exit 0, bỏ rơi hoàn toàn cụm Admin.
- **Quy tắc phòng ngừa:**
  Mọi script dùng chung giữa 2 cụm máy (Kibe & Admin) khi đọc host config phải đảm bảo `D:/Taadaa/tools` nằm trong `sys.path` trước khi `import taadaa_host`.

## 3. Cạm bẫy Watchdog Silent Cluster Skip (`feed_session_watchdog.py`)
- **Hiện tượng:**
  Trong vòng lặp duyệt `CLUSTERS = [kibe, admin]`, nếu cụm Admin không có run folder (`D:/Taadaa/runtime/admin/live/YYYY-MM-DD/row-X-...`), code cũ `continue` âm thầm.
  -> Báo cáo gửi về Telegram chỉ hiển thị khối `【FARM KIBE - MÁY 1-80】`, hoàn toàn biến mất khối `【FARM ADMIN】`, khiến User tưởng hệ thống bỏ quên hoặc watchdog bị lỗi.
- **Quy tắc báo cáo:**
  Báo cáo tổng kết ca phải luôn thể hiện trạng thái của cả 2 cụm:
  - Nếu cụm có run folder: In đầy đủ chi tiết Feed / Follow / Upload.
  - Nếu cụm chưa có run folder do thiếu nick ở Row đó: Phải ghi rõ `🏢 【FARM ADMIN - MÁY 201-280】: Trống slot / Chưa có nick Row N (Đang chờ reg bù)` để đảm bảo tính minh bạch O(1).
