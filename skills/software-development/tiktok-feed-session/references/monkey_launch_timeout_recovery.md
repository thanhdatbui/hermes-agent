# Recovery Hướng dẫn: ADB Timeout Monkey Launch & Tránh Treo Quét Đĩa

## 1. Triệu chứng & Nguyên nhân (Root Cause)
- **Triệu chứng alert:**
  ```text
  adb command timed out: ('...\\adb.exe', '-s', '<serial>', 'shell', 'monkey', '-p', 'com.ss.android.ugc.trill', '-c', 'android.intent.category.LAUNCHER', '1')
  ```
- **Nguyên nhân gốc rễ:**
  - Lệnh `monkey -p com.ss.android.ugc.trill ...` khi gửi qua `adb shell` có thể bị block do ADB daemon trên thiết bị Android bị nghẽn I/O, hệ thống bận, hoặc chính tiến trình monkey bị deadlock/treo khi ứng dụng đang khởi tạo.
  - Trong nhiều trường hợp alert (như Máy 72), thực tế TikTok đã mở sẵn ở màn hình Home Feed (Đề xuất), nhưng script runner vẫn gọi `monkey` để relaunch mà không kiểm tra trạng thái foreground trước.
  - Khi timeout xảy ra, nếu code không bọc `try...except (TimeoutError, Exception)` an toàn, ngoại lệ timeout sẽ làm sập toàn bộ feed session của máy.

## 2. Giải pháp Code (Safe Monkey Launch Pattern)

### A. Preflight Check: Kiểm tra Foreground Trước Khi Launch
Trước khi gọi force-stop hoặc monkey launch, luôn đọc `get_focused_activity(ctx)`:
```python
current_focus = get_focused_activity(ctx)
if current_focus and current_focus.get("package") == target_package:
    # Ứng dụng đã ở foreground sẵn, không cần bắn lệnh monkey gây rủi ro timeout
    return ForceStopRelaunchResult(package_name=target_package, ...)
```

### B. Bọc Bounded Timeout & Try/Except Cho Monkey Shell
Trong `device_prepare.py`, `actions.py`, `feed_swipe_smoke.py`:
```python
try:
    launch_result = ctx.adb.shell(
        ["monkey", "-p", target_package, "-c", "android.intent.category.LAUNCHER", "1"],
        timeout=min(timeout, 15),
    )
except (TimeoutError, Exception) as exc:
    logger.warning("Monkey launch timed out or failed (%s); verifying if app is already foreground", exc)
    # Kiểm tra lại focus thay vì crash ngay lập tức
    post_focus = get_focused_activity(ctx)
    if post_focus and post_focus.get("package") == target_package:
        # App thực tế đã chạy, tiếp tục phiên
        pass
    else:
        # Ghi nhận degraded / raise theo policy có kiểm soát
        ...
```

## 3. Quy Tắc Điều Tra O(1) — Cấm Tuyệt Đối Quét Diện Rộng
- **Tuyệt đối không chạy `grep -rn` hoặc `find` trên thư mục gốc `tiktok-luot nuoi acc`:**
  - Thư mục `.ai-runs` chứa hàng nghìn lượt chạy với hàng gigabytes ảnh PNG và XML UI dump.
  - Lệnh grep/find đệ quy trên Windows MSYS bash sẽ bị treo cứng (timeout 900s), làm cạn kiệt toàn bộ ngân sách execution turn của agent.
- **Cách tra cứu đúng:**
  - Dùng `python D:/Taadaa/tools/inspect_machine.py <N>` để đọc trực tiếp hiện trường máy.
  - Tra cứu trực tiếp file code cụ thể đã biết: `python_runner/flows/device_prepare.py`, `python_runner/core/actions.py`, `python_runner/flows/feed_swipe_smoke.py`.
  - Nếu cần kiểm tra run mới nhất của một máy cụ thể, chỉ đọc file `machines/machine_<N>/.../summary.txt` bên trong thư mục timestamp mới nhất được liệt kê qua `ls -td .ai-runs/2026* | head -n 1`.
