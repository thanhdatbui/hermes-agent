# RCA & Spec: Coordinator Guard Token Bleeding & 1-Strike Circuit Breaker (20/10/2026)

## 1. Bản chất sự cố 9 lần bị Guard chặn liên tiếp
- **Bối cảnh:** Khi User yêu cầu chỉnh sửa logic né giờ reboot cho `cron_night_tiktok_2fa_watchdog.py`, Coordinator cố tình dùng `delegate_task` thay vì `dispatch_worker.py`.
- **Hậu quả 9 lần bị chặn:**
  1. `MISSING_TASK_KIND`
  2. `EDIT_MISSING_FILE`
  3. `MULTI_FILE_VIOLATION`
  4. `EDIT_MISSING_OLD_STRING`
  5. `OLD_EQUALS_NEW`
  6. `OUT OF REPO WHITELIST`
  7. `OLD_EQUALS_NEW`
  8. `ANCHOR_NOT_FOUND`
  9. `GUARD SOURCE BLACKLISTED`
- **Tác động tiêu hao tài nguyên (Token Bleeding):**
  - Mặc dù Pre-Tool Hook (`guard_dispatch_contract.py`) chặn ở tầng Python cục bộ (<50ms) nên bảo toàn 0% quota của Claude CLI (không spawn subprocess).
  - **NHƯNG** với mỗi lần bị chặn, tool error response lại được nạp ngược vào conversation context của Coordinator.
  - Với context size ~60k-80k tokens, việc lặp lại 9 turns khiến Coordinator nuốt lại toàn bộ context 9 lần, tiêu hao **~500.000 đến 700.000 input tokens** trên pool Coordinator (:20129 / Gemini), đồng thời làm phình to session và ngâm treo Telegram 70 phút!

---

## 2. Quy tắc Chốt chặn Cơ học (1-Strike Circuit Breaker for Guard Denials)
1. **Quy tắc 1-Strike Fail-Closed:**
   - Khi một lệnh gọi công cụ (`delegate_task`, `terminal`, `write_file`) bị bất kỳ Pre-Tool Hook / Guard nào chặn với thông báo lỗi (`⛔ [COORDINATOR GUARD ...]`), Coordinator **CẤM TUYỆT ĐỐI** thử lại mù quáng bằng cách đoán mò lại tham số, đổi format hay rút ngắn chuỗi anchor.
   - Số lần thử lại tối đa cho lỗi vi phạm hợp đồng Guard là **1 LẦN DUY NHẤT** (Strike 1).
   - Nếu lần 2 vẫn dính Guard chặn $\rightarrow$ Kích hoạt ngay Circuit Breaker:
     - Dừng ngay việc gọi tool đó.
     - Chuyển thẳng sang kênh chuẩn hóa duy nhất: Single Dispatch Gateway (`python D:/Taadaa/tools/dispatch_worker.py`).
2. **Quy tắc Tước quyền `delegate_task` khi sửa Code:**
   - CẤM mọi nỗ lực định dạng prompt cho `delegate_task` khi mục tiêu là sửa code hoặc test.
   - Mọi task code/test BẮT BIẾN đi qua `dispatch_worker.py` (Haiku 5.5 CLI $\rightarrow$ Agy CLI).
3. **Bảo tồn Quota Coordinator:**
   - Không được biến phiên trò chuyện thành môi trường thử nghiệm (trial-and-error) các regex hay syntax của Guard.
   - Thất bại 1 lần ở Guard là bằng chứng kiến trúc đang đi sai đường; phải chuyển đổi phương thức thi công ngay lập tức.
