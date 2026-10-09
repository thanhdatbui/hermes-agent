# Telegram Multi-ISP Send Failover & OmniRoute SQLite Tuning (01/10/2026)

## 1. Telegram Multi-ISP Send Failover (WARP / Proxy ↔ FPT Direct)

### Triệu chứng & Điểm mù (Silent Undeliverable)
- Polling (`get_updates_request`) đã có `TelegramMultiISPTransport` để failover qua FPT Direct khi Viettel Proxy (`192.168.110.2:10001`) hoặc WARP chập chờn.
- Tuy nhiên, luồng gửi phản hồi và sửa tin (`request`) trước đây vẫn chỉ nhận `proxy=proxy_url` đơn lẻ.
- **Hệ quả**: Bot vẫn nhận được tin nhắn từ Telegram (polling sống), nhưng khi gửi câu trả lời thì request bị nghẽn/timeout trên proxy chết $\rightarrow$ Bot im lặng hoàn toàn trên Telegram dù log hiển thị đã xử lý xong.

### Bản vá Kiến trúc (3 Vị trí Đồng bộ)
1. **Khởi tạo Dual Transport trong `adapter.py`**:
   ```python
   # plugins/platforms/telegram/adapter.py
   _multi_transport_send = TelegramMultiISPTransport(
       fallback_ips=fallback_ips,
       stall_threshold_s=stall_s,
       recovery_probe_interval_s=probe_s,
       **_multi_kwargs,
   )
   request = HTTPXRequest(
       **request_kwargs,
       httpx_kwargs={"transport": _multi_transport_send},
   )
   get_updates_request = HTTPXRequest(
       **request_kwargs,
       httpx_kwargs={"transport": _multi_transport_polling},
   )
   ```
2. **Đồng bộ 3 nơi trên máy**:
   - `C:\Users\Kibe\AppData\Local\hermes\hermes-agent\plugins\platforms\telegram\adapter.py`
   - `C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\Lib\site-packages\plugins\platforms\telegram\adapter.py`
   - `D:\Taadaa\Hermes\plugins\platforms\telegram\adapter.py`
3. **Kiểm chứng tự động (Unit Test)**:
   - File test: `tests/test_telegram_send_failover.py`
   - Lệnh chạy: `pytest tests/test_telegram_send_failover.py` (3 passed).
   - Kiểm tra `request` và `get_updates_request` đều được khởi tạo instance transport riêng biệt.

---

## 2. OmniRoute SQLite Maintenance & Anti-Hang (Incident 30/09 - 01/10/2026)

### Sự cố Treo Luồng & Crash 0xC0000409
- Luồng chính của Node.js bị block bởi thao tác bảo trì SQLite đồng bộ (checkpoint WAL 1.8GB mỗi 6 giờ kèm VACUUM).
- Hai bảng phình to nhất:
  - `quota_snapshots`: Lưu lịch sử snapshot quota của các account để vẽ chart.
  - `conversation_turn_nodes`: Lưu cây hội thoại rẽ nhánh cũ.
- Khi dung lượng đạt ~1.9GB và WAL ~1.8GB, thời gian khởi động lên tới 150s, timeout admission queue, crash `STATUS_STACK_BUFFER_OVERRUN` (0xC0000409).

### Quy trình Dọn Dẹp & Thu Nhỏ O(1)
1. Xóa bản ghi > 3 ngày (an toàn 100%, không mất tokens/credentials/routing):
   ```sql
   DELETE FROM quota_snapshots WHERE timestamp < strftime('%s', 'now', '-3 days');
   DELETE FROM conversation_turn_nodes WHERE created_at < datetime('now', '-3 days');
   PRAGMA wal_checkpoint(TRUNCATE);
   VACUUM;
   ```
   - Kết quả: `storage.sqlite` từ 1888MB $\rightarrow$ 597MB, WAL từ 1.8GB $\rightarrow$ 4MB, startup time từ 150s $\rightarrow$ 44s.
2. Cấu hình Watchdog Node.js (`omniroute_watchdog.ps1`):
   - Nâng trần bộ nhớ: `--max-old-space-size=8192` (8GB heap).
   - Checkpoint WAL nhỏ giọt mỗi 5 phút (thay vì 6 tiếng dồn 1 lần).
   - Giới hạn body log 64KB, cắt chuỗi tối đa 16KB, retention log 7 ngày, bỏ port inspect.

---

## 3. Hermes Context Resolution Order & Ngưỡng nén thực tế

### Thứ tự phân giải Context Length (`get_model_context_length`):
1. **Bước 0**: `model.context_length` trong `config.yaml` (toàn cục). Nếu có (vd: `1000000`), Hermes lấy luôn và **bỏ qua** định nghĩa trong `custom_providers`.
2. **Bước 0b**: `custom_providers[].models.<model>.context_length` chỉ được đọc khi Bước 0 là `None`.
3. **Quy tắc Small-Context Floor (`_effective_threshold_percent`)**:
   - Nếu `context_length < 512.000` (như 200k): Threshold bị nâng lên tối thiểu 75% (`_SMALL_CTX_THRESHOLD_PERCENT = 0.75`).
   - Nếu `context_length >= 512.000` (1M): Giữ nguyên tỉ lệ `compression.threshold: 0.3` (30%).
4. **Ngưỡng nén thực tế của `omni-worker`**:
   - Context length = 1.000.000.
   - Threshold percent = 0.3.
   - Threshold tokens = **300.000 tokens** (luôn kích hoạt trước trần 372k của các worker GPT-5.6).
