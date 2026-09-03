# Upload Hook Session Timeout & Unconditional Run Contract (2026-08-24)

## 1. Bản chất sự cố Timeout Watchdog ở Phiên 3 (Phiên cuối ca)

Khi vận hành farm nuôi nick TikTok tự động:
- **Cấu trúc ca:** 1 máy chạy 3 ca/ngày (Sáng, Chiều, Tối). Mỗi ca vận hành **1 tài khoản riêng biệt** (3 ca = 3 acc/máy/ngày).
- **Cấu trúc phiên:** Mỗi ca gồm **3 phiên nuôi** (Session 1, 2, 3). Ở phiên cuối (Session 3), flow `multi_machine_feed_session.py` sẽ kích hoạt `_run_upload_hook` để gọi subprocess `scripts.tiktok_workflow` đăng video.
- **Hiện tượng lỗi:** Alert Telegram báo `hard outer watchdog timeout exceeded (15.1m > 15.0m)` tại thời điểm đang upload video dở, dù phần lướt feed đã hoàn thành từ phút thứ 5.
- **Root Cause & Dữ liệu thực tế đo từ 868 lượt upload thành công:**
  - Thời gian chạy upload trung bình (Avg): `8.9 phút` (535.8s)
  - Mức thông thường (Median P50): `8.1 phút` (483.0s)
  - Mức trễ cao (P90): `13.7 phút` (822.0s)
  - Tối đa khi retry / mạng chậm (Max): `25.9 phút` (1556.0s)
  ➔ Chuỗi Session 3 gồm: *Preflight (1-2m) + Feed Swipe (3-5m) + Follow Hook (1-2m) + Upload Video (8-15m) = 15 – 25 phút*. Trần watchdog 15m hoặc 30m không đủ buffer an toàn khi mạng chậm hoặc video lớn.

---

## 2. Chuẩn hóa Timeout & Watchdog (2026-08-24)

- **Cấu hình `DEFAULT_DEVICE_TIMEOUT_SECONDS`:** Nâng từ `600s` (10m) / `1500s` (25m) lên **`2100.0s` (35 phút)**.
- **Trần `worker_hard_timeout`:** Tự động tính bằng `timeout_seconds + 300.0s` = **`2400.0s` (40 phút)**.
- **Mục đích:** Đảm bảo toàn bộ future trong `ThreadPoolExecutor` có đủ ngân sách thời gian để upload và hậu kiểm video mà không bị watchdog bên ngoài ngắt nhầm.

---

## 3. Quy tắc bắt buộc chạy Upload kể cả khi Feed Fail

- **Hợp đồng cũ:** `_run_upload_hook` chỉ được gọi nếu `child_result.final_status in {"success", "degraded"}`.
- **Hợp đồng mới:** Khi đến Session 3 (phiên cuối của ca), flow **BẮT BUỘC** gọi `_run_upload_hook` để đăng video bất kể phiên lướt trước đó có gặp lỗi/manual-needed hay không.
- **Triển khai tại `python_runner/flows/multi_machine_feed_session.py::_run_child`:**
```python
# Upload hook: phiên cuối cùng của ca → gọi upload video (chạy kể cả khi lướt feed fail)
try:
    _run_upload_hook(ctx, account, child_ctx, child_result)
except Exception as exc:
    child_ctx.logger.log(
        device_id=account.serial,
        account=account.expected_username,
        step="upload-hook",
        action="run_upload",
        result="failed",
        artifact_path=str(child_ctx.artifacts.run_dir),
        extra={"upload_hook_error": str(exc)[:180]},
    )
```
- Các gate an toàn bên trong `_run_upload_hook` (check row 1/2, check session 3, check workbook, check video render `.mp4`) vẫn được giữ nguyên độc lập.
