# Per-Device 15m Watchdog & Capture Deadline Finalization (2026-08-22)

## 1. Bối Cảnh & Vấn Đề
Khi chạy `multi-machine-feed-session` qua `ThreadPoolExecutor`, một số máy bị mất kết nối ADB (`device not found` / child treo tại `adb wait-for-device`) hoặc kẹt trong vòng lặp UI capture calibration (`_capture_step`).
Nếu chỉ có timeout ở cấp lệnh ADB mà không có deadline ở cấp child context worker:
- Worker lặp lại vô tận hoặc treo ở child process, không bao giờ return `MachineFeedSessionResult`.
- Process cha chờ `future.result()` vô hạn → batch không bao giờ kết thúc, không ghi `summary.txt` cho máy lỗi.
- Cron runner 15 phút kế tiếp bị skip ("already running"), gây tắc nghẽn toàn bộ ca nuôi acc.

## 2. Kiến Trúc Sửa Đổi Bắt Buộc (Contract)

### A. Thiết lập deadline riêng cho từng child worker
Trong `multi_machine_feed_session.py`:
```python
DEFAULT_DEVICE_TIMEOUT_SECONDS = 900.0  # 15 phút
...
timeout_seconds = float(ctx.config.get("_device_timeout_seconds") or ctx.config.get("timeouts", {}).get("device_seconds", DEFAULT_DEVICE_TIMEOUT_SECONDS))
child_config["_deadline_monotonic"] = time.monotonic() + timeout_seconds
```

### B. Deadline guard trong vòng lặp capture
Trong `feed_swipe_smoke.py` (`_capture_step` và `splash_slow_capture_wait`):
```python
for attempt_number in range(1, max_attempts + 1):
    ensure_run_plan_deadline(ctx.config, f"capture {step} attempt {attempt_number}")
    focus = get_focused_activity(ctx)
```

### C. Bắt `RunPlanDeadlineExceeded` và tự đóng gói terminal summary
Trong `feed_session_smoke` và `feed_swipe_smoke`:
```python
try:
    return _feed_session_flow(...)
except RunPlanDeadlineExceeded as exc:
    ctx.logger.log(
        device_id=ctx.device_id,
        account=ctx.account,
        step=f"{SESSION_ARTIFACT_PREFIX}/deadline_exceeded",
        action="deadline_exceeded",
        result="failed",
        error=str(exc),
    )
    partial = ctx.config.get("_feed_swipe_partial_result")
    if isinstance(partial, FlowResult):
        partial.details["final_status"] = "failed"
        partial.details["stop_reason"] = str(exc)
        result = FlowResult(ExitStatus.FAIL, str(exc), partial.details)
    else:
        result = FlowResult(ExitStatus.FAIL, str(exc), {
            "final_status": "failed",
            "stop_reason": str(exc),
            "total_swipes_completed": 0,
            "summary": {"reason": str(exc), "stop_reason": str(exc)},
        })
    final = finalize_feed_session_cleanup(ctx, result, artifact_prefix=SESSION_ARTIFACT_PREFIX, summary_key="feed_session_summary")
    ctx.config["_feed_swipe_partial_result"] = final
    return final
```

## 3. Quy Trình Xử Lý Khi Có Máy Treo Quá 15 Phút Trên Live
1. **Kiểm tra process tree:** Dùng CIM/PowerShell kiểm tra PID python cha và PID adb.exe con đang chạy `wait-for-device`.
2. **Không kill bừa bãi cả farm:** Chỉ dừng đúng child ADB/Python của ca treo sau khi đã xác định rõ artifact và log.
3. **Bổ sung `summary.txt`:** Nếu ca cũ chết đột ngột chưa kịp ghi manifest/summary, viết bổ sung `summary.txt` (`final_status: failed`) để cron watchdog và công cụ phân tích không báo treo giả.
4. **Kiểm tra cron:** Gọi `cronjob list` xác nhận các job `phase9-runner-tiktok-feed` và `phase9-watcher-tiktok-feed` đã sẵn sàng cho lượt chạy tiếp theo.
