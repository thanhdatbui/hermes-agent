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

## 3. Cạm Bẫy Timeout 120s Trong Closeout Gate Với Test Suite Dài

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
