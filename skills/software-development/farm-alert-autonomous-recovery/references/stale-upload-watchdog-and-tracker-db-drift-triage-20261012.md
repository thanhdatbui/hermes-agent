# Stale Upload Watchdog & Tracker DB Drift Triage Protocol (12/10/2026)

Hướng dẫn đối soát và xử lý khi nhận cảnh báo tiến độ upload toàn farm (`daily-stale-upload-accounts-watchdog` - job_id `5ad19a65f7ef`).

---

## 1. Hiện tượng & Bản chất Lệch Dữ liệu (DB Drift / Stale Timestamp)
- **Hiện tượng:** Bản tin đối soát gửi về Telegram hiển thị ngày tham chiếu cũ trong ngoặc `(2026-10-10)` dù thời điểm chạy thực tế là ngày hôm nay (`12/10/2026`).
- **Nguyên nhân cốt lõi:**
  - Script audit `D:/Taadaa/tools/audit_stale_upload_accounts.py` cấu hình mặc định:
    ```python
    DEFAULT_DB_PATH = r"D:/OneDrive/TaadaaData/tiktok_tracker.db"
    FALLBACK_DB_PATH = r"D:/Taadaa/data/tiktok_tracker.db"
    ```
  - Trong thực tế vận hành, Single Source of Truth thời gian thực được cronjob cào dữ liệu `cron_tiktok_daily_tracker.py` ghi nhận là **`D:/Taadaa/data/tiktok_tracker.db`**.
  - File trên OneDrive chỉ là bản sao lưu tĩnh cũ hơn (dừng ở ngày 10/10). Do `DEFAULT_DB_PATH` tồn tại trên đĩa, script không bao giờ kích hoạt fallback, dẫn tới tính toán `days_stale` và số lượng active/stale bị kẹt theo mốc thời gian quá khứ.

---

## 2. Quy trình Đối soát Nhanh O(1) (Instant Sanity Check)
1. **Kiểm tra mtime và MAX(timestamp) giữa 2 DB:**
   ```bash
   python -c "
   import sqlite3
   for p, lbl in [('D:/OneDrive/TaadaaData/tiktok_tracker.db', 'OneDrive'), ('D:/Taadaa/data/tiktok_tracker.db', 'Runtime')]:
       c = sqlite3.connect(p).cursor()
       c.execute('SELECT MAX(timestamp) FROM snapshots')
       print(f'{lbl}: {c.fetchone()[0]}')
   "
   ```
2. **Chạy audit cưỡng bức qua DB runtime:**
   ```bash
   python D:/Taadaa/tools/audit_stale_upload_accounts.py --db D:/Taadaa/data/tiktok_tracker.db --days 7 --critical-days 14
   ```
   So sánh kết quả để lấy số liệu thực tế ngày hôm nay (Active, Stale, Zero-video).

---

## 3. Quy tắc Phân loại 3 Tầng khi Triage Top Nick Bị Đóng Băng (>14 ngày)

Khi nhận danh sách cảnh báo các nick không tăng video >14 ngày, **CẤM** suy diễn vội vàng hoặc sửa mò code upload. Bắt buộc phân loại theo 3 nhóm nguyên nhân độc lập:

### Tầng 1: Lỗi Phần cứng / ADB Thiết bị (Hardware Disconnect)
- **Kiểm tra:** Chạy `python D:/Taadaa/tools/inspect_machine.py <N>` cho các máy xuất hiện trong top đầu (ví dụ Máy 10, Máy 30).
- **Dấu hiệu:** ADB trả về `device not found` hoặc `offline` (tuột cáp USB, sập nguồn, treo hub).
- **Kết luận:** Nick không thể đăng video do máy vật lý mất kết nối từ ngày máy bắt đầu offline. Cần thao tác vật lý (cắm lại cáp/bật nguồn), không phải lỗi runner.

### Tầng 2: Quy hoạch Cụm Máy / Trạng thái Dưỡng (Cohort / Host Status)
- **Kiểm tra:** Gom nhóm danh sách stale theo `host_id` (`kibe` vs `admin`) và phân bố số ngày kẹt.
- **Dấu hiệu:** Phần lớn nick stale (ví dụ >80%) tập trung ở cụm `admin` (Máy 201–280), đều dừng ở mức 1–2 clip và cùng kẹt đúng một mốc số ngày (ví dụ 22 ngày).
- **Kết luận:** Đây là các tài khoản thuộc nhóm test ban đầu của Farm Admin, hiện đang trong chu kỳ dưỡng/ngâm hoặc đang chờ phân phối nguồn video render riêng biệt cho cụm Admin.

### Tầng 3: Lệch giữa Public Scraping Tracker vs File Sổ Cái Excel (Scrape Drift)
- **Kiểm tra:** Mở file `Tik<slot>.xlsx` tại dòng máy tương ứng, đọc cột `Video Đã Đăng` (cột 8) và so sánh với trường `video` trong database snapshot.
- **Dấu hiệu:**
  - Database snapshot ghi: `1 video`.
  - File Excel ghi: `3 video` hoặc `7 video` (trạng thái `OK`).
- **Kết luận:** Tracker cào dữ liệu qua web public TikTok (`__UNIVERSAL_DATA_FOR_REHYDRATION__`). Các clip mới đăng có thể đang bị xét duyệt, gắn cờ giới hạn hoặc đặt riêng tư nên không hiển thị công khai trên web. Thiết bị thực tế đã hoàn thành upload theo đúng sổ cái.
