# Multi-Shift Silent Watchdog: Dynamic Shift Naming & Independent State Management

## 1. Bối Cảnh & Vấn Đề
Một script watchdog ban đầu được thiết kế chỉ cho một ca cụ thể (ví dụ ca tối: `post_evening_gpm_login_watchdog.py`).
Sau đó, để tận dụng tối đa thời gian máy rảnh giữa các ca nuôi feed trong ngày, khung giờ chạy được mở rộng sang nhiều ca (Sáng: 07:15-08:45, Trưa: 12:00-13:45, Tối: 20:15-23:45).

### 2 Lỗi Thiết Kế Điển Hình:
1. **Hardcode tên ca trong báo cáo tổng kết**:
   - Tiêu đề báo cáo bị gán cứng `[LOGIN GPM ĐÊM - TỔNG KẾT]` và `Hoàn tất ca tối`.
   - Khi chạy và chốt kết quả ở ca trưa (13:40), script bắn tin nhắn `[LOGIN GPM ĐÊM - TỔNG KẾT] ... Hoàn tất ca tối` lên Telegram, gây hiểu lầm nghiêm trọng cho user (*"Gì mà h ca tối"*).
2. **Cờ `finished: True` cấp ngày chặn các ca tiếp theo**:
   - File state chỉ lưu cờ boolean đơn giản `{"date": "2026-09-20", "finished": true}`.
   - Khi ca trưa chốt `finished: True`, toàn bộ các tick của ca tối cùng ngày đều kiểm tra `if state.get("date") == today_str and state.get("finished"): return 0`, khiến ca tối bị chặn đứng hoàn toàn (deadlock).

---

## 2. Giải Pháp Chuẩn: Multi-Shift State & Dynamic Naming

### Bước 1: Nhận diện ca chạy động (Dynamic Shift Resolution)
```python
def get_current_shift_info() -> tuple[str, str, str]:
    """
    Trả về (shift_code, shift_label, shift_desc) dựa trên giờ hiện tại.
    Ví dụ:
      - Sáng: 07:15 - 08:45 -> ("SANG", "SÁNG", "sáng")
      - Trưa: 12:00 - 13:45 -> ("TRUA", "TRƯA", "trưa")
      - Tối:  20:15 - 23:45 -> ("TOI", "TỐI", "tối")
    """
    now = datetime.now(HCMC)
    current = now.hour * 60 + now.minute
    if 7 * 60 + 15 <= current <= 8 * 60 + 45:
        return ("SANG", "SÁNG", "sáng")
    elif 12 * 60 <= current <= 13 * 60 + 45:
        return ("TRUA", "TRƯA", "trưa")
    elif 20 * 60 + 15 <= current <= 23 * 60 + 45:
        return ("TOI", "TỐI", "tối")
    
    # Fallback theo giờ nếu chạy ngoài các mốc chặt
    if now.hour < 12:
        return ("SANG", "SÁNG", "sáng")
    elif now.hour < 18:
        return ("TRUA", "TRƯA", "trưa")
    else:
        return ("TOI", "TỐI", "tối")
```

### Bước 2: Format báo cáo tổng kết động theo ca
```python
def _format_summary_report(total_success: int, total_fail: int, shift_label: str = "TỐI", shift_desc: str = "tối") -> str:
    live_anti_count = len(_get_live_omniroute_antigravity_emails())
    session_count = len(_get_gpm_profiles_with_google_session())
    return (
        f"[LOGIN GPM {shift_label} - TỔNG KẾT]\n"
        f"• Kết quả ca: ✓ {total_success} | ✗ {total_fail} | proxy_limit 2/port/ngày | Hoàn tất ca {shift_desc}\n"
        f"• Antigravity Pool: {live_anti_count} accounts LIVE trên OmniRoute (:20129)\n"
        f"• Profile sẵn Google Session chờ OAuth: {session_count} accounts"
    )
```

### Bước 3: Quản lý State phân tách theo từng ca (`finished_shifts` & `reported_shifts`)
Thay vì dùng một cờ `finished` duy nhất cho cả ngày, quản lý mảng ca đã hoàn thành:
```python
shift_code, shift_label, shift_desc = get_current_shift_info()

# Kiểm tra xem ca hiện tại đã hoàn tất chưa
finished_shifts = state.get("finished_shifts", []) if is_same_day else []
reported_shifts = state.get("reported_shifts", []) if is_same_day else []

if shift_code in finished_shifts:
    return 0  # Ca này trong ngày đã xong, im lặng chờ ca tiếp theo

# Khi ca kết thúc (hết candidates hoặc chạm mốc cuối ca):
if all_done:
    if shift_code not in reported_shifts:
        if shift_success > 0 or shift_fail > 0:
            print(_format_summary_report(shift_success, shift_fail, shift_label, shift_desc))
        reported_shifts.append(shift_code)
    if shift_code not in finished_shifts:
        finished_shifts.append(shift_code)

state.update({
    "date": today_str,
    "finished_shifts": finished_shifts,
    "reported_shifts": reported_shifts,
    # Chỉ đánh dấu finished toàn ngày nếu đã hoàn thành ca cuối cùng (TOI)
    "finished": ("TOI" in finished_shifts),
})
```

---

## 3. Checklist Khi Mở Rộng Khung Giờ Một Cron Đơn Ca Thành Đa Ca
1. [ ] **Cron schedule**: Giờ chạy trong `schedule` cron đã bao gồm tất cả các ca (ví dụ: `*/5 7,8,12,13,20,21,22,23 * * *`).
2. [ ] **Time window filter**: Hàm lọc giờ trong script khớp đúng các khoảng rảnh giữa các ca.
3. [ ] **Dynamic naming**: Tiêu đề báo cáo, cutoff time (ví dụ sau 11:15 vs sau 23:45), và mọi khối session telemetry mới (như `session_failed_by_reason`, `session_uploaded_machines`, cụm lỗi) thay đổi tương ứng theo ca (Sáng / Trưa / Chiều / Tối), tuyệt đối không hardcode chuỗi tĩnh kiểu "ca tối nay" trong các khối phụ.
4. [ ] **State isolation**: State theo dõi ca hoàn thành bằng list (`finished_shifts`) thay vì boolean `finished: True` chặn toàn ngày.
5. [ ] **Silent on no-op**: Đầu ra `stdout` vẫn giữ nguyên tắc 0 bytes nếu ca đó không có việc hoặc không phát sinh thành công mới.
