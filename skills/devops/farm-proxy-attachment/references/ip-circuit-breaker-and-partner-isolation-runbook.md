# TikTok Follow Farm IP Circuit Breaker & Partner Machine Isolation Runbook

## Bối cảnh sự cố & Số liệu thực tế (2026-10-10)
Đo đạc trên 301 ca chạy thực tế từ tháng 8 đến tháng 10:
- **Chạy đôi cùng IP (2 máy/IP)**: Tỷ lệ dính cờ nhả/drop follow lên tới **70.6%** (24/34 ca).
- **Chạy solo (1 máy/IP)**: Tỷ lệ nhả chỉ là **36.4%** (39/107 ca).
- **Hiện tượng Cascading Failure (Dắt dây theo IP)**: Khi Máy A dính nhả (`FOLLOW_FAILED`), TikTok cắm cờ cấm follow trên IP đó trong 12–24h. Nếu Máy B dùng chung IP chạy ngay sau đó trong vòng 2–20 phút, Máy B chắc chắn ăn nhả ngay từ lượt đầu tiên (0 lượt), khiến cả 2 tài khoản đều bị TikTok phạt oan.

## Kiến Trúc Cầu Dao Tự Ngắt IP (`ip_circuit_breaker.py`)

### 1. Trip Trigger (Khi Máy A dính nhả)
Khi `follow_state.py` nhận tín hiệu `FOLLOW_FAILED` từ runner:
```python
# Tự động giật cầu dao ngắt cổng proxy của máy A cho đến hết ngày
trip_ip_breaker(
    db_path="D:/Taadaa/data/tiktok_tracker.db",
    machine_num=self.machine_num,
    proxy_port=self.proxy_port,
    reason=f"M{self.machine_num} dính FOLLOW_FAILED: {reason}"
)
```

### 2. Preflight Check (Khi Máy B bắt đầu ca)
Trước khi khởi tạo phiên follow trên Máy B (`run_follow.py`):
```python
is_tripped, trip_reason, tripped_m = check_ip_breaker(
    db_path="D:/Taadaa/data/tiktok_tracker.db",
    machine_num=machine_num,
    proxy_port=proxy_port
)
if is_tripped:
    logger.warning("IP CIRCUIT BREAKER TRIPPED by M%s: %s -> Safe Skip!", tripped_m, trip_reason)
    record_saved_machine("D:/Taadaa/data/tiktok_tracker.db", proxy_port, machine_num)
    return {"status": "CIRCUIT_BREAKER_SKIPPED", "followed_count": 0, "reason": trip_reason}
```

### 3. Nguyên Tắc An Toàn
- **Safe Skip (Không phạt nick)**: Trạng thái `CIRCUIT_BREAKER_SKIPPED` được phân loại là bỏ qua an toàn, tuyệt đối không tính vào streak lỗi hay đẩy nick vào Probation/Cooldown.
- **Auto-Reset theo ngày**: CSDL lưu trường `target_date`, cầu dao tự động đóng lại (reset) vào 00:00:00 của ngày tiếp theo.
- **Wave Scheduling**: Turn 1 bốc các máy hoàn toàn độc lập IP (tối đa 40 máy). Turn 2 chạy các máy còn lại sau khi đã loại trừ các cổng bị cầu dao ngắt ở Turn 1.
