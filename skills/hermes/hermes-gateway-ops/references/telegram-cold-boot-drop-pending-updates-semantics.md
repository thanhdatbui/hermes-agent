# Telegram Gateway Cold Boot vs Reconnect Update Semantics

## Bối cảnh & Hiện tượng
Khi máy tính chạy Hermes Coordinator (ví dụ máy Kibe) bị khởi động lại (reboot / reset PC):
- Trong thời gian máy đang tắt và gateway chưa khởi động, người dùng gửi tin nhắn trên Telegram.
- Khi bot online trở lại, bot **hoàn toàn không nhận được** các tin nhắn đã gửi trong lúc offline.

## Bản chất kỹ thuật (Mã nguồn Gateway)
Trong adapter Telegram của Hermes (`plugins/platforms/telegram/adapter.py`):
```python
polling_started = await self._start_polling_resilient(
    # On a cold first boot drop the stale Bot API queue; on a
    # watcher reconnect after an outage preserve it so messages
    # sent while the bot was offline are delivered (#46621).
    drop_pending_updates=not is_reconnect,
    error_callback=_polling_error_callback,
)
```

1. **Cold Boot (`is_reconnect=False`):**
   - Khi dịch vụ hoặc tiến trình gateway khởi động từ đầu sau khi boot máy, `drop_pending_updates` được đặt thành `True` (`not False`).
   - Cờ `drop_pending_updates=True` gửi yêu cầu đến Telegram Bot API **xóa sạch toàn bộ update đang chờ trong queue**.
   - Mục đích thiết kế: Tránh tình trạng bot vừa khởi động bị dồn ứ (stampede/flood) hàng loạt lệnh cũ tích tụ trong thời gian downtime dài.

2. **Watcher Reconnect (`is_reconnect=True`):**
   - Khi gateway vẫn đang chạy nhưng bị rớt mạng tạm thời (mất kết nối internet/proxy) và tự động reconnect lại, `drop_pending_updates` là `False`.
   - Hàng đợi tin nhắn trên Telegram được bảo toàn và chuyển tiếp đầy đủ cho bot.

## Bài học vận hành
- Nếu máy PC vừa restart, mọi chỉ thị gửi qua Telegram trong lúc máy đang tắt đều bị hủy trên Telegram server.
- Coordinator / User bắt buộc phải gửi lại prompt sau khi bot đã online (kiểm tra qua log `✓ telegram connected` hoặc trạng thái service).
