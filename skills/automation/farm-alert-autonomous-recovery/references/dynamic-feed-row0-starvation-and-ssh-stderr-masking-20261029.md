# Dynamic Feed Row-0 Starvation False Alert & SSH Warning Masking Triage (29/10/2026)

## 1. Dynamic Feed (`row-0`) vs Static Row Starvation False Alert
- **Hiện tượng:** Bản tin Cronjob Watchdog (`feed_session_watchdog.py`) báo động đỏ:
  `🌾 Sức khỏe 8 Row (Chu kỳ 4 ngày): R1:🔴... | R8:🔴...`
  `🚨 CẢNH BÁO BỎ ĐÓI: Row 1, Row 2, Row 3, Row 4, Row 5, Row 6, Row 7, Row 8 > 108h chưa nuôi thành công!`
- **Bản chất kỹ thuật (Root Cause):**
  - Farm đã chuyển sang cơ chế **Dynamic Feed** (`USE_DYNAMIC_FEED=1` trong `tiktok_runner.py`), kết hợp dynamic pool theo 3 ca:
    * Ca 1: Pool {1, 2, 7}
    * Ca 2: Pool {3, 4, 8}
    * Ca 3: Pool {5, 6} + Dưỡng sinh
  - Toàn bộ thư mục runtime sinh ra có tiền tố `row-0-HHMMSS` (ví dụ `row-0-200013`).
  - Hàm thẩm định nuôi `get_row_nurture_summary()` trong `scripts/watchdog/alerts.py` sử dụng regex cứng:
    `re.match(r"^row-(\d+)-(\d{2})(\d{2})", r_dir.name)` và chỉ cập nhật nếu `1 <= r <= 8`.
  - Kết quả: Toàn bộ các phiên chạy `row-0` bị bỏ qua 100%, đồng hồ tính giờ nuôi của 8 Row bị kẹt ở các phiên chạy tĩnh từ tuần trước (> 108h), gây ra **báo động giả (false positive)**.
- **Kỷ luật Triage O(1):**
  - Khi thấy cảnh báo bỏ đói cả 8 Row cùng lúc, BẮT BUỘC kiểm tra `D:/Taadaa/runtime/<cluster>/cron-state/runner_simple_state.json` và thư mục `D:/Taadaa/runtime/<cluster>/live/<date>/` trước khi phán đoán farm tê liệt.

---

## 2. OpenSSH Stderr Warning Masking Root Cause (Admin Remote Cluster)
- **Hiện tượng:** `upload_result.json` hoặc báo cáo watchdog ghi nhận lỗi:
  `reason: "** The server may need to be upgraded. See https://openssh.com/pq.html"`
- **Bản chất kỹ thuật:**
  - Client SSH trên máy Kibe kết nối sang `admin-farm` (192.168.110.119) in cảnh báo Post-Quantum Key Exchange ra `stderr`:
    `** WARNING: connection is not using a post-quantum key exchange algorithm.`
    `** The server may need to be upgraded. See https://openssh.com/pq.html`
  - Tầng wrapper bắt lấy dòng cuối của `stderr` làm `reason` thay vì đọc `report.json` của worker, làm che khuất (mask) lỗi nghiệp vụ thực tế.
- **Kỷ luật Triage:**
  - Tuyệt đối không dừng lại ở chuỗi `openssh.com/pq.html`.
  - BẮT BUỘC đọc file kết quả thực tế trên host Admin:
    `ssh admin-farm "type D:\CodexRuntime\tiktok-video\runs\<run_id>\report.json"`
  - Các mã lỗi thực tế thường gặp bên dưới:
    * `[POST_RECHECK_UNAVAILABLE]`: Video đã submit nhưng TikTok CDN chưa cập nhật grid profile trong 120s -> Guard an toàn chặn repost.
    * `[DUPLICATE_MEDIA_BLOCKED]`: Media fingerprint SHA-256 đã tồn tại -> Chặn upload trùng.
    * `[VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED]`: Nút tạo (+) không bung được media picker.

---

## 3. Lỗi Khuyết Video Tuần Tự (`video_not_rendered` / "Hết video/Cần cào")
- **Hiện tượng:** Watchdog báo `Hết video/Cần cào: 40`, trong khi thư mục `D:\TIKTOK-videonuoinick\<folder>` vẫn có hàng chục video rendered (ví dụ 46 video).
- **Bản chất:**
  - Tài khoản trong `TikN.xlsx` đang ở tiến độ video thứ $K$ (ví dụ video 10), video cần đăng tiếp theo là $K+1$ (ví dụ `11.mp4`).
  - Trong thư mục chứa video bị nhảy cóc (có `1..10.mp4`, khuyết `11.mp4`, rồi đến `12, 13...mp4`).
  - Runner kiểm tra sự tồn tại tuần tự của đúng file `(K+1).mp4`. Nếu file không tồn tại, runner sẽ skip với mã `video_not_rendered`.
- **Xử lý nhanh:**
  - Kiểm tra `ls D:/TIKTOK-videonuoinick/<folder>/`.
  - Cập nhật số tiến độ trong workbook lên để khớp với video kế tiếp hoặc bù file bị khuyết số.
