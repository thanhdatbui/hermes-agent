# Silent Watchdog Pattern & Spam-Free Telegram Delivery

## Bối cảnh & Triệu chứng
User thắc mắc/khó chịu vì nhận thông báo liên tục:
> "Gì thế báo liên tục v" (từ job `post-evening-gpm-login-watchdog` hoặc các job watchdog đêm).

## Nguyên nhân gốc (Root Cause)
1. **Cơ chế Hermes Cron Delivery:**
   - Khi cronjob cấu hình `no_agent=True` và `deliver='telegram:...'` (hoặc `deliver='origin'`): BẤT KỲ ký tự nào in ra `stdout` (non-empty) đều được scheduler xem là tin nhắn và gửi ngay đến Telegram.
   - Khi stdout rỗng (`""`): Scheduler sẽ **SILENT** — hoàn toàn không gửi gì.
2. **Lỗi thiết kế in log theo batch:**
   - Script chạy định kỳ (vd: mỗi 5-10 phút) trong khung giờ (vd: 21:30 - 23:45).
   - Trong mỗi tick, script xử lý 1 batch nhỏ (vd: 10 accounts/workers) và cuối hàm `main()` lại in:
     `print(f"[LOGIN GPM ĐÊM] ✓ {success_n} | ✗ {fail_n}...")`
   - Hậu quả: Cứ mỗi 10 phút, dù chỉ hoàn thành 1 batch lẻ hoặc fail 1 batch con, cronjob lại in stdout khiến Telegram bắn thông báo liên tục cả đêm làm phiền user.

## Nguyên tắc Vàng: Watchdog Phải Im Lặng (Silent Watchdog)
1. **Im lặng tuyệt đối trong suốt tiến trình (Intermediate silence):**
   - Mọi log trung gian, log per-machine, log retry BẮT BUỘC chỉ ghi vào `sys.stderr` hoặc file log đĩa (`D:\Taadaa\runtime\...\*.log`).
   - KHÔNG ĐƯỢC in bất kỳ thứ gì ra `stdout` (dùng `print()`) sau mỗi batch lẻ.
2. **Chỉ báo cáo 1 LẦN DUY NHẤT khi hoàn tất toàn bộ ca hoặc hết giờ:**
   - Điều kiện báo: `all_done == True` (đã quét hết toàn bộ candidates / workbook) HOẶC chạm mốc chốt ca (vd: sau 23:30).
   - Lưu trạng thái đã báo cáo (`reported: True`) vào file state JSON (`cron-state/*.json`).
   - Khi đã `reported: True`, các tick sau trong cùng ngày KHÔNG ĐƯỢC báo lại nữa.
3. **Mẫu chuẩn (Canonical Pattern) cho Watchdog cuốn chiếu:**

```python
# Chỉ in ra stdout đúng 1 lần khi toàn bộ ca kết thúc hoặc chốt giờ
if all_done and not state.get("reported_final"):
    total_ok = len(state.get("success_list", []))
    total_fail = len(state.get("fail_list", []))
    print(f"[TỔNG KẾT CA TỐI] Hoàn tất nạp GPM: ✓ {total_ok} | ✗ {total_fail}")
    state["reported_final"] = True
    save_state(state)
# Nếu chưa xong toàn ca: STDOUT PHẢI HOÀN TOÀN RỖNG để Hermes cron không gửi tin nhắn Telegram.
```
