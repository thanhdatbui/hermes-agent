# Unified Cross-Host Avatar Management & Auto-Resolve Machine Mapping

## 1. Bối cảnh & Hiện tượng (2026-09-18)
- **Tình huống**: Hợp nhất hiển thị và quản lý TikTok Dashboard trên máy Kibe (cổng 1905) cho cả hai cụm farm:
  - Farm Kibe: Máy 1..80 (dải host `kibe`).
  - Farm Admin: Máy 201..280 (dải host `admin`).
- **Nguy cơ giẫm chân**: Khi hợp nhất database theo dõi (`tiktok_tracker.db`), nếu script watchdog upload avatar chạy theo kiểu cũ (quét mọi máy thiếu avatar) thì máy Kibe sẽ cố gửi lệnh điều khiển máy Admin hoặc ngược lại.
- **Hiện tượng lệch Excel vs TikTok thật**:
  - File Excel con (`Tik5.xlsx` máy 42 `@seifeespe23`) ghi `Avatar = OK`.
  - Nhưng trên TikTok thật nick vẫn mang avatar mặc định hệ thống (`musically-maliva-obj/1594805258216454`).
  - Watchdog cũ đọc từ Excel bỏ qua không up avatar, dẫn tới nick không bao giờ có avatar.

---

## 2. Giải pháp Kiến trúc: Single Source of Truth & Auto-Resolve Machine

### A. Dashboard Database là Chân lý Duy nhất (Source of Truth)
- Web Dashboard (`tiktok_dashboard.py`) & Tracker (`tiktok_account_tracker.py`) trích xuất link avatar qua thẻ HTML hydration `__UNIVERSAL_DATA_FOR_REHYDRATION__`.
- Hàm `is_default_avatar(avatar_url)` phát hiện chính xác:
  - Chứa `musically-maliva-obj` hoặc `1594805258216454` hoặc URL rỗng $\rightarrow$ `has_avatar = False`.
  - URL avatar tuỳ chỉnh của người dùng $\rightarrow$ `has_avatar = True`.
- Cập nhật bảng `farm_account_info` lưu ánh xạ `(username, may, tik, host_id)`.

### B. Cơ chế Tự Đối Chiếu Số Máy (Auto-Resolve Machine ID)
Thay vì chia tách file database hay sinh nhiều tool riêng, watchdog ca tối (`post_evening_avatar_watchdog.py`) tự động đối chiếu số máy trước khi kích hoạt batch:

```python
# Tra cứu máy từ SQLite Database theo host_id
c.execute("""
    WITH Ranked AS (
        SELECT s.username, s.status, s.has_avatar,
               ROW_NUMBER() OVER (PARTITION BY s.username ORDER BY s.id DESC) as rn
        FROM snapshots s
    )
    SELECT m.may, r.has_avatar, r.status
    FROM farm_account_info m
    LEFT JOIN Ranked r ON m.username = r.username AND r.rn = 1
    WHERE m.tik = ? AND m.host_id = ?
    ORDER BY m.may
""", (tik, current_host_id))
```

- **Quy tắc phân vùng phần cứng**:
  - **Trên Kibe (`host_id == 'kibe'`)**: Chỉ xử lý các máy $1 \le \text{may} \le 80$. Mọi nick thuộc máy $\ge 200$ của Admin bị tự động bỏ qua.
  - **Trên Admin (`host_id == 'admin'`)**: Chỉ xử lý các máy $201 \le \text{may} \le 280$. Mọi nick thuộc máy $\le 80$ của Kibe bị tự động bỏ qua.

---

## 3. Pitfall: Lệch Ánh Xạ Slot Đứt Đoạn Trên File Master Admin (`sync-tik-workbooks.py`)
- **Triệu chứng**: File tổng Admin `taikhoan_dat_v2_updated .xlsx` có các nick Row 8 (Tik 8) và Tik 7 nhưng các file `Tik8.xlsx` và `taikhoan_run_safe.xlsx` của Admin lại để trống (0 nick Tik 8).
- **Nguyên nhân**: Dàn máy Admin nhập liệu theo đợt nên mỗi máy chỉ có 3–4 dòng rời rạc (chưa đủ 8 dòng tuần tự). Script cũ đếm dòng tịnh tiến (`slot_index += 1`) nên gán nhầm dòng thứ 3 vào Tik 3 thay vì Tik 8.
- Khắc phục chuẩn hóa:
  - Trong `sync-tik-workbooks.py`, đọc giá trị Cột B (`Folder Video`). Nếu có giá trị $1 \le \text{folder} \le 8$ thì ưu tiên lấy làm `explicit_slot`.
  - Giúp đồng bộ chính xác 100% tài khoản Row 8 vào đúng `Tik8.xlsx` và `taikhoan_run_safe.xlsx` mà không phụ thuộc vào việc máy có đủ 8 dòng liên tiếp hay không.

---

## 4. Pitfall: Daily Farm Tracker Bị Sót Cụm Admin Do Candidates Break Loop (2026-09-19)
- **Hiện tượng**: Báo cáo Telegram `daily-tiktok-farm-tracker` (07:00) chỉ quét được 605 nick thay vì 882 nick, user thắc mắc "Sao tổng quét ít v quét cả 2 farm kibe vs admin mà".
- **Nguyên nhân**: Hàm `load_farm_accounts()` trong `tiktok_account_tracker.py` dùng vòng lặp tìm `excel_path` đầu tiên rồi `break`:
  ```python
  candidates = [
      "D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx",
      "D:/Taadaa/tiktok-luot nuoi acc/data/taikhoan_run_safe.xlsx",
  ]
  ```
  Khiến script chỉ nạp 605 nick của dải máy 1..80 (Kibe), bỏ rơi 277 nick của dải máy 201..280 (Admin).
- **Quy tắc chuẩn hóa Data Aggregation Toàn Farm**:
  - Mọi script thống kê toàn farm (Tracker, Check-live, Stock) khi chạy chế độ mặc định (không chỉ định file cụ thể) **BẮT BUỘC duyệt gộp tất cả các file safe tồn tại**:
    ```python
    target_paths = [
        "D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx",
        "D:/OneDrive/TaadaaData/admin/taikhoan_run_safe.xlsx",
    ]
    ```
  - Khử trùng theo `username` (`str(account_id).strip().lstrip('@')`) và kết hợp dải máy (Kibe 1..80 + Admin 201..280) để đảm bảo tổng số lượng phản ánh đúng 100% quy mô thực tế toàn farm.
