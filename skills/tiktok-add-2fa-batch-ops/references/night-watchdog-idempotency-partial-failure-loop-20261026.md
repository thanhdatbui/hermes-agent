# Lỗi Vòng Lặp Rerun & Bão Spam Của Night Watchdog Khi Có Partial Failure (26/10/2026)

## 1. Hiện Tượng Thực Tế
- Nhóm Telegram `Tiktok add 2fa` (`-5468653590`) bị spam liên tục các bản tin báo cáo 2FA toàn farm lúc nửa đêm (ví dụ: 00:38, 02:34, 03:23).
- Toàn bộ batch 2FA bị kích hoạt chạy lại nhiều lần xuyên đêm, gây nghẽn thiết bị, tiêu tốn tài nguyên và tăng nguy cơ va chạm với khung dọn cache (04:00) hoặc ca nuôi sáng (05:05).

## 2. Nguyên Nhân Gốc Rễ (Root Cause)
1. **Thiết kế cronjob tần suất cao:** `night-tiktok-2fa-watchdog` chạy mỗi 15 phút (`*/15 * * * *`) để chớp lấy khung giờ rảnh ban đêm.
2. **Kẹp điều kiện hoàn tất với 100% thành công:**
   ```python
   def already_ran_today(today_str: str) -> bool:
       state = load_state()
       is_success = state.get("last_2fa_success") is True or state.get("last_success_date") == today_str
       return bool((state.get("last_2fa_date") == today_str or state.get("last_success_date") == today_str) and is_success)
   ```
   - Trong môi trường phone farm vật lý (~160 máy), luôn có tỷ lệ máy bị lỗi cục bộ (hết acc, rớt kết nối, SIM, app lỗi).
   - Khi có bất kỳ máy nào lỗi (`failed > 0`), runner trả về `status = "partial_failure"`.
   - Script ghi nhận `last_2fa_success = False` và `last_success_date = None`.
3. **Mất tính Idempotency:**
   - Vì `last_2fa_success` là `False`, hàm `already_ran_today()` trả về `False` (coi như ca đêm chưa chạy).
   - Ngay khi batch trước nhả lane lock, tick 15 phút tiếp theo của cronjob tưởng ca đêm chưa được thực hiện, nên lại khởi chạy toàn bộ batch Kibe & Admin từ đầu.
   - Vòng lặp: Chạy 1-2 tiếng -> Báo cáo Telegram -> `status = partial_failure` -> Cron kích hoạt lại -> Bão spam và quá tải farm.

## 3. Quy Tắc & Giải Pháp Bắt Buộc Cho Night Watchdog
1. **Tách biệt `execution completion` và `100% success`:**
   - Watchdog ban đêm là dạng **Batch One-Shot theo ngày**: Một khi đã quét hết toàn bộ máy trong ca đêm (dù kết quả là `success` hay `partial_failure`), ca đêm coi như **ĐÃ CHẠY XONG**.
   - Kiểm tra idempotency `already_ran_today`:
     ```python
     def already_ran_today(today_str: str) -> bool:
         state = load_state()
         # Đã chạy trong ngày hôm nay thì dừng, bất kể partial_failure
         return state.get("last_2fa_date") == today_str
     ```
   - Tương tự với Gmail:
     ```python
     def already_ran_gmail_tonight(today_str: str) -> bool:
         state = load_state()
         return state.get("last_gmail_date") == today_str
     ```
2. **Cơ chế chạy lại (Rerun Discipline):**
   - TUYỆT ĐỐI CẤM tự động rerun tự phát trong cùng 1 đêm khi gặp `partial_failure`.
   - Rerun chỉ được phép kích hoạt khi có cờ tường minh `--force` từ người vận hành hoặc từ workflow sửa lỗi có chủ đích.
3. **Giám sát spam:**
   - Mỗi phase trong Night Chain chỉ được gửi tối đa 1 bản tin tổng kết mỗi đêm về nhóm Telegram nghiệp vụ trừ khi có cờ `--force`.
