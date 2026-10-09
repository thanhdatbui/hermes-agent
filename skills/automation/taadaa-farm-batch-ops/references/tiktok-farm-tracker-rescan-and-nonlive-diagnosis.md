# TikTok Farm Tracker: Chẩn Đoán Nick Non-LIVE & Cơ Chế Quét Bổ Sung (Rescan)

## 1. Hiện Tượng & Nguyên Nhân Chênh Lệch Nick Trên Dashboard
Khi Web Dashboard (`D:/Taadaa/tools/tiktok_dashboard.py`) hoặc Daily Tracker hiển thị tổng nick quét (VD: >1.000) lớn hơn số nick `LIVE` (VD: 927), **KHÔNG ĐƯỢC KẾT LUẬN VỘI LÀ NICK DIE**:

1. **Trạng thái `PENDING` (chưa quét):**
   - Các nick được import khởi tạo vào DB `snapshots` hoặc `farm_account_info` từ các đợt đồng bộ danh sách cũ (dải máy Admin, slot mới) nhưng chưa từng được worker chạy quét qua TikTok.
2. **Trạng thái `ERROR` (timeout / nghẽn proxy):**
   - Khi request profile bị rớt mạng, proxy chết hoặc timeout, hệ thống tạm ghi nhận `ERROR`. Thực tế tài khoản vẫn sống (`HTTP 200`).
3. **Hiện tượng False `NOT_FOUND` do Bot Check:**
   - TikTok trả về trang HTML rỗng hoặc challenge SlardarWAF mà không có thẻ `__UNIVERSAL_DATA_FOR_REHYDRATION__`. Bộ bóc tách naive sẽ gán nhãn `NOT_FOUND` dù tài khoản hoàn toàn tồn tại.
   - **Quy tắc đối soát O(1):** Kiểm tra trực tiếp URL `https://www.tiktok.com/@<username>` qua curl/urllib. Nếu trả về HTTP 200 thì nick vẫn LIVE.

---

## 2. Kiến Trúc Chuẩn Cho `tiktok_account_tracker.py`

### A. Hàm `load_farm_accounts`: Hỗ trợ `only_non_live` & fallback DB
Signature chuẩn:
```python
def load_farm_accounts(
    excel_path: Optional[str] = None,
    machines: Optional[List[str]] = None,
    limit: Optional[int] = None,
    only_non_live: bool = False,
    db_path: Optional[Union[str, sqlite3.Connection]] = None,
) -> List[Dict]:
```

**Chi tiết luồng xử lý:**
1. Khi `only_non_live=True`:
   - Mở DB `db_path` (mặc định `D:/Taadaa/data/tiktok_tracker.db`). Nếu là `sqlite3.Connection`, dùng trực tiếp; nếu là đường dẫn string, mở và đóng an toàn.
   - Truy vấn danh sách nick có snapshot mới nhất khác `LIVE`:
     ```sql
     WITH Ranked AS (
         SELECT username, status, ROW_NUMBER() OVER (PARTITION BY username ORDER BY timestamp DESC, id DESC) as rn
         FROM snapshots
     )
     SELECT username FROM Ranked WHERE rn = 1 AND status != 'LIVE';
     ```
   - Tra cứu schema bảng `farm_account_info` (nếu tồn tại) để lấy metadata dự phòng: `may`, `video_posted` (hoặc `video`), `device_id`.
2. Khi đọc file Excel:
   - Nếu `only_non_live=True`, bỏ qua (`continue`) các username không nằm trong tập non-live.
3. Sau khi đọc xong file Excel:
   - Nếu `only_non_live=True`, duyệt tiếp các nick non-live từ DB mà chưa có trong Excel (`seen_users`). Bổ sung vào kết quả với `may` và `video_posted` lấy từ `farm_account_info`.
   - Áp dụng bộ lọc `machines` và `limit` đồng nhất.

### B. Hàm quét trung tâm `run_scan`: Hỗ trợ Auto-Retry (Pass 2)
Tách module quét thành hàm độc lập để test và vận hành linh hoạt:
```python
def run_scan(
    accounts: List[Dict],
    workers: int = 5,
    use_proxy: bool = True,
    auto_retry: bool = True,
    fetch_fn: Optional[callable] = None,
) -> List[Dict]:
    if not accounts:
        return []

    _fetch = fetch_fn or (lambda u: fetch_profile(u, use_proxy=use_proxy))

    def _worker(acc):
        username = acc['username']
        profile = _fetch(username)
        merged = dict(acc)
        merged.update(profile)
        return merged

    max_workers = min(workers, len(accounts)) if accounts else 1
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        stats_list = list(executor.map(_worker, accounts))

    failed_indices = [
        i for i, item in enumerate(stats_list)
        if item.get('status') in ['ERROR', 'RATE_LIMITED', 'NOT_FOUND']
    ]

    # Điều kiện Auto-Retry: Có lỗi và tỷ lệ lỗi < 50% tổng số nick
    if auto_retry and failed_indices and (len(failed_indices) < 0.5 * len(stats_list)):
        print(f"[AUTO-RETRY] Pass 1 hoàn thành với {len(failed_indices)}/{len(stats_list)} nick non-live/error (< 50%).")
        print(f"[AUTO-RETRY] Khởi động Pass 2 quét bổ sung với proxy mới xoay vòng...")
        retry_accounts = [accounts[i] for i in failed_indices]
        retry_workers = min(workers, len(retry_accounts)) if retry_accounts else 1
        with ThreadPoolExecutor(max_workers=retry_workers) as executor:
            retry_results = list(executor.map(_worker, retry_accounts))

        recovered = 0
        for orig_idx, new_res in zip(failed_indices, retry_results):
            if new_res.get('status') == 'LIVE':
                stats_list[orig_idx] = new_res
                recovered += 1
            elif stats_list[orig_idx].get('status') in ['ERROR', 'RATE_LIMITED'] and new_res.get('status') == 'NOT_FOUND':
                stats_list[orig_idx] = new_res
        print(f"[AUTO-RETRY] Pass 2 hoàn thành: cứu sống thành công {recovered}/{len(failed_indices)} nick về LIVE.")
    elif failed_indices and auto_retry:
        print(f"[AUTO-RETRY] Bỏ qua: {len(failed_indices)}/{len(stats_list)} nick bị lỗi (>= 50%), nghi ngờ sự cố mạng/proxy diện rộng.")

    return stats_list
```

### C. CLI Arguments trong `main()`
```python
parser.add_argument("--rescan-non-live", action="store_true", default=False, help="Chỉ quét bổ sung các nick có status mới nhất != 'LIVE'")
parser.add_argument("--auto-retry", action="store_true", default=True, help="Tự động quét lại các nick bị lỗi (mặc định: True)")
parser.add_argument("--no-auto-retry", dest="auto_retry", action="store_false", help="Tắt tính năng tự động retry pass 2")
```

---

## 2.1. Truy Vết & Phân Bổ Sở Hữu Nick Lạ / Die Giữa Hai Farm (Kibe vs Admin)
Khi phát hiện nick DIE/NOT_FOUND (như `@symmotqc1r2`), Coordinator cần định vị O(1) nick thuộc farm nào mà không được đoán mò:
1. **Dải máy quy ước:**
   - Máy `1..80`: Farm Kibe (`host_id='kibe'`).
   - Máy `201..280`: Farm Admin (`host_id='admin'`).
2. **Truy vấn Workbook & DB:**
   - Tra cứu trong `D:/OneDrive/TaadaaData/admin/taikhoan_run_safe.xlsx` và `kibe/taikhoan_run_safe.xlsx`.
   - Tra cứu nguồn tạo nick: `taikhoan_dat_v2_updated .xlsx` (cột Email, Mật khẩu, Ngày reg).
3. **Hiện trường Remote ADB sang Admin:**
   - Dàn máy Admin được kết nối qua `D:/Taadaa/tools/remote_admin_adb.py` hoặc `adb -H 192.168.110.119`.
   - Nếu cổng `5037` của Admin bị đóng (do Admin restart máy làm tắt background process), tuyệt đối không phán đoán máy bị hỏng phần cứng mà hướng dẫn Admin chạy lại `D:\OneDrive\Taadaa_Sync_Shared\bat_remote_adb_admin.bat` (Run as administrator) để mở lại kết nối mạng LAN.

---

## 3. Quy Chuẩn Unit Test (`test_tiktok_account_tracker.py`)
- **100% Mocked**: Toàn bộ test dùng SQLite `:memory:` hoặc mock object. Tuyệt đối không gọi network hay file thật trên disk nếu không cô lập qua `tmp_path`.
- **Test case `load_farm_accounts_only_non_live`:**
  1. Tạo DB in-memory gồm bảng `snapshots` chứa nick A (`LIVE`), nick B (`ERROR`), nick C (`PENDING`).
  2. Bảng `farm_account_info` chứa nick C với metadata `may='10', video_posted=5`.
  3. File Excel chứa nick A và nick B.
  4. Gọi `load_farm_accounts(excel_path=..., only_non_live=True, db_path=conn)`:
     - Phải lọc bỏ nick A (`LIVE`).
     - Phải nạp nick B từ Excel.
     - Phải bổ sung nick C từ DB kèm `may='10'` và `video_posted=5`.
- **Test case `run_scan_auto_retry`:**
  - Mock `fetch_fn` trả về 3 LIVE và 1 ERROR ở Pass 1, sang Pass 2 trả về LIVE.
  - Kiểm tra `stats_list` cuối cùng đã được cập nhật LIVE và call count của `fetch_fn` đúng số lần retry.

---

## 4. Kỷ Luật Worker Turn Budget Khi Thực Thi
- **Pitfall**: Đọc file quá nhiều lần và chạy query thăm dò lắt léo trong terminal sẽ làm cạn kiệt budget lượt gọi (tool limit) trước khi kịp áp dụng patch.
- **Kỷ luật**:
  1. Phase PLAN (tối đa 2 tool calls): Xác định chính xác vị trí cần chèn trong `tiktok_account_tracker.py` và `test_tiktok_account_tracker.py`.
  2. Phase EXECUTE (ngay lượt tiếp theo): Gọi `patch` hoặc `write_file` để ghi code và test vào file.
  3. Phase VERIFY (1 tool call): Chạy pytest xác nhận kết quả.

---

## 5. Cơ Chế Delta Biến Động (Follower / Heart) Trên Dashboard & Cạm Bẫy `rn = 1` vs `rn = 2`
### A. Bản chất hiện tượng Delta sụt giảm bất thường (VD: từ +500 tim về +1)
- **Cơ chế mặc định của `tiktok_dashboard.py`**:
  - Dashboard dùng Window Function `ROW_NUMBER() OVER (PARTITION BY username ORDER BY timestamp DESC) as rn`.
  - Phép so sánh delta hiện tại là `r1.rn = 1` so với `r2.rn = 2`.
- **Cạm bẫy khi chạy nhiều lượt scan trong ngày**:
  - `rn = 2` **KHÔNG PHẢI là mốc 24h trước hay mốc ngày hôm qua**, mà là **đợt scan liền trước đó**.
  - Ví dụ thực tế:
    - Đợt 1 quét lúc `07:03`: So với tối hôm trước (23/09) -> Delta toàn farm tăng mạnh (+514 tim, +37 follower).
    - Đợt 2 quét lúc `07:36` (sau 33 phút): `rn = 2` bị đẩy thành mốc `07:03`. Trong 33 phút chỉ có duy nhất 1 nick tăng 1 tim -> Delta KPI toàn farm sụt về `+1`.
- **Nguyên tắc giải thích & chẩn đoán cho Coordinator**:
  - Khi user thắc mắc vì sao sáng thấy tăng nhiều mà sau đó delta chỉ còn `+1` hay `0`, kiểm tra ngay lịch sử scan trong SQLite:
    ```bash
    python -c "import sqlite3; conn = sqlite3.connect('file:D:/Taadaa/data/tiktok_tracker.db?mode=ro', uri=True); cur = conn.cursor(); cur.execute('SELECT substr(timestamp, 1, 16) as scan_ts, count(*), sum(heart), sum(follower) FROM snapshots GROUP BY scan_ts ORDER BY scan_ts DESC LIMIT 5'); print(cur.fetchall())"
    ```
  - Nếu có 2 đợt scan cùng ngày cách nhau ngắn, khẳng định rõ: delta hiển thị trên dashboard phản ánh mức tăng trong vài chục phút giữa 2 lần quét, không phải mất dữ liệu hay farm tụt tương tác 24h.
- **Giải pháp kiến trúc khi cần so sánh chuẩn 24h / Ngày hôm trước**:
  - Không dùng `r2.rn = 2` thuần túy.
  - Thay vào đó, định nghĩa baseline `r2` là snapshot mới nhất có `date(timestamp) < date(r1.timestamp)` (chốt ngày hôm trước) hoặc `timestamp <= datetime(r1.timestamp, '-24 hours')`.
