# TikTok Profile Switch Reload Polling Pattern

## 1. Hiện tượng & Triệu chứng (Sự cố Máy 8 & Farm Proxy)
- **Triệu chứng:** Alert `profile username still mismatched after switch` khi chuyển từ tài khoản cũ sang tài khoản mới trong switcher.
- **Hiện trường:** Sau khi phiên dừng vài giây, kiểm tra thiết bị thì thấy TikTok đã chuyển sang tài khoản mới thành công (`dumpsys window` và XML profile đã là nick mới).
- **Hậu quả:** Phiên chạy bị dừng oan và kích hoạt cờ giữ lock thiết bị (`blocked`), làm gián đoạn chu kỳ nuôi nick của farm.

## 2. Nguyên nhân gốc rễ (Root Cause)
1. **Độ trễ mạng qua Farm Proxy:**
   - Khi chạy qua proxy farm (`192.168.110.2:2000X`), TikTok mất khoảng 6–10 giây để hoàn tất request đổi session token và re-render giao diện Profile của tài khoản mới.
2. **Anti-pattern: Đọc XML 1 lần duy nhất quá sớm:**
   - Script chỉ sleep 4.5–6.0s sau khi tap account row trong switcher, rồi chụp UI XML xác minh đúng 1 lần duy nhất.
   - Tại mốc ~5s, TikTok vẫn đang hiển thị profile cũ (chưa nhận xong dữ liệu mạng).
   - Script thấy username chưa khớp nên coi attempt 1 thất bại và lập tức tap mở lại Switcher ở attempt 2.
3. **Tác động cắt ngang (Interrupt Collision):**
   - Hành động mở lại account switcher modal cắt ngang quá trình network reload đang dở của TikTok, khiến attempt 2 cũng không reload được và văng lỗi `profile username still mismatched after switch`.

## 3. Giải pháp chuẩn: Polling Chờ Reload Sau Switch
Trong `verify_and_switch_profile` (`python_runner/flows/feed_swipe_smoke.py`):
1. **Vòng lặp Polling (tối đa 3 lần, delay 2.0s giữa các lần):**
   - Sau lần navigate profile ban đầu, không vội kết luận thất bại ngay lần đọc đầu tiên.
   - Sử dụng vòng lặp `for poll_idx in range(1, max_verify_polls + 1):` (với `max_verify_polls = 3`):
     - Nếu `poll_idx > 1`: `time.sleep(2.0)`.
     - Re-read profile identity qua `_read_profile_identity_with_add_phone_guard`.
     - Kiểm tra `verify_selected_account` hoặc `username_matches`.
     - Nếu khớp (`verified = True`): Ghi log `verify_profile_after_switch_polled` và `break` ngay lập tức.
     - Nếu chưa khớp và còn lượt poll: Ghi log `verify_profile_after_switch_waiting_reload` và tiếp tục poll.
2. **Ngăn chặn mở lại Switcher sớm:**
   - Chỉ khi đã hết toàn bộ số lần polling (tổng thời gian chờ lên đến ~10–12s) mà username vẫn không khớp mới coi attempt đó thất bại và thử tìm lại switch anchor.
