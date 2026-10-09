# Case UI-92: Module 2 Multi-Anchor Exhaustion Before Mode 1 Degradation & Internal Pending Priority

- **Thời gian xử lý:** 04/10/2026
- **Vị trí áp dụng:** `follow_runner/flows/mode2_follow_followers.py` (`run_mode2`, `missing_button_rows`).
- **Sự cố thực tế:** Ca 1 Row 2 ngày 04/10/2026, Module 2 chỉ đạt 2 follow trong khi Module 1 phải gánh 25 follow bù do 3 máy sống sót (M17, M18, M33) đều dừng ngay sau Anchor 1 với lỗi `MANUAL_REVIEW: follower row không có nút follow semantic`.

---

## 1. Nguyên nhân cốt lõi (Root Cause)
1. **Ngắt sớm toàn bộ session sau 1 Anchor:**
   - Trong `mode2_follow_followers.py`, danh sách anchor được cấu hình lấy tối đa 3 kênh (`uids = uids[:3]`).
   - Khi Anchor 1 gặp lỗi UI (như `missing_button_rows` hoặc lỗi mở tab), cờ `failed = True` kích hoạt lệnh `break` ở vòng lặp ngoài `for uid in uids:`.
   - Hậu quả: Runner ngắt ngay lập tức mà chưa từng thử Anchor 2 và Anchor 3, đẩy toàn bộ quota sang Module 1 chạy bù.
2. **False Positive Missing Button Rows khi vẫn còn hàng hợp lệ:**
   - Khi phát hiện một hàng nội bộ thiếu nút follow (`missing_button_rows`), code cũ ngắt ngay lập tức dù trên màn hình vẫn còn các hàng nội bộ khác có nút follow hợp lệ (`internal_pending`).

---

## 2. Quy chuẩn kỹ thuật bắt buộc (Invariants)
1. **Duyệt đủ ít nhất 3 Anchor trước khi cho phép qua Module 1:**
   - Module 2 BẮT BUỘC phải duyệt lần lượt qua tất cả các Anchor trong danh sách (`uids[:3]`).
   - Khi một Anchor gặp lỗi UI/layout cục bộ (missing buttons, lỗi mở tab):
     * Ghi nhận `anchor_fail_reason`.
     * Điều hướng an toàn về Feed (`_back_to_feed(engine)`).
     * Tiếp tục chuyển sang Anchor tiếp theo trong danh sách.
   - CHỈ KHI **tất cả các Anchor đều thất bại/cạn kiệt** mà chưa follow được nick nào (`used == 0`):
     * Mới gán `res.status = "MANUAL_REVIEW"` để `follow_engine.py` kích hoạt `mode2_degraded` chuyển Module 1 chạy bù.
   - Nếu bất kỳ Anchor nào kéo được follow (`used > 0`): Phiên được tính là thành công (`res.status = "OK"`, `res.failed = False`). Phần budget còn lại nếu có sẽ do Module 1 bù tiếp.
2. **Ưu tiên follow các hàng có nút hợp lệ (`internal_pending`):**
   - Khi phát hiện `missing_button_rows`, nếu màn hình vẫn còn các hàng `internal_pending` có nút hợp lệ:
     * Ghi log cảnh báo và tiếp tục follow các hàng hợp lệ đó.
     * Chỉ khi không còn hàng nào bấm được (`not internal_pending`), mới lùi về Feed và chuyển sang Anchor tiếp theo.
3. **Fail-Closed khi TikTok nhả/chặn follow:**
   - Nếu phát hiện lỗi cấp độ tài khoản (`state.follow_failed` hoặc `res.follow_failed` do TikTok nhả follow / chặn action):
     * DỪNG NGAY LẬP TỨC toàn bộ session để bảo vệ nick, không thử tiếp các Anchor khác hay Module 1.

---

## 3. Verification & Regression Suite
- Unit test: `test_run_mode2_tries_next_anchor_when_first_anchor_fails` chứng minh khi Anchor 1 fail mở tab, runner tự động chuyển sang Anchor 2 và follow thành công (`out.status == "OK"`, `opened == ["anchor1", "anchor2"]`).
- Toàn bộ suite `follow_runner/tests/test_mode2_follow_followers.py` (206 tests) PASS 100%.
