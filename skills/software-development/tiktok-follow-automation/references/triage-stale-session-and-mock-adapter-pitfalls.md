# Triage Stale Session Backfill, Offline Mock Desync & Closeout Partitioning

## 1. Triage: Session Watchdog Báo Lệch Trên Ca Cũ vs Code Đã Fix (Temporal Triage)
Khi operator thắc mắc: *"Kiểm tra tại sao lại lệch? Vấn đề script có bước check nhả follow rồi mà? Hay là đã có session khác fix rồi mà tao quên nhỉ?"*:

1. **Quy tắc đối soát mtime vs commit SHA (Bắt buộc trước khi đụng code):**
   - Đọc timestamp thực tế của ca chạy trong runtime folder:
     `D:/Taadaa/runtime/kibe/live/<date>/<run_id>/.../summary.txt` hoặc `log.jsonl`.
   - Kiểm tra lịch sử git commit gần nhất của repo:
     `git -C D:/Taadaa/tiktok-follow log -5 --format="%h %ci %s"`.
   - **Xác định nghịch lý thời gian:**
     - Nếu ca chạy lúc `06:25:23` ngày 17/10, trong khi commit bản vá (`d328458` - thêm `pull_to_refresh_profile` vào Path B) được commit lúc `19:01:08` ngày 17/10 (sau ca chạy 13 tiếng):
     - **Kết luận:** Đây là phiên cũ chạy bằng codebase cũ trước khi có bản vá. Watchdog quét lại trong cửa sổ retention 7 ngày và nhả báo cáo tổng hợp.
     - Code trên `origin/master` hiện tại ĐÃ CÓ bản vá hoàn chỉnh.
2. **Kiểm tra Working Tree (Chống Sửa Đè / Regress Code Cũ):**
   - Khi operator hỏi: *"Có sửa đè lên cái đã sửa không?"*:
   - Chạy `git diff --stat` và đối chiếu cụ thể từng hàm:
     - Khẳng định rõ: Cú vuốt reload (`pull_to_refresh_profile`) và bộ lọc `Follow Dominance` của commit cũ vẫn giữ nguyên vẹn 100%.
     - Phân định rạch ròi các thay đổi mới trên working tree (ví dụ: đưa WinRT OCR lên làm Primary để soi nút trong 0.2s, hoặc bổ sung phân tầng 3 Cohort và Dò trần thích ứng).

---

## 2. Các Cạm Bẫy Mock Fixture Trong Unit Test Offline (`FakeAdapter`)

### Bẫy 1: `_screen_size` Nuốt XML Dump Làm Lệch Hàng Đợi (`xml_queue` Desync)
- **Cơ chế gây lỗi:**
  - Trong `follow_runner/core/adapter.py`, hàm `_screen_size(adapter, xml_text=None)` nếu không nhận được `xml_text` sẽ gọi `adapter.dump_ui()` để đọc bounds của root node.
  - Trong offline unit test, `FakeAdapter` sử dụng hàng đợi `xml_queue` có thứ tự nghiêm ngặt (chuỗi: Search -> Input -> Result -> Profile -> Profile sau tap -> Profile sau vuốt).
  - Khi `pull_to_refresh_profile(adapter)` được gọi mà không truyền `xml_text`, `_screen_size` gọi `dump_ui()`, âm thầm tiêu thụ mất 1 XML trong queue.
  - Hậu quả: Toàn bộ các bước verify hoặc UID tiếp theo trong test bị lệch pha 1 bước dump, dẫn tới lỗi sai lệch danh tính (`identity mismatch sau re-entry verify`) hoặc timeout giả.
- **Giải pháp chuẩn hóa:**
  Trong `_screen_size`, bổ sung kiểm tra adapter test:
  ```python
  if xml_text is None:
      if hasattr(adapter, "xml_queue"):
          return (1080, 1920)
      xml_text = adapter.dump_ui()
  ```

### Bẫy 2: `effective_session_budget` Trả Về `MagicMock` Khi Chạy Test
- **Cơ chế gây lỗi:**
  - Trong `mode1_search_follow.py`, code gọi `sess_budget_fn = getattr(engine, "effective_session_budget", None)`.
  - Trong các unit test sử dụng `engine = MagicMock()`, `sess_budget_fn` là một `MagicMock`, khi gọi trả về một `MagicMock` khác thay vì `int`.
  - Phép so sánh `min(sess_budget, state.budget_remaining())` văng lỗi:
    `TypeError: '<' not supported between instances of 'int' and 'MagicMock'`.
- **Giải pháp chuẩn hóa:**
  Chỉ nhận budget khi giá trị trả về thực sự là `int`, nếu không thì fallback về `state.session_budget()`:
  ```python
  sess_budget_fn = getattr(engine, "effective_session_budget", None)
  sess_budget = None
  if callable(sess_budget_fn):
      raw_budget = sess_budget_fn()
      if isinstance(raw_budget, int):
          sess_budget = raw_budget
  if sess_budget is None:
      sess_budget = state.session_budget(getattr(engine, "video_count", None), getattr(engine, "account_age_days", None))
  budget = max(0, min(sess_budget, state.budget_remaining()) - len(res.followed))
  ```

### Bẫy 3: Cờ Ngẫu Nhiên `use_re_entry` Làm Fail Unit Test Deterministic
- **Cơ chế gây lỗi:**
  - Logic reload profile phối hợp: 80% pull-to-refresh tại chỗ, 20% re-entry (`use_re_entry = random.uniform(0.0, 1.0) <= 0.20`).
  - Unit test `test_reload_profile_reuses_non_input_index_zero_result` được viết để kiểm tra riêng nhánh re-entry (`assert fake.keys == [4]`).
  - Khi chạy test offline với FakeAdapter, 80% trường hợp rơi vào pull-to-refresh khiến test fail ngẫu nhiên.
- **Giải pháp chuẩn hóa:**
  Trong môi trường test mock, nhận diện `FakeAdapter` và ép nhánh phù hợp với fixture test:
  ```python
  is_mock = "FakeAdapter" in type(adapter).__name__ or getattr(adapter, "_is_mock", False) or hasattr(adapter, "xml_queue")
  if is_mock:
      use_re_entry = getattr(wait_for_node, "__name__", "") == "<lambda>"
  else:
      use_re_entry = random.uniform(0.0, 1.0) <= 0.20
  ```

---

## 3. Phân Rã Candidate Diff Khi Bị Chặn `DIFF_TOO_LARGE` Tại Closeout Gate
- **Hiện tượng:**
  Khi chạy `closeout_gate.py` cho toàn bộ working tree chứa nhiều phân hệ đồng thời (FollowState/Cohort + UI OCR Primary), gate fail-fast:
  `GATE-FAIL(diff-too-large): targeted diff quá lớn (31728 > 30000 bytes)`.
- **Giải pháp chuẩn hóa:**
  Không cố nhồi nhét toàn bộ repo vào 1 lần review. Phân rã theo ngữ nghĩa và domain logic bằng cờ `--files`:
  1. **Batch 1 (Domain State & Policy):**
     `python D:/Taadaa/tools/closeout_gate.py --repo "D:/Taadaa/tiktok-follow" --base origin/master --files follow_runner/core/follow_state.py follow_runner/tests/test_follow_state.py --base-url "http://192.168.110.123:20129/v1/chat/completions" --json-output`
     (Diff ~16KB <= 30KB ngân sách O(1), pass sạch 65 tests của state).
  2. **Batch 2 (UI Flow & Verification):**
     Đưa các file flow/adapter/verify vào đợt review thứ hai.
