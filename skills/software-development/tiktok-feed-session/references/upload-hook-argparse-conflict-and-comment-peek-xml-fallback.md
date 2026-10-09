# Phân tích nguyên nhân & Pitfall: Hook Upload Crash & Comment Peek Silent Skip (16/09/2026)

### 1. Sự cố Hook Upload văng Argparse Error làm hàng loạt máy không đăng được video
* **Hiện tượng:**
  * Toàn bộ các máy tới bước upload hook đều thất bại hoặc văng lỗi mà không đăng được video.
  * Sang phiên 2, watchdog báo `Bỏ qua (79): Khác (59)`, khiến user hoang mang không rõ vì sao không đăng được.
* **Nguyên nhân gốc rễ:**
  * Trong `D:/Taadaa/Tiktok-video/scripts/tiktok_workflow/run_post.py`, CLI `argparse` bị khai báo trùng lặp option string `--video-source-root` (dòng 1694 và dòng 1765).
  * Khi runner gọi subprocess `python -m scripts.tiktok_workflow --video-source-root ...`, Python văng ngay từ bước parse CLI:
    `argparse.ArgumentError: argument --video-source-root: conflicting option string: --video-source-root`.
  * Vì subprocess văng `returncode=1`, nhưng hệ thống đã kịp ghi nhận token đặt chỗ `launched` vào `shift_upload_history.json`, sang phiên tiếp theo máy kiểm tra thấy phiên trước đã có token nên skip với lý do `already_uploaded_in_shift`.
* **Khắc phục:**
  * Gỡ bỏ khai báo duplicate đầu tiên ở dòng 1694, giữ nguyên khai báo chuẩn ở dòng 1765 (có `dest="video_source_root"` và alias `--media-source-root`).
  * Verify bằng unit test: `pytest D:/Taadaa/Tiktok-video/tests/test_run_post_cli_args.py`.

---

### 2. Sự cố Đọc Comment 0 Lượt (Silent Skip Comment Peek trên toàn farm)
* **Hiện tượng:**
  * Watchdog báo cáo `Đọc comment: 0 lượt / 1300 video (0.0%)` dù tính năng Comment Peek đã được merge và cấu hình tỷ lệ 20% - 35%.
* **Nguyên nhân gốc rễ:**
  * Trong `python_runner/flows/feed_swipe_smoke.py`, hàm `_maybe_peek_comments` kiểm tra `xml_text = after_attempt.get("raw_xml")`.
  * Tuy nhiên, luồng chụp màn hình chuẩn của runner sau các đợt tối ưu RAM chỉ lưu đường dẫn file đĩa `after["xml_path"]` (`ui.xml`) mà không giữ chuỗi `raw_xml` trong in-memory dict `after`.
  * Do `after.get("raw_xml")` luôn trả về `None`, hàm `_maybe_peek_comments` âm thầm `return False` ngay dòng đầu tiên mà không log lỗi, khiến toàn bộ 80 máy bị skip 100% tính năng đọc comment.
* **Khắc phục:**
  * Bổ sung fallback đọc `raw_xml` từ `xml_path` trước khi gọi `_maybe_peek_comments`:
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
  * Verify bằng test suite: `pytest python_runner/tests/test_comment_peek_logic.py` và `pytest python_runner/tests/test_feed_swipe_smoke.py -k "test_maybe_peek_comments"`.

---

### 3. Cơ chế giải thích số liệu Feed Watchdog cho User
* **Lý do "Khác (X)" ở mục Đăng video:**
  * Watchdog cũ chỉ gom 2 lý do tường minh ("Đang dưỡng sinh" và "Chưa render/thiếu video").
  * Mọi lý do khác (đã trigger trong ca `already_uploaded_in_shift`, chưa đủ 10 ngày tuổi `account_creation_date_unverifiable`, đang ngâm cooldown `account_cooling_period`) đều bị dồn vào "Khác".
* **Lý do Thả tim Bạn bè (Friends likes > 0):**
  * Script nuôi acc chia tỷ lệ lướt: 70% For You, 15% Following, 15% Friends (Bạn bè).
  * Tab Bạn bè của TikTok tự động phân phối video từ danh bạ đồng bộ, gợi ý liên kết, hoặc video từ cụm tài khoản lân cận. Bot lướt qua tab này và thả tim tự nhiên theo xác suất cấu hình, không phải tài khoản đã kết bạn thủ công.
