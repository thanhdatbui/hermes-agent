# Multi-shift Watchdog Scheduling & State Management

## 1. Context & Lessons Learned
Khi mở rộng một watchdog ban đầu chỉ chạy một ca (ví dụ: ca tối `post_evening_gpm_login_watchdog`) sang chạy nhiều khung giờ trong ngày (sáng, trưa, tối giữa các ca nuôi feed):
- **Cạm bẫy 1: Hardcoded Header & Report Content**:
  Nếu template báo cáo hardcode `[LOGIN GPM ĐÊM - TỔNG KẾT]` và `Hoàn tất ca tối`, khi watchdog chạy vào khung giờ trưa (12:00 - 13:45) hoặc sáng (07:15 - 08:45), thông báo gửi về Telegram/Discord sẽ gây hoang mang cho người vận hành ("Gì mà giờ ca tối?").
- **Cạm bẫy 2: Cờ `finished: true` khóa cả ngày**:
  Nếu state lưu trữ cờ `finished: true` ở cấp độ ngày (`date: YYYY-MM-DD`), khi ca trưa chạy xong và hết candidate tạm thời, watchdog sẽ tự đánh dấu `finished: true`. Hậu quả: Đến ca tối thực sự (sau 20:15), watchdog kiểm tra thấy `state.get('finished') == True` và return 0, bỏ qua hoàn toàn ca tối.

## 2. Chuẩn Thiết Kế Multi-shift Watchdog
### a. Hàm nhận diện ca động (`get_current_shift_info`)
Tách biệt mã ca (`shift_code`), nhãn hiển thị in hoa (`shift_label`) và mô tả in thường (`shift_desc`):
```python
def get_current_shift_info() -> tuple[str, str, str]:
    now = datetime.now(HCMC)
    current = now.hour * 60 + now.minute
    # Khung giờ rảnh thực tế giữa các ca nuôi feed TikTok:
    if 9 * 60 + 30 <= current <= 11 * 60 + 20:
        return ("SANG", "SÁNG", "sáng")
    if 15 * 60 + 30 <= current <= 17 * 60 + 20:
        return ("CHIEU", "CHIỀU", "chiều")
    if 21 * 60 + 30 <= current <= 23 * 60 + 45:
        return ("TOI", "TỐI", "tối")
    if now.hour < 13:
        return ("SANG", "SÁNG", "sáng")
    elif now.hour < 19:
        return ("CHIEU", "CHIỀU", "chiều")
    return ("TOI", "TỐI", "tối")
```

### b. Báo cáo linh hoạt theo ca & nhường máy an toàn
Báo cáo tổng kết ca tách bạch rõ: thành công, lỗi, và số lượng bỏ qua an toàn nhường máy bận cron nuôi acc:
```python
def _format_summary_report(total_success: int, total_fail: int, shift_label: str = "TỐI", shift_desc: str = "tối", skipped_busy: int = 0) -> str:
    lines = [
        f"[LOGIN GPM {shift_label} - TỔNG KẾT]",
        f"• Kết quả ca: ✓ {total_success} | ✗ {total_fail} | proxy_limit 2/port/ngày | Hoàn tất ca {shift_desc}",
    ]
    if skipped_busy > 0:
        lines.append(f"• Bỏ qua an toàn: {skipped_busy} acc nhường máy đang bận cron khác (TikTok/Avatar)")
    lines.extend([
        f"• Antigravity Pool: {live_anti_count} accounts LIVE trên OmniRoute (:20129)",
        f"• Profile sẵn Google Session chờ OAuth: {session_count} accounts"
    ])
    return "\n".join(lines)
```

### c. State phân tách theo từng ca
Lưu trữ danh sách ca đã báo cáo (`reported_shifts`) và ca đã hoàn tất (`finished_shifts`):
```json
{
  "date": "2026-10-04",
  "processed": [...],
  "proxy_count": {...},
  "total_success": 33,
  "total_fail": 2,
  "reported": true,
  "finished": false,
  "finished_shifts": ["SANG", "CHIEU"],
  "reported_shifts": ["SANG", "CHIEU"]
}
```
- Khi bắt đầu tick: Chỉ skip nếu `is_same_day and shift_code in finished_shifts`.
- Khi kết thúc một ca (hết candidates hoặc hết giờ): Thêm `shift_code` vào `finished_shifts` và `reported_shifts`.
- Cờ toàn ngày `finished` chỉ được set khi ca cuối cùng trong ngày (TỐI) kết thúc hoặc toàn bộ các ca `{"SANG", "CHIEU", "TOI"}` đã hoàn tất.
- **Coordinator O(1) Inspection**: Khi Coordinator cần đọc state tổng kết ca của watchdog, dùng `read_file` trực tiếp vào `D:/Taadaa/runtime/kibe/cron-state/post_evening_gpm_login_state.json` thay vì chạy lệnh shell qua `terminal` (tránh bị chặn bởi Coordinator guard allowlist).
