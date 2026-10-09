# Live Token Verification vs Stale Health Labels Runbook

## 1. Cốt lõi: Live Probe First, Stale Labels Second
- **Bệnh học (Pathology):** Các nhãn `testStatus: "banned"`, `testStatus: "expired"`, `testStatus: "error"`, hoặc `isActive: false` trong OmniRoute SQLite / UI thường là di chứng (artifact) của các đợt lỗi nhất thời trong quá khứ (như proxy xoay dính IP bẩn, Cloudflare challenge tạm thời, hoặc worker timeout).
- **Hậu quả nghiêm trọng:** 
  - Agent đọc nhãn tĩnh rồi vội vã báo cáo User là "tài khoản bị ban" hoặc đề xuất gỡ bỏ tài khoản còn sống nguyên vẹn.
  - Watchdog thấy `isActive: false` vội vã mở GPM cố đăng nhập lại trong khi session token vẫn còn hạn sử dụng hợp lệ.
- **Quy tắc bất biến:**
  - **CẤM TUYỆT ĐỐI** kết luận tài khoản bị ban/hỏng chỉ dựa trên metadata tĩnh trong database.
  - **BẮT BUỘC** gọi live probe trực tiếp lên upstream endpoint trước mọi quyết định:
    ```bash
    POST /api/providers/{connection_id}/test
    # hoặc
    POST /api/providers/validate với apiKey hiện tại
    ```
  - Nếu live probe trả về `valid: true` (hoặc `diagnosis.type: "ok"`):
    1. Lập tức cập nhật DB: `is_active = 1`, `test_status = 'active'`, `last_error = NULL`, `backoff_level = 0`.
    2. Bỏ qua toàn bộ bước đăng nhập lại qua GPM.
    3. Đảm bảo connection đã được add vào combo pool (ví dụ: `chatgpt-web-pool`).

---

## 2. ChatGPT-Web Recovery & Session Guard
- **Guard Empty Token:** Nếu watchdog không trích xuất được cookie/token (trả về `None` hoặc chuỗi rỗng), **CẤM** gửi payload `{apiKey: null}` sang endpoint validate vì sẽ làm upstream văng ngoại lệ `HTTP 400 Bad Request`. Bắt buộc kiểm tra guard `EMPTY_SESSION_TOKEN` trước.
- **Dọn sạch Cookie & Reload URL:** Trong Playwright/CDP, sau khi gọi `context.clear_cookies()`, **BẮT BUỘC** gọi `page.goto("https://chatgpt.com/auth/login")` để trình duyệt xóa DOM cũ và tải lại form đăng nhập sạch. Không reload sẽ khiến form đăng nhập không hiển thị, dẫn tới việc không điền được thông tin.

---

## 3. Antigravity Farm Device Mapping & GPM Multi-System Prerequisites
- **Đa nguồn Workbook:** Dữ liệu tài khoản farm có thể luân chuyển giữa các workbook quản lý (`taikhoan_dat_v2_updated .xlsx` vs `master_gmail_manager.xlsx`).
- **Thứ tự tra cứu an toàn:**
  1. Kiểm tra ưu tiên file cập nhật: `taikhoan_dat_v2_updated .xlsx` (sheet `Tài Khoản`, Cột A: Máy, Cột F: GMAIL, Cột J: Device Serial, Port proxy: `20000 + mid`).
  2. Fallback sang `master_gmail_manager.xlsx` (sheet `Master_All` hoặc `Kibe_Farm_S7`).
- **3 Điều Kiện Tiên Quyết Để Cron Xử Lý Được OAuth:**
  1. *Mapping thiết bị hợp lệ:* Script nối được email $\leftrightarrow$ máy S7 (mid, serial, port) từ workbook `taikhoan_dat_v2_updated .xlsx`.
  2. *ĐÃ CÓ PROFILE GPM TRÊN PC:* Pipeline OAuth bắt buộc mở browser profile GPM trên PC. Nếu profile chưa được tạo trên GPMLogin (ví dụ `sync_gpm_lifecycle.py` chỉ đọc file cũ nên chưa tạo profile cho nick mới), cron **HOÀN TOÀN KHÔNG THỂ XỬ LÝ** dù điện thoại đang online. Khi tạo profile tự động từ `taikhoan_dat_v2_updated .xlsx`, fallback proxy chuẩn theo cú pháp: `test.taadaa.click:{20000 + mid}:mobi{mid}:TaadaaMobi#2026!`.
  3. *Bẫy omniroute_success trong status_exclusions:* Trong `sync_gpm_lifecycle.py`, tuyệt đối CẤM đưa `omniroute_success` vào `status_exclusions`. Nếu đưa vào, các nick đã từng nạp thành công trong quá khứ nhưng nay bị `expired` token sẽ bị chặn vĩnh viễn không thể tạo profile GPM, dẫn tới việc watchdog không thể mở browser để cấp lại token.
  4. *Máy farm rảnh an toàn:* Thiết bị Android không được đang chạy ca nuôi TikTok (`com.ss.android.ugc.trill`) hoặc chiếm dụng proxy 4G. Nếu máy đang bận, kết nối proxy qua điện thoại sẽ bị nghẽn/timeout 10060 làm fail OAuth.
  5. *Đồng bộ 2 chiều Deploy <-> Runtime:* Khi chỉnh sửa cron scripts trong Git deploy `D:/Taadaa/Hermes/deploy/hermes-home/scripts`, `cron_sync_watchdog.py` bắt buộc phải sao chép sang runtime `%LOCALAPPDATA%\hermes\scripts` (kiểm tra `f.stat().st_size != dst.stat().st_size` hoặc ép copy đè) để các cron job đang chạy trên scheduler nhận được mã nguồn mới nhất.
- **Phối hợp S7:** Khi Google yêu cầu xác minh bảo mật (Google Prompt hoặc mã OOTP 10 số):
  - Duyệt Prompt: Bắt target PIN trên web $\rightarrow$ Tap notification $\rightarrow$ Chọn số tương ứng trên S7 $\rightarrow$ Return True ngay.
  - Bốc mã 10 số: Điều hướng Google Play Services trên S7 $\rightarrow$ Trích xuất mã bảo mật $\rightarrow$ Điền vào ô input trên PC.
- **3-Way Sync Guard (Deploy -> Runtime):** Trong `cron_sync_watchdog.py`, chỉ kiểm tra `st_mtime` là không đủ vì sửa file nhanh có thể bị trùng timestamp. Bắt buộc kiểm tra thêm `f.stat().st_size != dst.stat().st_size` để các bản vá trong Deploy lập tức được đẩy sang Runtime `~/AppData/Local/hermes/scripts` và OneDrive.

---

## 4. Rào cản Worker Gate & Điều phối Canary
- **Phân định TASK_KIND rõ ràng:**
  - `TASK_KIND: INVESTIGATE` bị Gate ép cứng sang chế độ **READ-ONLY 100%** (cấm tạo file, cấm patch). Nếu dispatch điều tra mà yêu cầu Worker tạo script tạm sẽ bị chặn ngay (`WORKER GATE - READ-ONLY WORKER`).
  - `TASK_KIND: EDIT` bắt buộc đi kèm `Scope Lock: <path cụ thể>`.
- **Cấm vẽ việc tạo script tạm chạy ngoài Whitelist:**
  - Terminal của Worker và Coordinator bị chặn bởi `DEFAULT-DENY TERMINAL` (chỉ cho phép `inspect_machine.py`, `adb`, `git`, `pytest`).
  - Không dispatch Worker tạo file script Python tạm rồi gọi chạy qua terminal. Phải tích hợp kiểm chứng vào script chuẩn của hệ thống hoặc dùng lệnh allowlist chính thức.

---

## 5. Kỷ luật Báo cáo Điều phối (Coordinator Discipline)
- **Không dùng từ ngữ mập mờ, né tránh:** CẤM TUYỆT ĐỐI báo cáo "⚠️ CẦN LƯU Ý" một cách mơ hồ làm người dùng khó hiểu và bực mình ("còn này lưu ý gì đéo hiểu"). Phải nêu thẳng vào trọng tâm:
  1. Đã xong hay Chưa xong (Ví dụ: "CHƯA XỬ LÝ ĐƯỢC").
  2. Lý do cụ thể vì sao chưa xong (Ví dụ: chưa có profile GPM trên PC, hoặc máy farm đang bận chạy ca TikTok chiếm proxy).
  3. Cron nào trong hệ thống phụ trách xử lý (Ví dụ: `post_evening_gpm_login_watchdog.py` / `30ffbf1672e7`).
  4. Phương án giải quyết dứt điểm tiếp theo.
- **Tránh bẫy phán ban ẩu đả:** Khi thấy nhãn `testStatus: "banned"` cũ từ database, TUYỆT ĐỐI CẤM vội vàng báo User là tài khoản bị ban hoặc đề xuất gỡ bỏ. Phải gửi live test request trực tiếp lên upstream endpoint (`POST /api/providers/{id}/test`), nếu trả về `valid: true` thì tài khoản vẫn sống 100% và phải phục hồi ngay lập tức.
- **Bẫy Ảo Giác "Token Expired Hết" trên Dashboard Quota:**
  - Trang `/dashboard/quota` render TOÀN BỘ connection trong bảng `provider_connections` (bao gồm các account rác/cũ từ quá khứ), KHÔNG phân tách theo combo pool.
  - Khi thấy cụm card đỏ "Token expired", BẮT BUỘC query SQLite đối soát ID với combo pool (`select data from combos where name='ag-gemini-pool-3'`). Các account expired thường là standalone Free/Standard cũ, trong khi 100% account Pro trong pool vẫn active và còn nguyên quota.
- **Bệnh Học "Pool Còn Quota Mà Nhảy Vào Acc Lỗi" (Tier Spillover Cascade):**
  - Trong combo phân tầng (ví dụ `omni-worker` strategy `priority`), Tier 1 là Pro Pool (`ag-gemini-pool-3`), Tier 2 là Free Pool (`ag-gemini-free-pool`).
  - Khi worker nã payload nặng (100k-200k tokens), acc Pro đầy concurrency (2/2) quá `queueTimeoutMs` (ví dụ 1000ms), router lập tức failover trượt xuống Tier 2 (Free Pool).
  - Các acc Free KHÔNG gánh được model cao cấp (`gemini-3.8-flash-tiered`) -> Google ném 429/403 Upstream liên hoàn -> trượt tiếp xuống Tier 3 (Codex).
  - *Khắc phục:* Nâng `queueTimeoutMs` của Tier 1 lên 3000ms-5000ms để chờ acc Pro nhả concurrency, hoặc ngắt Free Pool ra khỏi chuỗi fallback của model không hỗ trợ Free tier.
- **Đối soát số liệu thực:** Trước và sau khi xử lý phải query live API của OmniRoute (`/api/providers`) để báo cáo số lượng connection active thực tế tăng/giảm chính xác. CẤM báo "đã xong" khi mới chỉ sửa code mà chưa kiểm chứng kết quả chạy thực tế.
