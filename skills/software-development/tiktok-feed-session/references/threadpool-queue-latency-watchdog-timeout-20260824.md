# ThreadPoolExecutor Queue Latency & Hard Outer Watchdog False-Fail (2026-08-24)

## 1. Bản chất sự cố & Dấu hiệu nhận diện

- **Hiện tượng / Alert:**
  - Telegram Farm Alerts báo: `🚨 [MÁY XX] DỪNG PHIÊN` kèm `Lý do: hard outer watchdog timeout exceeded (35.1m > 35.0m)` và `🟡 GIỮ HIỆN TRƯỜNG ĐỂ HERMES AGENT XỬ LÝ`.
  - Tuy nhiên, ảnh đính kèm hiện trường là TikTok đang phát video bình thường (hoặc màn hình Profile khớp account), không có dấu hiệu treo hay lỗi.
  - Khi kiểm tra `run_manifest.json` trong thư mục máy con sau đó: `final_status: success`, số swipes hoàn thành đủ 100% (ví dụ 10-11/11 swipes), thời gian thực thi thực tế chỉ ~15–18 phút.
  - Sự cố xảy ra hàng loạt trên các máy thuộc đợt sau (ví dụ máy 6, 7, 13, 16, 19, 35, 44, 59 trong batch 72 máy với `max_workers = 40`).

---

## 2. Root Cause: Queue Latency vs Execution Duration

Trong kiến trúc `ThreadPoolExecutor` đa máy:
- Khi batch 72 máy chạy với `max_workers = 40`, 40 máy đầu tiên nhận thread thực thi ngay, còn 32 máy còn lại phải xếp hàng chờ trong hàng đợi (`queue`) khoảng 20–23 phút.
- **Lỗi logic cũ:** Gán `start_mono = time.monotonic()` ngay tại thời điểm `executor.submit(...)` (lúc đưa future vào hàng đợi).
- Khi watchdog ngoài (`hard outer watchdog`) chạy vòng lặp kiểm tra định kỳ:
  $$\text{elapsed} = \text{now\_mono} - \text{submit\_mono}$$
- Khi thời gian nằm chờ trong queue (~22 phút) + thời gian chạy thực tế (~13 phút) vượt quá trần 35 phút (30m + 5m margin), watchdog ngắt kết quả máy con thành `failed`, ghi `hard outer watchdog timeout exceeded`, kích hoạt lock handoff và gửi alert Telegram, trong khi worker con vẫn đang lướt feed thành công trên background thread.

---

## 3. Kiến trúc sửa đổi chuẩn (Worker Start Timing Wrapper)

Không tính mốc thời gian timeout từ lúc submit vào executor; chỉ tính mốc `start_mono` tại thời điểm worker con thực sự được luồng xử lý thực thi:

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

Và trong vòng lặp watchdog:
```python
now_mono = time.monotonic()
timed_out_futures = []
for f in list(pending_futures):
    _timing = futures[f][2]
    _start_mono = _timing.get("start_mono")
    if _start_mono is not None and (now_mono - _start_mono) > worker_hard_timeout:
        timed_out_futures.append(f)
for future in timed_out_futures:
    pending_futures.remove(future)
    account, reservation, timing = futures[future]
    start_mono = timing.get("start_mono", now_mono)
    elapsed_m = round((now_mono - start_mono) / 60.0, 1)
    err_msg = f"hard outer watchdog timeout exceeded ({elapsed_m}m > {round(worker_hard_timeout/60.0, 1)}m)"
    ...
```

---

## 4. Triage Checklist khi gặp Hard Outer Watchdog Alert

1. **Kiểm tra thời gian thực thi của child:** Đọc `start_time` và `end_time` trong `machines/machine_<id>/<run_id>/run_manifest.json`. Nếu `end_time - start_time < 30m` và `final_status: success`, đây là false-fail do queue latency.
2. **Kiểm tra tổng số máy trong batch vs max_workers:** Nếu `len(machines) > max_workers`, các máy đợt 2+ bắt buộc phải được bảo vệ bởi timing wrapper đo lường thời gian chạy thực.
