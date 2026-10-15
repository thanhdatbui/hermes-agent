# Gateway Auto-Resume After Reboot: Message Timestamp vs Routing updated_at & Lookback

## 1. Triệu chứng & Bối cảnh
Sau khi hệ thống farm hoặc máy host reboot (ví dụ cữ daily reset 05:00 sáng hoặc reboot đột ngột), một số session/topic Telegram đang chạy dở dang không tự động phục hồi (auto-resume) mà bị treo im lặng, buộc User phải gửi tin nhắn mới để đánh thức.

## 2. Nguyên nhân cốt lõi (Root Cause)
Cơ chế bảo toàn session trước khi reboot (`preserve_in_flight_sessions`) và cứu hộ sau crash (`suspend_recently_active`) gặp phải 2 lỗi kiến trúc:

1. **Bẫy `entry.updated_at` trong `gateway_routing`:**
   - Trong kiến trúc Hermes Gateway, trường `entry.updated_at` của bảng `gateway_routing` **chỉ được cập nhật một lần duy nhất khi có tin nhắn mới từ User** (Incoming Event).
   - Khi Agent tiếp nhận lệnh và thực thi chuỗi tool calls, subagents, code-surgery hoặc background processes kéo dài > 20 phút (ví dụ User nhắn lúc 04:55:35, Agent chạy tool liên tục đến 05:20:12 = 25 phút), `entry.updated_at` vẫn bị ghim cứng ở mốc `04:55:35`.
   - Kết quả: Khi script preflight quét lúc 05:20:07 với `lookback_minutes = 20` (cutoff = 05:00:07), phép so sánh `updated < cutoff` dẫn đến việc script hiểu nhầm session đã idle lâu và **bỏ qua không đánh dấu `resume_pending: true`**!

2. **Lớp phòng thủ thứ hai (`suspend_recently_active` trong `session.py`) vướng chung lỗi:**
   - Điều kiện `if not entry.suspended and entry.updated_at >= cutoff:` cũng nhìn vào `entry.updated_at`, khiến phiên khởi động lại sau crash cũng bỏ rơi session.

## 3. Giải pháp chuẩn hóa (Fix Contract)

### A. Truy vấn mốc thời gian thực từ bảng `messages`
Không dựa duy nhất vào `entry.updated_at`. Phải lấy `MAX(timestamp)` từ SQLite `messages` của session để phản ánh đúng thời điểm Agent vừa thao tác:

```python
sid = entry.get("session_id")
with db._lock:
    row_ts = db._conn.execute(
        "SELECT MAX(timestamp) FROM messages WHERE session_id = ? AND active = 1", (sid,)
    ).fetchone()
last_activity_ts = row_ts[0] if (row_ts and row_ts[0]) else None

# Chỉ bỏ qua khi CẢ updated_at VÀ message cuối cùng đều nằm ngoài cutoff:
if updated < cutoff and not (last_activity_ts is not None and float(last_activity_ts) >= cutoff.timestamp()):
    continue
```

### B. Mở rộng khung Lookback an toàn
- Nâng `lookback_minutes` mặc định từ 20 phút lên **60 phút** (3600s).
- Trong `D:/Taadaa/Hermes/gateway/session.py`, helper `_last_message_at(session_id)` được bổ sung trước `suspend_recently_active` và nâng `max_age_seconds` lên **3600**.

### C. Tiêu chí phân loại In-Flight chính xác
- **CẦN RESUME:** Turn cuối cùng là `role == 'user'`, `role == 'tool'`, hoặc `role == 'assistant'` nhưng có tool calls chưa hoàn tất/chưa có kết quả.
- **BỎ QUA (ĐÃ XONG):** Turn cuối cùng là `role == 'assistant'` thuần túy (không có tool call pending), nghĩa là Agent đã trả lời xong và đang đợi User. Bỏ qua đúng thiết kế để tránh spam lại tin nhắn cũ.
