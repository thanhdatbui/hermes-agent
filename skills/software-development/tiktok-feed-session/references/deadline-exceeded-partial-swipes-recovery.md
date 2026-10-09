# Xử lý RunPlanDeadlineExceeded khi đã có video lướt thành công (Partial Swipes)

## 1. Bối cảnh & Hiện tượng lỗi
- **Alert:** `🚨 [MÁY N] DỪNG PHIÊN • Lý do: run plan max_duration_seconds exceeded before capture swipe_X_after_gemphonefarm_blind_popup attempt 1 • Trạng thái: 🟡 GIỮ HIỆN TRƯỜNG ĐỂ HERMES AGENT XỬ LÝ`
- **Hiện trường:** Điện thoại ở màn hình video TikTok bình thường hoặc vừa dismiss popup, tài khoản đã lướt được một số video (ví dụ: 9 video), nhưng hết thời lượng tối đa cho phép của phiên (`_deadline_monotonic`).

## 2. Nguyên nhân cốt lõi
- `ensure_run_plan_deadline(config, operation)` kiểm tra `time.monotonic() >= float(deadline)` và bắn ngoại lệ `RunPlanDeadlineExceeded`.
- Trong `feed_swipe_smoke.py`, cả 2 khối bắt lỗi `except RunPlanDeadlineExceeded`:
  - `feed_session_smoke` (khoảng dòng 23167)
  - `feed_swipe_smoke` (khoảng dòng 22760)
  trước đây bị **hardcode ép cứng** `partial.details["final_status"] = "failed"` và trả về `ExitStatus.FAIL` vô điều kiện.
- Hậu quả:
  1. `multi_machine_feed_session.py` thấy `final_status != "success"` và `final_status != "degraded"`, lập tức gửi Farm Alert dừng máy giả (false-positive).
  2. Bỏ qua quy trình cleanup đóng app / bấm HOME / nhả device lock (vì `_cleanup_on_stop` mặc định là False), khiến máy bị bỏ lại ở hiện trường.

## 3. Quy chuẩn phân loại kết quả khi chạm Deadline (Graceful Deadline Degradation)
Khi chạm deadline, kiểm tra số lượt lướt đã hoàn thành trong `partial = ctx.config.get("_feed_swipe_partial_result")`:
```python
completed = int(partial.details.get("total_swipes_completed") or partial.details.get("actual_swipe_count") or 0)
target = int(partial.details.get("selected_total_videos") or partial.details.get("total_swipes_requested") or 1)

if completed >= target and target > 0:
    partial.details["final_status"] = "success"
    partial.details["stop_reason"] = ""
    partial.details.setdefault("summary", {})["stop_reason"] = ""
    partial.details["summary"]["reason"] = "feed session completed at deadline"
    result = FlowResult(ExitStatus.SUCCESS, "feed session completed at deadline", partial.details)
elif completed > 0:
    stop_msg = f"session deadline reached after {completed}/{target} swipes completed"
    partial.details["final_status"] = "degraded"
    partial.details["stop_reason"] = stop_msg
    partial.details.setdefault("summary", {})["stop_reason"] = stop_msg
    partial.details["summary"]["reason"] = stop_msg
    result = FlowResult(ExitStatus.DEGRADED, stop_msg, partial.details)
else:
    partial.details["final_status"] = "failed"
    partial.details["stop_reason"] = str(exc)
    partial.details.setdefault("summary", {})["stop_reason"] = str(exc)
    partial.details["summary"]["reason"] = str(exc)
    result = FlowResult(ExitStatus.FAIL, str(exc), partial.details)
```

## 4. Kiểm chứng & Regression Test
- File test: `python_runner/tests/test_feed_swipe_smoke.py`
- Lệnh chạy: `pytest python_runner/tests/test_feed_swipe_smoke.py -k "deadline" -v`
- Kiểm tra 2 kịch bản:
  1. `completed == 0`: trả về `ExitStatus.FAIL` (chưa lướt được video nào mà hết giờ).
  2. `completed > 0`: trả về `ExitStatus.DEGRADED` (hoặc `SUCCESS` nếu đã đủ target), cleanup được gọi và không bắn Farm Alert.
