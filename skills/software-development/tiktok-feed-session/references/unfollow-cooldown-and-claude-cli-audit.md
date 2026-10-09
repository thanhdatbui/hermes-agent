# Cơ chế Chống Nhả Follow & Kinh nghiệm Điều phối Claude CLI Audit Monolith

## 1. Cơ chế Chống Nhả Follow (Unfollow Cooldown Enforcement) trong `tiktok-luot nuoi acc`

### Nguồn nhận diện tài khoản bị phạt
- **Hàm:** `is_account_in_follow_cooldown(ctx)` trong `python_runner/flows/feed_swipe_smoke.py:13669`.
- **Đọc file:** `follow_state_{machine}_row_{row}.json` (hoặc fallback `follow_state_{machine}.json`) tại `D:/Taadaa/tiktok-follow/runs/state/`.
- **4 tiêu chí kích hoạt cooldown:**
  1. `cooldown_until_at`: `now_utc < until_dt` (so sánh UTC ISO timestamp).
  2. `cooldown_until_date`: `today_str <= cooldown_until_date` (so sánh ngày YYYY-MM-DD).
  3. `follow_failed_date == today_str`: Bị dính lỗi nhả follow ngay trong ngày hiện tại.
  4. `follow_failed is True`: Cờ đánh dấu dính án phạt khi chưa xác định thời hạn cụ thể.

### Xử lý trong các luồng tương tác
1. **Lướt Feed (Organic Feed Follow):**
   - `_maybe_follow_video()` (`feed_swipe_smoke.py:13717`): Kiểm tra `is_account_in_follow_cooldown(ctx)` ngay đầu hàm.
   - Nếu True: Log `account is in follow cooldown (imprisoned)` và `return False` ngay lập tức, ép tỷ lệ follow về 0% tuyệt đối bất kể `follow_rate` cài đặt là bao nhiêu.
2. **Popup Gợi ý Bạn bè (Follow Friends Popup):**
   - `dismiss_follow_friends_suggestion_popup()` (`benign_popup.py:4920`): Thiết lập `follow_limit = 0 if in_cooldown else 2`.
   - Khi dính án phạt: `range(0)` không chạy bất kỳ lượt tap follow nào, chuyển sang tìm nút `X` hoặc gửi phím `Back` để quay về Feed an toàn.
3. **Thẻ Đề xuất Follow lại trên Feed (`follow_back_suggestion`):**
   - Định nghĩa trong `GemPhoneFarmBlindPopupRule` (`feed_swipe_smoke.py:962`).
   - Xử lý vô điều kiện (unconditional): Bắt gặp nhãn "Follow lại" / "Follow back" là tap "Không quan tâm", bảo vệ cả tài khoản phạt lẫn tài khoản sạch.

---

## 2. Kinh nghiệm điều phối Claude CLI trên Codebase / Monolith lớn

1. **Tránh để Claude CLI tự đọc file monolith >20k dòng (`feed_swipe_smoke.py`):**
   - Claude Code khi quét và đọc toàn bộ file 22.000 dòng trong print mode (`-p`) rất dễ bị cạn lượt quay vòng (`--max-turns`) hoặc timeout (>300s).
2. **Kỹ thuật Pipe Context O(1):**
   - Coordinator dùng lệnh Python / grep trích xuất đúng các đoạn logic trọng yếu cần phân tích (vài chục đến vài trăm dòng).
   - Pipe qua `stdin` vào `claude -p "..."`: Claude xử lý và trả kết quả phân tích trong vòng <15s mà không cần đụng đĩa hay tốn lượt đọc file.
3. **Lưu ý đường dẫn Windows trong script Python:**
   - Khi chạy script Python trích xuất file trên Windows, dùng native drive format (`D:/...`), không dùng MSYS path (`/d/...`) vì `pathlib.Path` trên Python Windows sẽ biến `/d/...` thành `\\d\\...` gây `FileNotFoundError`.
