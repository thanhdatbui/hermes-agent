# Follow Hook Concurrency Throttling & Soft Deadline Budgeting

## 1. ADB Bus Saturation & Concurrency Bottleneck
- **Triệu chứng:** Hàng loạt máy bị `follow-timeout` (1200s) đồng thời khi kết thúc lượt lướt feed và chuyển sang follow hook.
- **Root Cause:**
  - Lướt feed chỉ gửi 1 lệnh `input swipe` mỗi 5-10s (rất nhẹ với ADB).
  - Follow hook thực hiện chuỗi phức tạp: Search UID -> kiểm tra kết quả -> mở profile -> verify identity -> tap follow -> reload profile verify nhả follow -> Back/Home về Feed. Mỗi UID tốn 10–15 lần UI XML dump toàn phần.
  - Khi 40 worker thread trong `multi_machine_feed_session.py` cùng gọi subprocess `run_follow.py` đồng thời, ADB server (`localhost:5037`) bị nghẽn (UI XML dump từ 0.5s tăng lên 15–30s/lần), đẩy thời gian 15–20 follow lên > 25 phút, vượt quá timeout 1200s.
- **Giải pháp:**
  - Áp dụng van `_FOLLOW_CONCURRENCY = threading.BoundedSemaphore(DEFAULT_FOLLOW_MAX_CONCURRENCY)` (cap = 20 máy) kết hợp cross-process OS file slot locks (`slot-0.lock` .. `slot-19.lock`) dưới `~/.codex/follow-concurrency-locks/` trong `multi_machine_feed_session.py`, tương tự như `_UPLOAD_CONCURRENCY`.
  - Các máy xếp hàng luân phiên, mỗi máy chạy xong trong 3–5 phút thay vì 25 phút.

## 2. Soft Deadline Budgeting trong Follow Runner
- **Triệu chứng:** `run_follow.py` trong `tiktok-follow` lặp qua danh sách UID/anchor mà không kiểm tra thời gian trôi qua, dẫn đến bị tiến trình cha cưỡng bức kill (`subprocess.TimeoutExpired`) tạo alert đỏ `GIỮ HIỆN TRƯỜNG`.
- **Root Cause:** Thiếu soft deadline check giữa các vòng lặp follow.
- **Giải pháp:**
  - `FollowEngine.has_time_for_next_action(reserve_seconds=60.0)` kiểm tra `(feed_timeout_seconds - elapsed) > reserve_seconds`.
  - Ở đầu mỗi vòng lặp trong `mode1_search_follow.py` và `mode2_follow_followers.py`, nếu thời gian còn lại < 60s thì dừng êm (`break`), ghi nhận các nick đã follow thành công, trả về status `"OK"` và đóng app về Home sạch sẽ.

## 3. Keyboard Occlusion & Redundant Dumps in Search Navigation
- Trong `_nav_search`:
  - Tránh gọi `dump_ui()` trùng lặp khi kiểm tra `EditText` trước khi gửi fallback `KEYCODE_ENTER` (tái sử dụng `initial_xml` đã dump).
  - Loại bỏ các node gợi ý tìm kiếm (`tvl_unified_sug`, `tvl_sug`, `tvl_his`) khỏi kết quả search card để tránh nhận nhầm autocomplete suggestion làm profile card.
  - Trong `_back_to_feed`, xử lý nút Back mở rộng (`_SEARCH_BACK_SUFFIXES`) và hỗ trợ thoát dứt điểm khi bàn phím ảo mở trên màn Search History.
