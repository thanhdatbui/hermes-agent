# Anti-Starvation, Fast Fail-Closed & Watchdog Timezone Invariants

Tài liệu hướng dẫn phòng chống nghẽn threadpool và xử lý đồng bộ thời gian trên TikTok Feed Session (cập nhật 2026-10-13).

---

## 1. Phòng chống Threadpool Starvation khi Prepare TikTok (`device_prepare.py`)
- **Triệu chứng:** Khi chạy các slot tài khoản sâu (Row 7, Row 8) hoặc máy bị lag/rớt USB, toàn bộ ca chạy bị kéo dài chạm kịch trần watchdog 2 tiếng (7200s).
- **Nguyên nhân gốc rễ:** 
  Trong `prepare_tiktok_app_for_automation`, hàm `dismiss_popup()` được gọi trong vòng lặp 10 lần retry focus TikTok. Nếu app văng hoặc không thể focus, foreground package là `None` (treo adb) hoặc đang ở màn hình Launcher (`com.sec.android.app.launcher`, Launcher3) / SystemUI. Lúc này, script vẫn gọi `capture_required_ui(timeout=60)` để tìm popup TikTok. 10 lần retry x 60s dump = ngâm threadpool từ 30 đến 76 phút cho mỗi máy hỏng!
- **Kỷ luật bắt buộc:**
  + Lưu cache `_last_focus` từ `read_focus()` (tránh gọi thêm lệnh dumpsys tốn tài nguyên).
  + Trong `dismiss_popup()`: Kiểm tra nếu `_last_focus.get("package")` là `None` hoặc nằm trong allowlist launcher/systemui:
    ```python
    pkg = _last_focus.get("package")
    if not pkg or pkg in (
        "com.sec.android.app.launcher",
        "com.google.android.apps.nexuslauncher",
        "com.android.launcher3",
        "com.android.systemui",
    ):
        logger.info("Skipping popup dismissal: foreground package %s is launcher/systemui", pkg)
        return False
    ```
  + Thời gian xử lý máy lỗi giảm từ 76 phút xuống dưới 10 giây.

---

## 2. Fast Fail-Closed khi Prepare Focus Thất Bại (`multi_machine_feed_session.py`)
- **Kỷ luật:** Thêm `"failed to focus tiktok after launch"` vào `_FATAL_DEVICE_ERROR_PATTERNS`.
- **Hành vi bắt buộc:**
  + Ngay khi `prepare_tiktok` trả về lỗi không focus được app: worker BẮT BUỘC trả về ngay lập tức.
  + CẤM chạy tiếp `follow-hook` hay `upload-hook` (tiết kiệm thêm 45-60s/máy).
  + Phát telemetry warning:
    ```python
    logger.warning(
        "[FAST-FAIL] Machine %s serial %s fatal stop: %s; skipping hooks immediately",
        getattr(account, "machine", "?"),
        getattr(account, "serial", "?"),
        child_result.stop_reason,
    )
    ```
  + Giải phóng slot và release lease ngay cho máy kế tiếp trong queue.

---

## 3. Đồng bộ Múi giờ UTC trong Watchdog Manifest (`feed_session_watchdog.py`)
- **Triệu chứng:** Phiên 1 chạy trễ đè lên Phiên 2 làm watchdog im lặng, không gửi báo cáo lúc 09:24.
- **Nguyên nhân gốc rễ:**
  `run_manifest.json` ghi timestamp chuẩn UTC ISO (`2026-10-13T01:02:39+00:00`). Hàm `_is_session_manifest_completed` cắt chuỗi thô lấy `"01:02"` so sánh với mốc kết thúc HCMC `"08:00"`. Vì `"01:02" < "08:00"` -> watchdog tưởng phiên chưa xong và cluster đang busy, dẫn đến deadlock chặn báo cáo.
- **Kỷ luật bắt buộc:**
  BẮT BUỘC parse datetime ISO và convert sang múi giờ `Asia/Ho_Chi_Minh` (`HCMC`) trước khi so sánh `end_hm >= win_end_hm`:
  ```python
  try:
      dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
      if dt.tzinfo is not None:
          dt = dt.astimezone(HCMC)
      end_hm = dt.strftime("%H:%M")
  except Exception:
      end_hm = end_time.replace("T", " ").split(" ", 1)[-1][:5]
  if end_hm >= win_end_hm:
      return True
  ```

---

## 4. Kỷ luật Test Isolation & Closeout Gate
- **Import Fallback `_path_setup`:**
  Mọi test file trong `python_runner/tests/` phải dùng cơ chế fallback sau để đảm bảo `pytest` chạy độc lập từ repo root qua `closeout_gate.py` không bị `ModuleNotFoundError`:
  ```python
  try:
      import _path_setup  # noqa: F401
  except ModuleNotFoundError:
      import sys
      from pathlib import Path
      _tests_dir = Path(__file__).resolve().parent
      if str(_tests_dir) not in sys.path:
          sys.path.insert(0, str(_tests_dir))
      import _path_setup  # noqa: F401
  ```
- **Hợp nhất Candidate Diff:**
  Khi thẩm định qua Closeout Gate (`closeout_gate.py`), `HEAD~1..HEAD` phải chứa đầy đủ logic runtime + telemetry + test suite tương ứng để Sol Auditor đánh giá toàn diện, tránh tình trạng commit lẻ tẻ chỉ có test khiến reviewer trừ điểm phạm vi chứng minh hẹp.
