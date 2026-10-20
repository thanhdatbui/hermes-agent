# Phân Tích Hiện Trường Lệch Follow & Cạm Bẫy Queue Shifting Unit Test (2026-10-18)

## 1. Hiện Tượng Lệch Đối Soát Web vs Script Báo Cáo Cũ (Tàn Dư Trước Commit)

### A. Triệu chứng
Người vận hành nhận được thông báo từ Watchdog:
```text
  + Đối soát TikTok Web (+0 Following thật | Lệch -2 so với script báo 2):
    - M23 (@tranngan8642) : script 2 lượt - web 0 lượt - lệch (-2)
```
Người vận hành thắc mắc: *"Tại sao lại lệch? Script có bước check nhả follow rồi mà?"*

### B. Quy trình chẩn đoán sai lầm (Anti-Pattern)
- Vội vàng kết luận script "chỉ nhìn Optimistic UI rồi đếm 2" hoặc "bộ check nhả không hoạt động".
- Vội vàng sửa code trên repo chính trong khi tính năng đã được vá hoàn chỉnh.

### C. Quy trình chẩn đoán chuẩn xác O(1)
1. **Kiểm tra timestamp ca chạy thực tế:**
   - Đọc `run_manifest.json` hoặc `summary.txt` trong `runtime/kibe/live/<date>/<run>/machines/machine_<M>/...`.
   - Xác định chính xác ca chạy diễn ra vào thời điểm nào (ví dụ: `2026-10-16T23:25:23Z` = 06:25 sáng 17/10).
2. **Đối chiếu với `git log`:**
   - Kiểm tra commit chứa bản vá check nhả follow (Path B Pull-to-refresh & Follow Dominance, ví dụ commit `d328458` lúc 19:01 ngày 17/10).
   - Nếu timestamp ca chạy **trước** commit fix: Đây là ca cũ chạy trên mã nguồn cũ, watchdog quét lại cửa sổ 7 ngày và báo cáo, không phải lỗi của mã nguồn hiện tại!

---

## 2. Hiện Tượng Lệch Âm Dương Bù Trừ Do Lệch Mốc Snapshot Watchdog (Snapshot Window Cutoff Misalignment)

### A. Triệu chứng
Người vận hành thấy báo cáo 2 phiên liên tiếp trong cùng một ca bị lệch cực lớn theo kiểu "bù trừ âm dương":
```text
Ca 2 Phiên 1: +0 Following thật | Lệch -29 so với script báo 29 (Web 0 lượt)
Ca 2 Phiên 2: +34 Following thật | Lệch +22 so với script báo 12 (Web 34 lượt)
```
Người vận hành hoang mang: *"Clgt lệch kinh khủng v? Bị TikTok bão nhả acc à?"*

### B. Cơ chế gốc rễ (Root Cause)
1. **Ca chạy trễ hoặc watchdog cào trễ:**
   - Ví dụ Phiên 1 quy ước `12:00 - 14:00`, nhưng ca thực tế chạy tới 14:30 hoặc watchdog đến 16:01 mới cào snapshot web (`timestamp = 16:01:21`).
2. **Kẹp cứng mốc SQL `query_end_iso`:**
   - Trong `reconcile_cluster_following`: `query_end_iso = session_end_iso + 10m` (`14:10:00`).
   - Query SQL tìm snapshot: `WHERE LOWER(username) = LOWER(?) AND timestamp <= '14:10:00'`.
   - Vì snapshot vừa cào là `16:01:21` > `14:10:00`, SQL **bỏ qua hoàn toàn snapshot mới** và lùi về snapshot sáng sớm (ví dụ `07:04:13`).
   - Cả `latest_row` lẫn `baseline_row` đều lấy snapshot `07:04:13` $\rightarrow$ `web_delta = 0` $\rightarrow$ **Báo lệch âm nặng (-29)**.
3. **Hiệu ứng cộng dồn sang Phiên 2:**
   - Đến Phiên 2 (`14:00 - 18:00`), `query_end_iso` là `18:10:00` nên nhận được snapshot mới nhất.
   - Nhưng khi tìm `baseline_row` (`timestamp <= 14:10:00`), do giữa `07:04` và `14:10` không có snapshot nào, SQL lại lùi về `07:04:13`.
   - Kết quả: Web delta của Phiên 2 tính gộp cả lượng follow của Phiên 1 + Phiên 2 $\rightarrow$ **Báo lệch dương nặng (+22)**.
4. **Đối chiếu thực tế:**
   - Tổng script 2 phiên: $29 + 12 = 41$.
   - Tổng web tăng từ sáng đến cuối ca: $41$.
   - **Tỷ lệ khớp thực tế: 100% (41/41)**, acc ăn follow sạch, không bị nhả một lượt nào.

### C. Quy trình kiểm chứng nhanh O(1)
Chạy script kiểm tra trực tiếp bảng `snapshots` trong `D:/Taadaa/data/tiktok_tracker.db`:
```python
import sqlite3
conn = sqlite3.connect("file:D:/Taadaa/data/tiktok_tracker.db?mode=ro", uri=True)
cur = conn.cursor()
# Lấy snapshot sáng sớm và snapshot sau ca chạy của nick
for u in target_usernames:
    cur.execute("SELECT timestamp, following FROM snapshots WHERE LOWER(username) = LOWER(?) ORDER BY id DESC LIMIT 5", (u,))
    print(u, cur.fetchall())
```
Nếu `following` cuối ca trừ sáng sớm khớp đúng tổng script của cả 2 phiên $\rightarrow$ Đây là lệch ảo do window cutoff, acc an toàn 100%.

---

## 2. Cạm Bẫy Tiêu Thụ Queue XML Dump Của FakeAdapter Trong Unit Tests

### A. Cơ chế gây lỗi (Queue Shifting Bug)
Trong các test suite offline (như `test_mode1_search_follow.py`):
- Fixture `_ok_followed_seq(fake, uid)` đẩy vào `fake.xml_queue` chính xác 6 XML dump cho mỗi UID:
  + Dump 0: Icon tìm kiếm
  + Dump 1: Ô input tìm kiếm
  + Dump 2: Kết quả tìm kiếm (card profile)
  + Dump 3: Profile cá nhân (nút Follow)
  + Dump 4: Kiểm tra trạng thái sau tap
  + Dump 5: Kiểm tra trạng thái sau reload / xác nhận không nhả
- Khi hàm `_reload_profile` gọi `pull_to_refresh_profile(adapter, sleep_after=...)` mà **không truyền `xml_text`**:
  + Hàm `pull_to_refresh_profile` gọi `_screen_size(adapter, xml_text)`.
  + Vì `FakeAdapter` không có method `screen_size()`, `_screen_size` gọi `adapter.dump_ui()` để đọc bounds của root layout.
  + Thao tác này âm thầm **tiêu thụ mất 1 dump XML (Dump 5)** từ `fake.xml_queue`!
- Khi test tiếp tục chạy để verify trạng thái sau reload:
  + Script gọi `_dump()` $\rightarrow$ đọc trúng Dump 6 (vốn là Dump 0 của UID tiếp theo)!
  + Dẫn tới lỗi `identity mismatch sau re-entry verify` hoặc `search input not proven focused with uid for @b`.

### B. Giải pháp chuẩn mực
1. **Trong `_reload_profile`:** Khi `is_mock = True`, bắt buộc truyền `xml_text` giả lập vào `pull_to_refresh_profile`:
   ```python
   mock_xml = '<hierarchy><node bounds="[0,0][1080,1920]"/></hierarchy>' if is_mock else None
   return pull_to_refresh_profile(adapter, sleep_after=0.0 if is_mock else random.uniform(3.0, 4.5), xml_text=mock_xml)
   ```
2. **Trong `FakeAdapter` (nếu cần):** Định nghĩa rõ method `screen_size(self) -> tuple[int, int]` trả về `(1080, 1920)` để tuân thủ 100% interface của `FollowAdapter`.

---

## 4. Cạm Bẫy Quy Chụp "Nuốt Mốc Ngày Cũ" Khi Ca Chạy Sớm Trước Snapshot Sáng (Ca 06:00 vs Snapshot 07:00)

### A. Hiện tượng và Cạm bẫy chẩn đoán sai
- Dashboard hiển thị: `⚡ Tiến độ hôm nay: Bot +35 lượt (Web 📈 Tổng tăng: +54)`.
- Agent vội vàng kết luận: "Query SQL của Dashboard so với hôm qua nên nuốt trọn số lượng của ngày hôm trước, cần fix SQL".
- **Hậu quả nếu sửa query theo snapshot sáng sớm (07:04):** Toàn bộ các nick chạy Ca 1 Phiên 1 lúc 06:00 sáng sẽ bị tính Web Delta = 0, xóa sổ thành tích ca sớm của toàn farm!

### B. Cơ chế thực tế
1. **Lịch chạy farm lệch với mốc snapshot sáng:**
   - Ca 1 Phiên 1 chạy từ **06:00 - 07:00**.
   - Snapshot watchdog toàn farm cào lúc **07:04**.
   - Ca 1 Phiên 2 chạy từ **08:00 - 09:30**.
   - Tại mốc 07:04, các máy chạy Phiên 1 đã hoàn thành và số following đã tăng thật trên TikTok.
   - Do đó, mốc so sánh với ngày hôm trước (`timestamp < max_dt`) trên Dashboard là **hoàn toàn chính xác** để gom trọn thành quả cả ngày (từ 00:00 đến 23:59).
2. **Nguyên nhân thật sự khiến Tool < Web (+35 vs +54):**
   - **Runner Timeout:** Khi `run_follow` bị timeout ở bước follow-hook, watchdog ghi nhận `status: 'timeout', followed_count: 0`. Máy thực tế đã bấm và TikTok đã nhận follow trước khi timeout, nhưng DB không được cộng (ví dụ M23 ở P1).
   - **Follow tự nhiên trong Feed:** Các lượt follow khi lướt video For-You / Friends của feed-session không được tính vào `internal_follows` nếu watchdog chỉ đếm follow chéo.
   - **TikTok Web trễ / dồn số:** TikTok đồng bộ lượt follow từ phiên trước hoặc nhả/bù lượt.

### C. Quy trình Triage chuẩn
1. Kiểm tra timestamp ca chạy trong `runtime/kibe/live/<date>/`: xác định ca chạy trước hay sau 07:00 sáng.
2. Kiểm tra XML dump thật trên máy (`verify_profile/ui.xml`) tại thời điểm sau phiên để đối chiếu số `Đã follow` trực tiếp trên app với số Web cào.
3. Tuyệt đối KHÔNG sửa mốc query SQL của Dashboard khi chưa kiểm chứng lịch ca 06:00.

---

## 5. Cạm Bẫy Timeout 120s Trong Closeout Gate Với Test Suite Dài

### A. Triệu chứng
Khi chạy `closeout_gate.py --repo ... --files ...`:
```text
  · Chạy tests: python -m pytest follow_runner/tests/test_mode1_search_follow.py follow_runner/tests/test_verify_follow.py --tb=short -q
  ✘ Tests timeout sau 120s
  ✘ Focused tests FAILED (0 failed, 1 errors) in 120.0s
```

### B. Nguyên nhân
- `closeout_gate.py` có hard timeout cho pytest: `pytest_timeout = min(timeout_seconds, 120)`.
- `test_mode1_search_follow.py` có 65 tests, trong đó có các test lướt feed và ngâm profile gọi `time.sleep` thật (dwell time 6-12s, delay 2.5-5s), chạy đơn lẻ đã mất ~90s.
- Khi `--files` gom nhiều file dẫn tới pytest gom 2 test suite lớn cùng lúc $\rightarrow$ tổng thời gian vượt quá 120s và gate fail-fast.

### C. Giải pháp
- Khi closeout, **phân rã task theo phạm vi O(1)** (tối đa <= 2 files, <= 30 dòng).
- Không gom chung các target module có test suite nặng vào cùng 1 lần review closeout gate.
- Các test case offline cần triệt để mock `time.sleep` thông qua `monkeypatch.setattr("time.sleep", lambda s: None)` để test chạy dưới 5s.
