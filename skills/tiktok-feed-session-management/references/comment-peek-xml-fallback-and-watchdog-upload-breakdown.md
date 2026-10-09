# Comment Peek XML Fallback & Watchdog Upload Breakdown

## 1. Comment Peek Fail-Silent do Thiếu In-Memory `raw_xml`

### Hiện tượng & Root Cause
- Thống kê phiên trên toàn farm liên tục báo: `Đọc comment: 0 lượt / 1300 video (0.0%)`.
- Trong `feed_swipe_smoke.py`, hàm `_maybe_peek_comments(ctx, after_attempt, peek_rate_percent)` yêu cầu:
  ```python
  xml_text = after_attempt.get("raw_xml")
  if not xml_text:
      return False
  ```
- Tuy nhiên, trong pipeline thu thập `_capture_step()`, đối tượng `after` (chuyển đổi từ `FeedStep.as_dict()`) chỉ lưu đường dẫn file XML trên đĩa (`after["xml_path"]`), hoàn toàn không lưu chuỗi `raw_xml` trong RAM (để tối ưu memory footprint cho multi-worker).
- Hậu quả: `after_attempt.get("raw_xml")` luôn trả về `None`, dẫn đến tính năng Comment Peek bị bỏ qua 100% trên toàn bộ 80 máy mà không phát sinh bất kỳ exception nào trong log!

### Chuẩn Fix (Lazy Fallback từ `xml_path`)
Trước khi chuyển `after` vào `_maybe_peek_comments`, tự động đọc nội dung file từ `xml_path` nếu `raw_xml` chưa có trong memory:
```python
if is_feed_session and is_deep_inspect_video:
    after["is_deep_inspect"] = True
    if not after.get("raw_xml") and after.get("xml_path"):
        try:
            from pathlib import Path
            xp = Path(str(after.get("xml_path")))
            if xp.is_file():
                after["raw_xml"] = xp.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            pass
    if _maybe_peek_comments(ctx, after, peek_rate_percent=session_comment_peek_rate):
        after["comment_peeked"] = True
```

---

## 2. Bóc Tách Chi Tiết Lý Do Bỏ Qua Upload Trên Watchdog (Chống Gom Nhãn "Khác")

### Hiện tượng
- Báo cáo ca gửi Telegram ghi: `Bỏ qua (79): Đang dưỡng sinh (17); Chưa render/thiếu video (3); Khác (59)`.
- Nhãn `Khác (59)` che lấp toàn bộ hiện trạng vận hành thực tế của farm, khiến người vận hành hoang mang không biết tại sao 59 máy không đăng được video.

### Root Cause
- Khi upload hook kết thúc, các trạng thái skipped mang nhiều lý do nghiệp vụ khác nhau:
  1. `already_uploaded_in_shift`: Đã từng khởi chạy trong phiên trước đó của cùng ca (tránh đăng 2 lần/ngày).
  2. `account_creation_date_unverifiable`: Chưa đối soát được ngày tạo tài khoản trên hệ thống sheet/config.
  3. `account_cooling_period_until_...` / `under_10_days` / `age_gate`: Tài khoản đang trong thời gian ngâm cooldown an toàn.
- Watchdog gom chung tất cả các lý do trên vào một mảng `up_other_skipped`, dẫn đến chữ `Khác (X)` chung chung.

### Chuẩn Phân Loại Watchdog
Tách thành các nhóm danh tính rõ ràng:
1. `up_already_uploaded`: `already_uploaded` hoặc `already_uploaded_in_shift`. Hiển thị: `Đã đăng trong ca (X)`.
2. `up_cooldown`: `account_cooling_period`, `cooling_period`, `age_gate`, `under_10_days`. Hiển thị: `Đang ngâm cooldown/tuổi nick (X)`.
3. `up_unverifiable`: `account_creation_date_unverifiable`. Hiển thị: `Chưa xác thực ngày tạo nick (X)`.
4. `up_other_skipped`: Các lý do ngoại lệ còn lại. Hiển thị: `Khác (X)`.

### Code Contract Implementation (`feed_session_watchdog.py`)
```python
# Khai báo các bucket upload
up_success = []
up_timeout = []
up_error = []
up_rest = []
up_novideo = []
up_already_uploaded = []
up_cooldown = []
up_unverifiable = []
up_other_skipped = []

# Phân loại theo u_reason & u_status
if u_status == "success" and u_code == 0:
    up_success.append(m)
elif u_reason.startswith("already_uploaded") and is_machine_upload_successful_in_shift(target_date, m, active_row):
    up_success.append(m)
elif "organic-rest-day" in u_reason or "rest-day" in u_reason:
    up_rest.append(m)
elif any(k in u_reason for k in ("video_not_rendered", "missing_video_folder")):
    up_novideo.append(m)
elif any(k in u_reason for k in ("already_uploaded_in_shift", "already_uploaded")):
    up_already_uploaded.append(m)
elif any(k in u_reason for k in ("account_cooling_period", "cooling_period", "age_gate", "under_10_days")):
    up_cooldown.append(m)
elif "account_creation_date_unverifiable" in u_reason:
    up_unverifiable.append(m)
elif u_status == "skipped" or any(k in u_reason for k in ("missing_account_id", "not-final-session", "sensitive-skip")):
    up_other_skipped.append(m)
elif "timeout" in u_status or "timeout" in u_reason:
    up_timeout.append(m)
else:
    up_error.append(m)

# Tổng hợp up_skip_parts
up_skip_parts = []
if up_rest:
    up_skip_parts.append(f"Đang dưỡng sinh ({len(up_rest)})")
if up_novideo:
    up_skip_parts.append(f"Chưa render/thiếu video ({len(up_novideo)})")
if up_already_uploaded:
    up_skip_parts.append(f"Đã đăng trong ca ({len(up_already_uploaded)})")
if up_cooldown:
    up_skip_parts.append(f"Đang ngâm cooldown/tuổi nick ({len(up_cooldown)})")
if up_unverifiable:
    up_skip_parts.append(f"Chưa xác thực ngày tạo nick ({len(up_unverifiable)})")
if up_other_skipped:
    up_skip_parts.append(f"Khác ({len(up_other_skipped)})")

up_skip_summary = "; ".join(up_skip_parts) if up_skip_parts else "Không có"
total_up_skipped = len(up_rest) + len(up_novideo) + len(up_already_uploaded) + len(up_cooldown) + len(up_unverifiable) + len(up_other_skipped)
```

### Đồng bộ nghiêm ngặt 3 vị trí:
1. `C:/Users/Kibe/AppData/Local/hermes/scripts/feed_session_watchdog.py`
2. `D:/Taadaa/Hermes/deploy/hermes-home/scripts/feed_session_watchdog.py` (hoặc `D:/Taadaa/tiktok-luot nuoi acc/scripts/hermes_cron/feed_session_watchdog.py`)
3. `D:/Taadaa/tiktok-luot nuoi acc/scripts/feed_session_watchdog.py`
Unit test: `pytest C:/Users/Kibe/AppData/Local/hermes/scripts/test_feed_session_watchdog.py`

---

## 3. Argparse Duplicate Argument trong Hook Subprocess

### Cạm bẫy
- Trong `Tiktok-video/scripts/tiktok_workflow/run_post.py`, việc định nghĩa 2 lần `parser.add_argument("--video-source-root", ...)` khiến CLI văng `argparse.ArgumentError: conflicting option string: --video-source-root`.
- Khi hook đăng video gọi subprocess, toàn bộ 42 máy bị crash ngay ở dòng lệnh khởi tạo, không thể upload.
- Hơn nữa, trước khi subprocess chạy, `_ShiftUploadLedger.record_launched()` đã ghi nhận trạng thái `launched` vào `shift_upload_history.json`.
- Do đó, khi sang Phiên 2 cùng ca, máy kiểm tra ledger thấy phiên 1 đã từng claim `launched` nên tiếp tục bỏ qua với lý do `already_uploaded_in_shift`, gây tê liệt hoàn toàn cả ca nuôi nick.

### Quy tắc kiểm tra
- Bắt buộc kiểm tra `pytest tests/test_run_post_cli_args.py` trước khi deploy thay đổi CLI runner.
- Nếu subprocess fail ngay khâu spawn (`record_spawn_failed`), bắt buộc revert trạng thái trong ledger để tránh fail-closed lan truyền sang các phiên kế tiếp.
