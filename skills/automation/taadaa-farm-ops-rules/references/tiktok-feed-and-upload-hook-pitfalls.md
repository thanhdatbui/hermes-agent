# TikTok Feed & Upload Pitfalls: Conflicting CLI Options, In-Memory XML Drop & Watchdog Skip Masking

## 1. Argparse Conflicting Option String in Hook Callers (`run_post.py`)
- **Triệu chứng:** Toàn bộ batch máy chạy feed session thành công nhưng khi chuyển sang upload hook thì đồng loạt fail `returncode=1`, log ghi:
  `argparse.ArgumentError: argument --video-source-root: conflicting option string: --video-source-root`
- **Nguyên nhân:** Khi mở rộng CLI argument trong `run_post.py` (hoặc bất kỳ script entrypoint nào) ở 2 vị trí khác nhau (ví dụ: nhóm argument chung ở trên và nhóm host-aware/aliases ở dưới), `argparse.ArgumentParser` mặc định văng exception `conflicting option string` nếu gặp cùng một cờ option mà không bật `conflict_handler='resolve'`.
- **Cách khắc phục & phòng ngừa:**
  - Giữ duy nhất một định nghĩa canonical cho option CLI kèm theo các aliases (ví dụ: `--video-source-root` và `--media-source-root`).
  - Kiểm tra tính hợp lệ của CLI arguments trước khi merge bằng focused pytest (`tests/test_run_post_cli_args.py`).

## 2. In-Memory XML Drop vs `raw_xml` Callers (`feed_swipe_smoke.py`)
- **Triệu chứng:** Thống kê sau ca nuôi feed luôn ghi nhận 0 lượt xem comment (`comment_peeks = 0`) dù cấu hình tỷ lệ xem sâu `20% - 35%`. Không hề có log lỗi hay exception.
- **Nguyên nhân:**
  - Pipeline chụp màn hình (`_capture_step`) lưu trữ XML ra file đĩa `ui.xml` và trả về `after["xml_path"]` nhằm tối ưu dung lượng RAM in-memory.
  - Các hàm hook hành vi con như `_maybe_peek_comments(ctx, after_attempt)` lại kiểm tra trực tiếp `xml_text = after_attempt.get("raw_xml")`.
  - Vì `after_attempt` không chứa trường `raw_xml`, hàm silently returns `False` ngay ở guard check đầu tiên mà không thực thi logic parse element.
- **Cách khắc phục & phòng ngừa:**
  - Caller trước khi gọi các hàm đòi hỏi chuỗi XML phải fallback load từ file đĩa nếu `raw_xml` chưa có trong RAM:
    ```python
    if not after.get("raw_xml") and after.get("xml_path"):
        try:
            from pathlib import Path
            xp = Path(str(after.get("xml_path")))
            if xp.is_file():
                after["raw_xml"] = xp.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            pass
    ```

## 3. Watchdog Skip Masking: Tránh gom gộp "Khác" gây mơ hồ
- **Triệu chứng:** Watchdog báo cáo `Bỏ qua (79): Khác (59)` khiến người vận hành không nắm được lý do thực tế máy bị bỏ qua hay lỗi ngầm.
- **Thực tế phân bổ:**
  - `already_uploaded_in_shift` (do phiên trước trong ca đã kích hoạt upload).
  - `account_creation_date_unverifiable` (chưa xác minh được tuổi tài khoản trên hệ thống).
  - `account_cooling_period` (tài khoản đang trong chu kỳ ngâm cooldown).
- **Quy tắc thiết kế Watchdog:**
  - Không bao giờ gom toàn bộ các lý do skip vào nhãn `Khác`. Phải bóc tách thành các bucket rõ ràng theo nghiệp vụ:
    - `Đang dưỡng sinh (X)`
    - `Chưa render/thiếu video (X)`
    - `Đã đăng trong ca (X)`
    - `Đang ngâm cooldown (X)`
    - `Chưa xác thực ngày tạo nick (X)`
    - `Khác (X)` (chỉ dành cho các lý do thực sự ngoại lệ chưa định danh).
