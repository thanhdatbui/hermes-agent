# Auto-Resume Session Sau Reboot: Cơ Chế Bảo Toàn In-Flight Session Dựa Trên MAX(messages.timestamp)

## 1. Bản Chất Sự Cố (Root Cause)

Khi máy tính reboot (định kỳ qua script preflight reset hoặc do người dùng khởi động lại), Hermes Gateway được thiết kế để tự động phục hồi các session đang làm việc dở dang thông qua cơ chế `_schedule_resume_pending_sessions()` dựa trên cờ `resume_pending = true` và `suspended = true` trong bảng `gateway_routing`.

Tuy nhiên, có một bẫy kiến trúc nghiêm trọng trong cách tính mốc thời gian hoạt động của session:
- **Lỗ hổng `entry['updated_at']`:** Trong kiến trúc Hermes Gateway, trường `entry['updated_at']` của bảng định tuyến `gateway_routing` **chỉ được cập nhật một lần duy nhất khi người dùng gửi tin nhắn mới vào**.
- **Hệ quả khi Agent chạy tool dài:** Khi Agent chạy một chuỗi tool calls, subagents, vá file hoặc chẩn đoán kéo dài (ví dụ: User gửi tin nhắn lúc `04:55:35`, Agent chạy tool liên tục đến `05:20:12` là gần 25 phút), `entry['updated_at']` trong bảng routing vẫn bị ghim cứng ở mốc `04:55:35`.
- Khi script preflight (`farm_preflight_daily_reset.py`) quét kiểm tra trước lúc reboot với ngưỡng cắt `lookback_minutes = 20` (ví dụ lúc `05:20:07`, mốc cutoff là `05:00:07`), do `04:55:35 < 05:00:07`, script ngỡ rằng session này đã bất động hơn 20 phút và **bỏ qua không đánh dấu `resume_pending = true`**!
- Đồng thời ở lớp phòng vệ thứ hai khi Gateway boot dậy (`suspend_recently_active()` trong `gateway/session.py`), điều kiện `entry.updated_at >= cutoff` cũng bỏ sót session này vì cùng lý do.

---

## 2. Giải Pháp Triệt Để (Architecture Fix)

### Điểm 1: Truy Vấn Mốc Thời Gian Thực Từ SQLite `messages`
Thay vì chỉ dựa vào `entry['updated_at']`, bắt buộc phải truy vấn mốc thời gian thực tế của hành động gần nhất từ bảng `messages` trong session database:
```python
sid = entry.get("session_id")
with db._lock:
    row_ts = db._conn.execute(
        "SELECT MAX(timestamp) FROM messages WHERE session_id = ? AND active = 1", (sid,)
    ).fetchone()
last_activity_ts = row_ts[0] if (row_ts and row_ts[0]) else None

# Xét tiếp nếu EITHER updated_at nằm trong cutoff HOẶC last_activity_ts nằm trong cutoff:
if updated < cutoff and not (last_activity_ts is not None and float(last_activity_ts) >= cutoff.timestamp()):
    continue
```

### Điểm 2: Nới Lỏng Lookback Window Lên 60 Phút
- Nâng `lookback_minutes` mặc định từ 20 phút lên **60 phút** trong script preflight reboot (`farm_preflight_daily_reset.py` ở cả `C:/Taadaa_Service` và repo `tools`).
- Nâng `max_age_seconds` trong `suspend_recently_active()` của `gateway/session.py` từ 1800s (30 phút) lên **3600s (1 giờ)**.

### Điểm 3: Bổ Sung Helper `_last_message_at` Trong `gateway/session.py`
```python
def _last_message_at(session_id: str) -> Optional[datetime]:
    try:
        from hermes_state import SessionDB
        db = SessionDB()
        with db._lock:
            row = db._conn.execute(
                "SELECT MAX(timestamp) FROM messages WHERE session_id = ? AND active = 1", (session_id,)
            ).fetchone()
        if row and row[0]:
            return datetime.fromtimestamp(float(row[0]))
    except Exception:
        pass
    return None
```
Trong `suspend_recently_active()`:
```python
last_msg_at = _last_message_at(entry.session_id)
if entry.updated_at < cutoff and (last_msg_at is None or last_msg_at < cutoff):
    continue
```

### Điểm 4: Giữ Nguyên Fail-Safe Chống Spam
Chỉ đánh dấu `resume_pending` khi:
1. `last_role in ('user', 'tool')` HOẶC
2. `last_role == 'assistant'` nhưng có `tool_calls` chưa có kết quả (tool call pending).
Nếu tin nhắn cuối là `assistant` thuần túy đã trả lời xong và không còn tool chờ phản hồi: **Bắt buộc bỏ qua** để tránh tự động thức dậy spam người dùng sau khi reboot.
