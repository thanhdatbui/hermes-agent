# Upload Hook Timeout & Media Fingerprint Reconciliation

References & Diagnostic Notes (2026-08-25):

## 1. Hiện tượng & Nguyên nhân Timeout Upload Hook cuối Phiên 3
- Khi Phiên 3/3 kết thúc, `multi_machine_feed_session.py` tự động kích hoạt `_run_upload_hook` gọi subprocess `run_post.py` cho từng máy.
- Toàn bộ 40 máy trong run `row-1-221524` ghi nhận `status: timeout, reason: upload-timeout` trong `upload_result.json`.
- **Nguyên nhân cốt lõi:**
  1. Samsung S7 sau khi lướt feed 8–11 video bị đầy bộ nhớ, khi chuyển qua luồng upload (`OPEN_TIKTOK` -> `WAIT_FEED` -> `ACCOUNT_SWITCHER` -> `PROFILE_GRID` -> `MEDIA_PUSH` -> `VIDEO_PICK` -> `CAPTION_FILL` -> `POST` -> `VERIFY_POST`) tốn từ 4–6 phút/máy.
  2. Dưới tải 40 workers đồng thời, các tác vụ ADB screenshot/dump UI và push file MP4 (8–10MB) qua USB hub bị nghẽn I/O, khiến tổng thời gian vượt quá ngưỡng timeout của subprocess (900s) hoặc bị outer watchdog của feed session abort giữa chừng.

## 2. Giải Pháp Tách Biệt Timeout Độc Lập Cho Upload Hook (Commit `9db6c84`)
- **Tách độc lập `DEFAULT_UPLOAD_HOOK_TIMEOUT_SECONDS = 1200.0` (20 phút):**
  - Subprocess `run_post.py` không dùng timeout 900s cũ, không bị phụ thuộc vào deadline lướt feed.
- **Mở rộng Outer Watchdog (`worker_hard_timeout`):**
  - Khi ở phiên cuối (hoặc force upload), watchdog tự động tính budget tối thiểu an toàn:
    $$\text{worker\_hard\_timeout} = \max(\text{configured\_hard}, \text{feed\_timeout} + \text{upload\_extra\_budget (1200s)} + 300.0)$$
  - Chuẩn hóa kiểm tra `math.isfinite()` và `math.ceil()` cho toàn bộ giá trị timeout float chống crash hoặc ép về 0s.

## 3. Pitfall Media Fingerprint Ledger (`MEDIA_FINGERPRINT_PENDING`)
- Repo `Tiktok-video` sử dụng `MediaFingerprintLedger` tại `D:\CodexRuntime\tiktok-video\idempotency\media-fingerprints\<sha256>.json`.
- Khi worker bắt đầu bước `RESOLVE_NEXT_VIDEO`, file `<sha256>.json` được tạo với `status: reserved` và TTL mặc định 1800s (30 phút).
- **Hậu quả khi bị timeout/crash:**
  - Nếu worker upload bị timeout hoặc bị kill giữa chừng trước khi chạm tới `VERIFY_POST`, file ledger vẫn giữ trạng thái `reserved`.
  - Khi retry hoặc chạy lại ngay sau đó (< 30 phút), state machine sẽ chặn với lỗi:
    `[MEDIA_FINGERPRINT_PENDING] Exact media SHA-256 has unresolved ledger status=reserved` và chuyển trạng thái về `MANUAL_REVIEW`.
- **Cách xử lý:**
  - Xóa file reservation mồ côi tương ứng trong `D:\CodexRuntime\tiktok-video\idempotency\media-fingerprints\` hoặc chờ sau 30 phút để cơ chế `stale_after_seconds` tự động giải phóng.

## 4. Dynamic 2-Layer Upload Preflight (Commit `ee4406c`)
- Xóa bỏ hoàn toàn hardcode whitelist row (không giới hạn Row 1–2).
- **Lớp 1:** `resolve_tik_workbook` kiểm tra file `TikN.xlsx` và mapping máy tương ứng.
- **Lớp 2:** Kiểm tra file `D:\TIKTOK-videonuoinick\<folder_video>\<next_video>.mp4` sẵn sàng trên đĩa.
- Hỗ trợ tự động chạy upload cho tất cả các ca Tik1..TikN nếu thỏa mãn cả 2 lớp.

## 5. Benchmark Thời Gian & Cấu Hình Swipes Tối Ưu Cho Farm Samsung S7
- **Thời gian chạy trung bình của 1 máy (đo trên 299 mẫu thực tế 2026-08-25):**
  - Trung bình: **6 phút 12 giây** (`372.8s`).
  - 8 swipes: ~5 phút 56 giây (`356.1s`).
  - 9 swipes: ~6 phút 00 giây (`360.7s`).
  - 10 swipes: ~6 phút 26 giây (`386.5s`).
  - 11 swipes: ~6 phút 28 giây (`388.0s`).
- Khuyến nghị Swipes per Session:
  - Khóa cố định ở dải **8 – 11 swipes / phiên** (trần tối đa = 15).
  - Không tăng swipe vượt 15 để tránh Android LMK kill uiautomator ngầm gây lỗi tràn RAM (`ATX_SESSION_UNAVAILABLE`).
  - Lịch 3 phiên/ca × ~10 swipes = ~30 video/ngày là ngưỡng tối ưu cả về độ bền phần cứng S7 lẫn thuật toán trust tài khoản TikTok.

## 6. Xử lý Navigation Blocker (Camera Creation Overlay) & Safe Fallback Import (Commit `cdce610`)
- **Hiện tượng:** Khi điều hướng về Trang chủ (`tap_home` trước khi lướt feed), TikTok bất ngờ mở màn hình Camera / Media Creation Overlay (chứa các text `ĐĂNG`, `TẠO`, `Văn bản`, `Máy ảnh`...).
- **Cơ chế phục hồi:**
  - `_find_navigation_element` trong `calibrate_screens.py` không thấy nút Home sẽ gọi `find_matching_handler(xml_text)` trong `benign_popup_registry.py`.
  - Bộ nhận diện `camera_creation_overlay` phát hiện màn hình và tự động gửi phím `KEYCODE_BACK` để thoát về Trang chủ.
- **Pitfall Import Package:**
  - `from flows.benign_popup_registry import find_matching_handler` có thể văng `ModuleNotFoundError` khi package context không có top-level `flows`.
  - Fix chuẩn: Bọc `try/except ModuleNotFoundError as err` và chỉ fallback `from python_runner.flows.benign_popup_registry...` khi `err.name == 'flows'`.

