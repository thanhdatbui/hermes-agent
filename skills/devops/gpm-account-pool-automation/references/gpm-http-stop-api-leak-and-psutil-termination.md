# GPMLogin HTTP Stop API Leak & OS Process Termination Invariant

## 1. Bản chất sự cố (Root Cause)
Khi điều khiển GPMLogin v3 qua Local API (`http://127.0.0.1:19995`):
* Endpoint `GET /api/v3/profiles/stop/{id}` chỉ gửi tín hiệu ngắt logic tới GPM daemon, **hoàn toàn KHÔNG đảm bảo kill tiến trình Chromium (`chrome.exe`) trên Windows**.
* Nếu script automation (audit, nurture, login) chỉ gọi `_stop_gpm_profile` qua HTTP request mà không có tầng OS process cleanup:
  - Cửa sổ Chromium tiếp tục sống và ghim trên Windows Taskbar.
  - Vòng lặp duyệt danh sách tài khoản (ví dụ `--all` 70 mail) sẽ mở dồn dập hàng chục cửa sổ browser, đè nghẹt Taskbar, ngốn CPU/RAM và làm treo các ứng dụng foreground của người dùng (như CapCut, render tool).

## 2. Tiêu chuẩn dập tắt Profile (Process Termination Invariant)
Mọi hàm `_stop_gpm_profile(profile_id, host_port=None)` bắt buộc phải thực thi 2 tầng dập tắt:
1. **Tầng 1 (GPM API):** Gửi HTTP GET tới `/api/v3/profiles/stop/{profile_id}` để đồng bộ state nội bộ của GPM.
2. **Tầng 2 (OS Process Termination qua `psutil`):**
   - Trích xuất port debug từ `host_port` (ví dụ `127.0.0.1:59828` -> `59828`).
   - Quét tiến trình hệ thống qua `psutil.process_iter(['name', 'cmdline'])`.
   - **BẢO VỆ TUYỆT ĐỐI CHROME CÁ NHÂN:** Bỏ qua ngay lập tức nếu `cmdline` chứa `google\chrome\user data` hoặc `google/chrome/user data`.
   - Khớp đúng tiến trình Chromium của GPM: có `--remote-debugging-port={port}` HOẶC `--user-data-dir` trỏ vào `gpmlogin/profile`.
   - Dọn sạch toàn bộ tiến trình con (`p.children(recursive=True)`), gọi `p.terminate()`, chờ tối đa 1.0s, nếu không thoát thì force-kill (`p.kill()`).
   - Bọc trong `try/except (psutil.NoSuchProcess, psutil.AccessDenied)` để an toàn tuyệt đối.

## 3. Kỷ luật cấu hình Cronjob / Batch Audit
* **CẤM TUYỆT ĐỐI chạy càn `--all` không giới hạn trong cron tự động:** Mọi cronjob định kỳ (như `chatgpt-account-lifecycle-healer`) BẮT BUỘC phải đặt giới hạn trần cuốn chiếu (ví dụ `--limit 5`) để tránh spam tải đột ngột.
* **Pre-flight Concurrency Check:** Trước khi mở profile mới, kiểm tra số lượng Chromium GPM đang mở (`active_gpm_count`). Nếu $\ge$ trần quy định (ví dụ trần 1 cho audit, trần 5 cho supervisor) thì phải dọn dẹp hoặc skip tick, không bao giờ để profile mở lũy kế.
