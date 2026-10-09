# Quy trình Preflight Shutdown trước khi Backup GPM Profiles

## 1. Vấn đề File Lock khi Sao lưu Profile GPM
Khi chạy backup định kỳ (cronjob `weekly-gpm-profiles-backup` hoặc script nén dữ liệu profiles `backup_gpm_profiles.py`):
- Nếu có profile GPM đang chạy (đang nuôi Gmail, lấy OAuth, ngâm session):
  - File `Default/Network/Cookies` (SQLite) và các file log LevelDB sẽ bị tiến trình `chrome.exe` lock độc quyền.
  - Quá trình đọc/nén file gặp lỗi `[Errno 13] Permission denied`.
- Dẫn đến bản backup bị khuyết thiếu cookie/session của các profile đang active.

## 2. Kỷ luật Pre-Backup: Tự động đóng toàn bộ Profile đang chạy
Trước khi tiến hành sao lưu (bất kể backup SQLite database hay nén thư mục session/cookies), script backup **BẮT BUỘC** thực hiện bước Preflight Shutdown:
1. **Lấy danh sách profile active:**
   - Gọi GPM Local API: `GET http://127.0.0.1:19995/api/v3/profiles/active`
2. **Đóng mềm (Graceful Stop):**
   - Lặp qua các profile đang mở và gọi: `GET http://127.0.0.1:19995/api/v3/profiles/stop/{profile_id}`
3. **Quét tiến trình Chromium mồ côi (Force Kill Fallback):**
   - Quét qua `psutil.process_iter()` lọc các tiến trình `chrome.exe` có cmdline chứa `gpmlogin/profile`.
   - **LƯU Ý AN TOÀN:** Tuyệt đối bỏ qua nếu cmdline chứa `google/chrome/user data` (Chrome cá nhân của User) hoặc thuộc về ADB, Hermes, Python.
   - Terminate/kill các tiến trình Chrome thuộc GPM còn sót lại.
4. **Độ trễ giải phóng file handle:**
   - Sleep 2-3 giây sau khi đóng toàn bộ để hệ điều hành Windows giải phóng hoàn toàn file lock độc quyền trên SQLite và LevelDB.
5. **Tiến hành Backup:**
   - Sau khi đảm bảo 0 profile GPM nào đang chạy, mới bắt đầu snapshot SQLite và nén session ZIP.
