# Quy Định Quản Lý Mã Nguồn Repo GPM Auto & Đồng Bộ GitHub

## 1. Phân Định Ranh Giới Repo (Repository Boundary & SSOT)
- **Quy tắc cốt lõi:** Bất kỳ công cụ, script hay quy trình tự động hóa nào tương tác trực tiếp với **GPMLogin** (gọi Local API port 19995, khởi chạy Chrome Profile Core 142, đăng nhập Google/Gmail/Hotmail, thiết lập 2FA Authenticator TOTP, hoặc tự động hóa cấp quyền OAuth Developer/Antigravity trên profile GPM) **BẮT BUỘC LƯU TRỮ VÀ QUẢN LÝ TẬP TRUNG TẠI REPO `D:\Taadaa\GPM auto`**.
- **Cấm vi phạm:** CẤM TUYỆT ĐỐI lưu trữ các script điều khiển profile GPM sang repo `AI-Tools` hoặc các repo khác.
  - `AI-Tools` (`D:\Taadaa\AI-Tools`): Chỉ quản lý core proxy LLM (OmniRoute port 20129, 9Router port 20128), model routing, API adapters, và các script watchdog hạ tầng.
  - `GPM auto` (`D:\Taadaa\GPM auto`): Là Single Source of Truth (SSOT) cho toàn bộ mã nguồn tự động hóa profile trình duyệt GPM, kịch bản bypass Google Prompt/2FA trên farm, và script nạp tài khoản.

---

## 2. Cấu Hình Remote GitHub & Quy Trình Đồng Bộ
- **Remote Repository:** `https://github.com/thanhdatbui/gpm-auto.git` (Private repository).
- **Default Branch:** `main`.
- **Lệnh kiểm tra kết nối:**
  ```bash
  git -C "D:/Taadaa/GPM auto" remote -v
  # origin  https://github.com/thanhdatbui/gpm-auto.git (fetch)
  # origin  https://github.com/thanhdatbui/gpm-auto.git (push)
  ```

---

## 3. Quy Tắc .gitignore & Bảo Vệ Dữ Liệu Nhạy Cảm (Credential Guard)
Khi làm việc trên repo `GPM auto`, các script thường xuyên đọc hoặc test với tài khoản thật. Để ngăn chặn rò rỉ mật khẩu và tài liệu nội bộ lên GitHub, file `.gitignore` BẮT BUỘC phải duy trì các quy tắc sau:

1. **Chặn tài liệu và file danh sách:**
   ```gitignore
   *.xlsx
   *.xls
   *.csv
   accounts.txt
   proxies.txt
   tokens.json
   credentials.json
   config/*.txt
   config/*.json
   ```
2. **Chặn các script nháp chứa mật khẩu hardcode:**
   - Các file script probe/test tạm sinh ra trong ca trực thường chứa password (`@Ks`):
   ```gitignore
   scripts/fast_finish_*.py
   scripts/finalize_*.py
   scripts/survey_*.py
   scripts/test_*.py
   ```
3. **Chặn dữ liệu runtime, log và ảnh chụp hiện trường:**
   ```gitignore
   logs/
   session_cache/
   debug_screenshots/
   *.png
   *.log
   http.port
   profiles_data/
   checkmail_browser_data/
   checkmail_proxy_data/
   checkmail_results/
   profiles_worker/
   ```

---

## 4. Chuẩn Hóa Script OAuth Pipeline Trong GPM Auto
Hai script cốt lõi phục vụ nạp tài khoản và bypass Google Prompt đã được chuẩn hóa tại thư mục `scripts/`:
- `scripts/run_oauth_s7_pipeline.py`:
  - Khởi chạy profile GPM qua Playwright kết nối proxy Singbox tương ứng.
  - Tự động vượt qua Google Prompt 2 giai đoạn trên Samsung Galaxy S7 (WAKEUP `224` + UNLOCK `82` + nhận diện PIN target và tap đúng số).
  - Tự động lấy Offline Security Code 10 số từ S7 Settings khi gặp `challenge/ootp`.
  - Nhận diện cơ chế bảo vệ Google Sensitive Action Gate (7-Day Cooldown `rrk=77`) để fail-fast, không ngâm timeout 180s.
  - Đảm bảo khối `try ... finally:` bên trong `acquire_device_lock` luôn gửi phím HOME (`keyevent 3`) đưa máy về màn hình chính trước khi nhả lock.
- `scripts/add_oauth_omniroute.py`:
  - Lấy authorization URL từ OmniRoute (`http://127.0.0.1:20129`).
  - Sau khi bắt code exchange thành công, tự động tra cứu Proxy ID theo port trong OmniRoute và gọi:
    * `PUT /api/settings/proxies/assignments` (`scope: account`, `scopeId: cid`, `proxyId: px_id`)
    * `POST /api/providers/{cid}/sync-models`
