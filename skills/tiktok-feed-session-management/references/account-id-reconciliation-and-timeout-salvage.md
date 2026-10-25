# Quy Chuẩn Đối Soát Theo Account ID (Username) & Hồi Phục Timeout (Timeout Salvage)

## 1. Bối Cảnh & Vấn Đề Gốc Rễ (Root Cause)
Trước đây, watchdog đối soát dữ liệu hành động (follow/upload) giữa script farm và TikTok Web (SQLite `snapshots`) dựa vào `account_row_index` (Row 1, 2, ...):
- **Lệch acc ở cữ chạy hỗn hợp:** Khi máy chạy ca hỗn hợp (`active_row = -1`) hoặc cữ phục hồi lệch row (ví dụ Máy 40 chạy Row 2 `@nguyenkhoi1403`), nếu script không truyền row hoặc watchdog fallback về Row 1 (`@charakrh768`), số liệu Web của nick Row 1 (= 0) bị so với số liệu script của Row 2 (= 3) $\to$ Watchdog báo oan: "script 3 lượt - web 0 lượt - lệch (-3)", gây báo động giả nick bị nhả follow.
- **Bảng `snapshots` không có `row`:** SQLite `D:/Taadaa/data/tiktok_tracker.db` chỉ lưu `(username, following, timestamp)`. Bản chất dữ liệu đối soát là thuộc về Account, không thuộc về Row máy.
- **Timeout làm mất dữ liệu follow:** Khi child runner chạm `follow-timeout` (ví dụ sau 20 phút), exception handler cũ gán cứng `followed_count = 0` và xóa trắng danh sách `followed`, làm mất 10-15 lượt follow thật đã thực hiện thành công trước đó (ví dụ M37 đã follow 11 nick thật nhưng bị báo 0).

## 2. Quy Chuẩn Kỹ Thuật (Architecture Invariants)

### A. Gắn Định Danh Account ID Xuyên Suốt Pipeline
1. **Runner Output (`multi_machine_feed_session.py`):**
   - Mọi payload `follow_result.json` và `upload_result.json` BẮT BUỘC có trường `"account": account.expected_username`.
   - Trong `_write_follow_result` và `_write_upload_result`, nếu payload thiếu `account` thì tự động fallback lấy từ `child_ctx.account` hoặc `child_ctx.config.get("_account")`.
2. **Parser & Merger (`parser.py` & `merger.py`):**
   - `parse_run_all` trích xuất `"account"` từ `follow_result.json`, `upload_result.json`, và cào regex từ `summary.txt` (`"username": "@..."` hoặc `"expected": "..."`).
   - `merge_follow_result`, `merge_upload_result`, `merge_machine_result` bảo toàn trường `"account"` và `"row"` qua các lần chạy trong ca.
3. **Watchdog Reconciliation (`feed_session_watchdog.py`):**
   - `reconcile_cluster_following` ưu tiên tuyệt đối dùng `f_acc` (ID account) để query DB:
     `SELECT following, timestamp FROM snapshots WHERE LOWER(username) = LOWER(?)`
   - Chỉ fallback về `f_row` hoặc slot đầu tiên khi không có `account`.
   - Sau khi có `val = username`, watchdog tra ngược lại `machine_slots` để gắn nhãn `[Tik N] (@username)` đẹp mắt và chuẩn xác 100%.

### B. Cơ Chế Vớt Dữ Liệu Khi Timeout (Timeout Salvage)
Khi child runner gặp timeout (`TimeoutExpired` / `follow-timeout`), CẤM gán cứng `followed_count: 0`.
BẮT BUỘC đọc file state `follow_state_{machine}_row_{row}.json`:
```python
state_p = Path(r"D:\Taadaa\tiktok-follow\runs\state") / f"follow_state_{account.machine}_row_{account.account_row_index}.json"
if state_p.exists():
    s_data = json.loads(state_p.read_text(encoding="utf-8"))
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    salvaged_follows = [
        uid for uid, ts in (s_data.get("followed") or {}).items()
        if str(ts).startswith(today_str)
    ]
```
Gán `followed_count = len(salvaged_follows)` và `followed = salvaged_follows` vào payload kết quả.

### C. Đồng Bộ Cron Mirror
- File `scripts/feed_session_watchdog.py` có mirror bắt buộc tại `scripts/hermes_cron/feed_session_watchdog.py`.
- Unit test `test_feed_session_watchdog_and_hermes_cron_sync` kiểm tra byte-by-byte giữa 2 file. Bất kỳ sửa đổi nào trên file chính BẮT BUỘC phải copy/sync ngay sang mirror.
