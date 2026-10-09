# Case Study & Pattern: Chống Báo Cáo Ma & Điều Phối Canh Máy Rảnh Tự Động (12/09/2026)

## 1. Sự Cố Zombie Summary Trong Pipeline Chuỗi Đêm (False Reports)
- **Bối cảnh:** Báo cáo chuỗi đêm `night-chain-reg-pipeline` báo hàng loạt máy thất bại với lỗi `proxy timeout` liên tiếp 4 đêm (từ 08/09 đến 12/09).
- **Phân tích hiện trường O(1):**
  - Curl trực tiếp proxy của từng máy: 100% các cổng đều live, trả IP trong < 1s.
  - Kiểm tra log chạy batch: Runner `run_all.ps1` thực tế đã crash ngay giây đầu tiên do `NameError: name 'PROJECT_ROOT' is not defined` trong `gmail_reg_v10.py` (khai báo biến ở dòng 58 nhưng được dùng ở dòng 37).
- **Nguyên nhân cốt lõi (Anti-Pattern):**
  - Hàm `parse_gmail_details` và `parse_tiktok_details` trong launcher `run_night_chain_pipeline.py` có fallback: khi runner crash và không in `Summary JSON:`, script tự động quét tìm thư mục `logs_parallel_*` mới nhất trong runtime directory.
  - Do batch bị crash từ ngày 08/09, thư mục "mới nhất" lại chính là thư mục từ đêm 08/09. Pipeline liên tục lấy file `summary.json` cũ này ra parse và báo cáo, tạo ra hiện tượng **báo cáo ma** (zombie summary).
- **Giải pháp chuẩn:**
  - Bổ sung kiểm tra `st_mtime`: Chỉ chấp nhận file summary được tạo trong vòng 3 giờ gần nhất (`time.time() - summary_path.stat().st_mtime <= 10800`). Nếu quá 3 giờ, trả về dict rỗng (không lấy log cũ).

---

## 2. Kỷ Luật Canh Máy Rảnh Tự Động (Chống Đoán Giờ Tĩnh)
- **Vấn đề khi dùng Mốc Giờ Tĩnh:**
  - Lịch nuôi acc buổi sáng kết thúc quanh `09:00 - 09:15`. Nếu coordinator tự động đặt cron hẹn giờ tĩnh (ví dụ `09:15:00`), rất dễ xảy ra xung đột nếu máy dump XML chậm, bị uiautomator freeze hoặc kẹt hook khiến lock bị giữ lâu hơn thời gian dự kiến.
  - Khi cron kích hoạt mà máy vẫn còn lock, tác vụ canary sẽ bị skip hoặc xung đột với tiến trình trước.
- **Mẫu Thiết Kế Watchdog Động (Adaptive Lock Watcher):**
  - Xây dựng một script watchdog nhẹ (`gmail_idle_canary_watchdog.py`) chạy chu kỳ 3 phút:
    1. Kiểm tra trực tiếp file lock vật lý tại `~/.codex/device-locks/machine_<M>.lock.json` và `serial_<S>.lock.json`. BẮT BUỘC máy phải đã hoàn toàn giải phóng lock.
    2. Đọc manifest ngày hiện tại (`runtime/kibe/cron-state/manifests/<DATE>/`): Tính khoảng cách thời gian đến slot nuôi kế tiếp phải $\ge 60$ phút.
    3. Thỏa mãn cả 2 điều kiện $\rightarrow$ Kích hoạt ngay lệnh on-demand / canary test live trên máy đó.
    4. Ghi nhận file trạng thái `completed: true` và tự hủy cron job để đảm bảo tính chất **Single-Run (One-Shot)**.
- **Kết quả kiểm chứng:**
  - Watchdog phát hiện Máy 39 vừa nhả lock lúc 08:51:43 (có khoảng nghỉ 188.3 phút), kích hoạt canary test live ngay lập tức.
  - Kết quả: Reg thành công 100% trong 714s, tạo tài khoản `laphuochuong99uoql@gmail.com` và nạp vào Android OS thành công.

---

## 3. Sự Cố Zombie Summary Trong Preflight Reg Bù `ensure_row_accounts.py` (Lẫn Lộn Báo Cáo Giữa Các Row - 24/09/2026)
- **Hiện tượng:** Cảnh báo Telegram `📋 [PREFLIGHT REG BÙ ROW 5]` báo 4 máy thất bại: `Máy 3, Máy 46, Máy 61, Máy 69`, dù thực tế Row 5 toàn farm đã đủ tài khoản. 4 máy thất bại này thực chất là kết quả từ đợt reg bù của **Row 8** diễn ra 1.5 giờ trước đó (`01:33:16`).
- **Nguyên nhân cốt lõi (Anti-Pattern):**
  - Hàm `apply_results()` trong `ensure_row_accounts.py` có chốt chặn lọc thời gian `batch_start_time`:
    ```python
    if batch_start_time is not None:
        min_ts = batch_start_time.timestamp() - 10
        dirs = [d for d in dirs if d.stat().st_mtime >= min_ts]
    ```
  - Nhưng hàm `send_telegram_summary(row, missing, rc)` lại **hoàn toàn thiếu tham số `batch_start_time`**, chỉ lấy thư mục mới nhất thô:
    ```python
    dirs = sorted(runs_dir.glob("20*"), key=lambda d: d.stat().st_mtime, reverse=True)
    if dirs:
        latest_run = dirs[0]
    ```
  - Khi đợt kiểm tra Row 5 chạy lúc 03:04 không có máy nào cần chạy reg bù (`len(missing) == 0` hoặc không spawn batch mới), `latest_run` bị rơi về thư mục run của Row 8 trước đó. `all_results.json` của Row 8 bị đọc lại và gộp vào báo cáo của Row 5, gây hoang mang và phán đoán sai lệch hiện trường.
- **Quy tắc Bất Biến (Anti-Zombie Gate):**
  1. `send_telegram_summary(row, missing, rc, batch_start_time)` BẮT BUỘC nhận `batch_start_time`.
  2. BẮT BUỘC lọc `dirs = [d for d in dirs if d.stat().st_mtime >= batch_start_time.timestamp() - 10]`.
  3. Nếu không có thư mục run nào phát sinh trong batch hiện tại hoặc `len(missing) == 0`: TUYỆT ĐỐI KHÔNG đọc `dirs[0]` cũ, không gửi báo cáo thất bại ma.

