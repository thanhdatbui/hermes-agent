# Chẩn đoán & Triage khi Watchdog báo 'Trạng thái download: ⚪ Đang dừng'

## 1. Bản chất cơ chế Watchdog
Cronjob `farm-render-download-watchdog` định kỳ mỗi 1h kiểm tra tiến trình `download_by_niche.py` qua `psutil.process_iter`:
- Nếu có tiến trình mang tên `download_by_niche.py` hoặc `download_all_sources.py` -> 🟢 Đang chạy.
- Nếu không tìm thấy tiến trình -> ⚪ Đang dừng.

**LƯU Ý CỐT LÕI**: "Đang dừng" **KHÔNG ĐỒNG NGHĨA VỚI BỊ CRASH / LỖI**. Rất nhiều trường hợp là batch đã hoàn tất việc quét và tải toàn bộ dải folder được giao và tự động thoát an toàn (Exit 0).

---

## 2. Quy trình O(1) Chẩn đoán trạng thái thực sự

### Bước 1: Tra cứu nhanh phân bổ trạng thái trong `state.db`
Đường dẫn DB:
- Kibe: `C:\CodexRuntime\tiktok-video\state.db` (ưu tiên SSD) hoặc `D:\CodexRuntime\tiktok-video\state.db`.
- Admin: `D:\CodexRuntime\tiktok-video-machine2\state.db`.

Chạy truy vấn:
```python
import sqlite3
conn = sqlite3.connect(r'C:\CodexRuntime\tiktok-video\state.db')
c = conn.cursor()
c.execute('SELECT status, count(*) FROM folders GROUP BY status')
print('Status summary:', c.fetchall())
c.execute('SELECT count(*) FROM folders WHERE video_count >= 30')
print('Qualified (>=30):', c.fetchone()[0])
```

**Đánh giá:**
- Nếu `pending == 0` và `downloading == 0` (hoặc `reserved == 0`): Toàn bộ dải folder (ví dụ 1..640 ở Kibe) đã được duyệt xong.
- Đếm số lượng `complete` (đạt 60-65 video) và `complete_partial` (đạt 30-59 video): Đây là các folder đã đủ điều kiện render/nuôi nick an toàn.

### Bước 2: Kiểm tra timestamp & Folder kết thúc trong log `report-*.jsonl`
Trong thư mục runtime (`C:\CodexRuntime\tiktok-video\`), đọc 5 dòng cuối của file `report-YYYYMMDD-HHMMSS.jsonl` mới nhất:
- Xem trường `folder` ở dòng cuối cùng có phải là folder cuối cùng của farm không (ví dụ `folder: 640`).
- Xem trường `checked_at` để biết thời điểm chính xác batch hoàn thành quét.

### Bước 3: Phân tích nhóm `insufficient_pool` (nếu có)
Nếu còn một số folder mang trạng thái `insufficient_pool`:
```python
c.execute('SELECT folder_num, niche, video_count, source_channel FROM folders WHERE status = "insufficient_pool"')
print(c.fetchall())
```
- Xác nhận `video_count == 0`: Các folder này chưa tải video nào do pool nguồn hiện tại thiếu kênh YouTube Shorts tiếng Việt đạt chuẩn $\ge 30$ video.
- Đây là hành vi bảo vệ an toàn của downloader (thà dừng chứ không trộn kênh hoặc tải video rác).

---

## 3. Mẫu báo cáo phản hồi User chuẩn mực
Khi user hỏi "Sao download dừng?":
1. **Khẳng định ngay**: Batch không bị crash mà đã chạy hết toàn bộ dải folder (ví dụ 640/640) và kết thúc lúc HH:MM.
2. **Số liệu định lượng**:
   - Số folder đạt chuẩn $\ge 30$ video (vd 622/640 folder ~ 97.2%).
   - Tổng số video gốc mp4 sẵn sàng phục vụ render.
3. **Giải thích các folder còn lại**: Liệt kê số lượng folder `insufficient_pool` (0 video) theo niche và lý do hết nguồn qualified.
4. **Đề xuất hành động**: Toàn farm đã đủ video render; nếu cần đạt 100% thì kích hoạt auto-discover cào bù thêm nguồn cho danh sách niche còn thiếu.
