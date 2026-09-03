# Hard Outer Watchdog Queue-Time vs Execution-Time False Alarm (2026-08-24)

## 1. Hiện tượng & Báo cáo Alert
- Alert Telegram / Farm Alerts: `[MÁY X] DỪNG PHIÊN | hard outer watchdog timeout exceeded (35.1m > 35.0m)`.
- Hiện trường / log của máy con: máy thực tế đã hoàn thành đủ số swipe (ví dụ 11/11 video), status `success`, thời gian chạy thực chỉ 12–18 phút.

## 2. Nguyên nhân cốt lõi (Root Cause)
- Khi chạy ca lớn (ví dụ 72+ máy) với `max_workers < tổng số máy` (ví dụ `max_workers = 40`), một nửa số máy thuộc đợt sau phải xếp hàng chờ trong `ThreadPoolExecutor` queue từ 15–25 phút trước khi có luồng rảnh.
- Trước đây, `futures[future] = (account, reservation, time.monotonic())` ghi lại mốc `start_mono` ngay tại thời điểm submit vào executor.
- Vòng lặp quét watchdog ở tiến trình cha so sánh `now_mono - futures[f][2] > worker_hard_timeout (30m + 5m = 35m)`. Do thời gian chờ hàng đợi cộng dồn với thời gian chạy thực vượt quá 35 phút, máy bị cha đánh dấu fail do timeout và gửi alert Telegram sai (False-Fail), dù tiến trình con vẫn đang chạy hoàn toàn bình thường và sau đó hoàn tất thành công.

## 3. Kiến trúc giải pháp chuẩn
Ghi nhận thời điểm bắt đầu chạy thực sự của worker qua timing dictionary được kích hoạt bên trong worker wrapper:
```python
timing: dict[str, float] = {}

def worker_wrapper(
    _ctx: DeviceContext,
    _account: MachineAccount,
    _adb: str,
    _res: Any,
    _timing: dict[str, float],
) -> MachineFeedSessionResult:
    _timing["start_mono"] = time.monotonic()
    return _run_child(_ctx, _account, _adb, _res)

future = executor.submit(worker_wrapper, ctx, account, resolved_adb or fallback_adb, reservation, timing)
futures[future] = (account, reservation, timing)
```

Khi quét watchdog:
```python
now_mono = time.monotonic()
timed_out_futures = []
for f in list(pending_futures):
    _timing = futures[f][2]
    _start_mono = _timing.get("start_mono")
    if _start_mono is not None and (now_mono - _start_mono) > worker_hard_timeout:
        timed_out_futures.append(f)
```

## 4. Quy tắc kiểm tra (Regression Contract)
- Test case `test_hard_outer_watchdog_starts_from_execution_not_queue_time`: giả lập `max_workers=1` với 2 máy; máy 2 chờ trong queue thời gian dài hơn timeout nhưng thời gian chạy thực tế ngắn → kết quả toàn batch và từng máy phải đạt `final_status: success`.
