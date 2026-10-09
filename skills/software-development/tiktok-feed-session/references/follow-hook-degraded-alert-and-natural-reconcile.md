# Follow Hook Degraded Alert & Natural Follow Reconcile Architecture

## 1. Cơ Chế Dual-Gate Cho Follow Hook (2026-09-28)
- Trong `multi_machine_feed_session.py`, bước follow-hook gọi subprocess `tiktok-follow`.
- Khi Module 2 (Anchor following) lỗi mở tab sau 2 lần thử:
  - Code trong `tiktok-follow` safe-skip anchor và ghi cờ `mode2_degraded=True` kèm `mode2_degraded_reasons` vào payload kết quả.
  - Module 1 (Search follow bù) tiếp tục chạy để không làm hỏng chỉ tiêu phiên.
  - Ngay cả khi kết quả cuối cùng là `status="OK"` và `failed=0`, runner farm **BẮT BUỘC** phải phát Farm Alert nếu cờ `mode2_degraded` bật:
    ```python
    elif (proc.returncode != 0 or bool(result.get("failed"))
          or result.get("status") != "OK" or has_contract_error
          or bool(result.get("mode2_degraded"))):
        # send_farm_machine_alert với error_reason="mode2_degraded: ..."
    ```
  - Đồng thời đánh dấu `result_log="script_error"` để log không bị che giấu lỗi kỹ thuật.

## 2. Đối Soát Following Trong Watchdog (`feed_session_watchdog.py`)
- Khi đối soát tăng following trên TikTok Web với Script, BẮT BUỘC gộp:
  `rep_cnt = cross_cnt (follow chéo) + nat_cnt (follow tự nhiên khi lướt feed)`
- Bỏ sót `natural_follows` sẽ tạo ra sai số ảo giữa Web và Script khiến báo cáo lệch.
