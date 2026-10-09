# GPM Watchdog Silent Batching and Single Closeout Report Protocol

## 1. Bối cảnh & Hiện tượng (Sự cố Spam Farm Alert)
Khi triển khai watchdog tự động đăng nhập Gmail lên GPMLogin sau ca tối (`post_evening_gpm_login_watchdog.py`), cronjob được cấu hình:
- Chạy định kỳ mỗi 10 phút (`*/10 21,22,23 * * *`).
- Đích gửi tin: Kênh Farm Alert (`telegram:-5373649734`).
- Chế độ: `no_agent=True` (nội dung stdout của script sẽ được scheduler tự động gửi trực tiếp làm tin nhắn Telegram).

### Lỗi Thiết Kế Gốc (Anti-Pattern):
1. **Spam sau mỗi batch lẻ:** Script chia việc thành từng batch tối đa 10 workers song song. Tuy nhiên, sau mỗi batch lẻ, script lại gọi `print(f"[LOGIN GPM ĐÊM] ✓ {success_n} | ✗ {fail_n}...")`.
2. Do cronjob chạy mỗi 10 phút, bất cứ khi nào xử lý xong 1 batch lẻ (thậm chí batch rỗng/thất bại do profile chưa sẵn sàng), scheduler lại tự động gửi một tin nhắn mới vào Telegram, gây spam liên tục làm phiền người vận hành.
3. Khi quét các tài khoản chưa được import/tạo profile trên GPM DB (`PROFILE_NOT_FOUND`), batch trả về toàn bộ lỗi `✗ 7`, gây hoang mang cho user.

---

## 2. Chuẩn Thiết Kế Silent Batching Cho Watchdog
Đối với mọi cron watchdog chạy cuốn chiếu nhiều đợt trong ca có cấu hình `no_agent=True` và đích gửi là kênh chat:

1. **Khóa Im Lặng Tuyệt Đối (Silent Execution):**
   - Trong quá trình xử lý các batch lẻ hoặc các tick cron trung gian, **CẤM TUYỆT ĐỐI in ra stdout**.
   - Mọi log chi tiết chỉ được ghi ra `sys.stderr` để phục vụ debug cục bộ.
   - Stdout rỗng (`""`) sẽ được Hermes Cron Scheduler coi là trạng thái im lặng (không có gì để báo) và KHÔNG gửi tin nhắn Telegram.

2. **Cơ chế Tích Lũy Trạng Thái (Accumulative Counters):**
   - Lưu trữ số lượng thành công/thất bại tích lũy (`total_success`, `total_fail`) vào file state JSON theo ngày (`date`).
   - Cập nhật cờ `reported: bool` để đảm bảo chỉ gửi báo cáo đúng 1 lần trong ngày.

3. **Điều Kiện Báo Cáo Tổng Kết Duy Nhất (Single Final Report):**
   Chỉ in ra stdout đúng một thông báo tổng kết khi và chỉ khi thỏa mãn một trong hai điều kiện:
   - **Hoàn tất 100% tài khoản cần xử lý trong ca** (`candidates` hết hoặc toàn bộ candidate đã qua danh sách `processed`).
   - **Hết khung giờ ca tối** (sau 23:30 HCM).
   - Kiểm tra `not reported` và có phát sinh công việc (`total_success > 0 or total_fail > 0`) trước khi print.

---

## 3. Mẫu Cấu Trúc Code Chuẩn (Pattern Implementation)

```python
# Đọc trạng thái trong ngày
is_same_day = (state.get("date") == today_str)
processed = state.get("processed", []) if is_same_day else []
total_success = state.get("total_success", 0) if is_same_day else 0
total_fail = state.get("total_fail", 0) if is_same_day else 0
reported = state.get("reported", False) if is_same_day else False

candidates, proxy_count = get_candidates(today_str, processed)

# Nếu không còn candidate nào cần xử lý
if not candidates:
    if not reported and (total_success > 0 or total_fail > 0):
        print(f"[LOGIN GPM ĐÊM - TỔNG KẾT] ✓ {total_success} | ✗ {total_fail} | proxy_limit 2/port/ngày | Hoàn tất ca tối")
        reported = True
    state.update({
        "date": today_str,
        "processed": processed,
        "proxy_count": dict(proxy_count),
        "total_success": total_success,
        "total_fail": total_fail,
        "reported": reported,
        "finished": True,
    })
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0

# Thực thi batch máy rảnh...
# (Chạy ngầm, ghi log ra stderr)
total_success += success_n
total_fail += fail_n

now_hcm = datetime.now(HCMC)
is_late = (now_hcm.hour == 23 and now_hcm.minute >= 30)
all_done = (len(processed) >= len(candidates) + len(batch)) or is_late

# IM LẶNG trong lúc chạy batch lẻ; CHỈ BÁO CÁO 1 LẦN DUY NHẤT khi xong toàn ca hoặc hết giờ
if all_done and not reported:
    if total_success > 0 or total_fail > 0:
        print(f"[LOGIN GPM ĐÊM - TỔNG KẾT] ✓ {total_success} | ✗ {total_fail} | proxy_limit 2/port/ngày | Hoàn tất ca tối")
    reported = True

state.update({
    "date": today_str,
    "processed": processed,
    "proxy_count": dict(proxy_count),
    "total_success": total_success,
    "total_fail": total_fail,
    "reported": reported,
    "finished": all_done,
})
STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
return 0
```
