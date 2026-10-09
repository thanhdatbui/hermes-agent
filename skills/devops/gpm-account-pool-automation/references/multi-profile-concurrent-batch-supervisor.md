# Multi-Profile Concurrent Batch Supervisor Architecture: GPM + Hotmail + ChatGPT + Codex

## 1. Context & Use Case
Khi điều phối một nhóm cố định các profile GPM (ví dụ: batch 5 tài khoản Hotmail M02, M04, M08, M09, M10), hệ thống cần đảm bảo:
- **Xử lý đồng thời ở tầng Batch (Batch-level Concurrency)**: Chạy song song N workers (`ThreadPoolExecutor(max_workers=5)`), mỗi worker phụ trách 1 profile/máy độc lập.
- **Xử lý tuần tự nghiêm ngặt ở tầng Profile (Per-Profile Sequential Stages)**: Một profile không được nhảy cóc giai đoạn và phải chờ đủ điều kiện / cooldown trước khi sang bước tiếp theo:
  1. `STAGE_1_HOTMAIL_LOGIN`: Login tài khoản Hotmail lên browser profile GPM (qua Playwright CDP hoặc API).
  2. `STAGE_2_CHATGPT_DIRECT_REG`: Đăng ký ChatGPT trực tiếp bằng email + password + OTP qua Microsoft Graph API (TUYỆT ĐỐI KHÔNG Google SSO/Microsoft SSO).
  3. `STAGE_3_SOAK_24_48H`: Chờ ngâm tài khoản 24 - 48 giờ sau khi tạo tài khoản ChatGPT.
  4. `STAGE_4_CODEX_OAUTH`: Chạy OAuth flow Codex / OmniRoute port 20129 + xác thực SĐT OTP (5sim/SumiStore).
  5. `STAGE_5_SOAK_7D`: Chờ đủ tuổi ngâm >= 7 ngày.
  6. `STAGE_6_HOTMAIL_SECURITY`: Đổi mật khẩu Hotmail mới, gỡ mail khôi phục không tin cậy và "Sign out everywhere".
  7. `STAGE_7_RELOGIN`: Đăng nhập lại profile GPM bằng mật khẩu Hotmail mới.

## 2. Batch-Level Guard vs Per-Account Locks
- **Anti-Pattern**: Tạo file lock riêng lẻ cho từng tài khoản hoặc scan DB liên tục trong cron loop gây race condition và khó thu hồi lock khi worker crash.
- **Best Practice (Single Batch Guard)**:
  - Dùng **một** OS file lock duy nhất cho toàn bộ batch supervisor tiến trình: `batch_gpm_hotmail_supervisor.lock`.
  - Trên Windows, dùng `msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)`.
  - Nếu không acquire được lock, log ngắn gọn và thoát 0 ngay (`silent watchdog pattern`), tránh chồng chéo các lần chạy cron cách nhau 5 - 30 phút.

## 3. State Machine & Persisted Artifacts
- **State Storage**:
  - Lưu vào `D:/Taadaa/runtime/kibe/cron-state/batch_gpm_5profiles_supervisor_state.json`.
  - Dùng atomic file write (ghi vào file `.tmp` rồi `os.replace` sang file chính) để tránh file hỏng khi mất điện/kill process.
  - Mỗi profile lưu rõ:
    ```json
    {
      "email": "vjorandrea1961@hotmail.com",
      "machine": 2,
      "profile_id": "62e1e029-31fe-449a-8044-f9f7ab3baa9e",
      "current_stage": "STAGE_2_CHATGPT_DIRECT_REG",
      "completed_stages": ["STAGE_1_HOTMAIL_LOGIN"],
      "stage_timestamps": {
        "STAGE_1_HOTMAIL_LOGIN": "2026-09-27T07:10:00Z"
      },
      "last_status": "BLOCKED_DEPENDENCY",
      "retry_count": 0
    }
    ```
- **Artifacts Isolation**:
  - Logs per profile: `D:/Taadaa/runtime/artifacts/gpm_supervisor/m{mid}_{email}.log`.
  - Debug screenshots: `D:/Taadaa/runtime/artifacts/gpm_supervisor/screenshots/`.

## 4. Upstream Dependency Pitfall: Trailing Space in Authoritative Workbook
- **Sự cố thực tế**:
  Trong `chatgpt_gpm_direct_reg.py`, đường dẫn file cập nhật được khai báo là:
  `UPDATED_XLSX = Path(r"D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated.xlsx")`.
  Tuy nhiên trên Windows disk, file thật sự có dấu cách ở đuôi trước đuôi mở rộng:
  `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx`.
- **Hậu quả**:
  `UPDATED_XLSX.exists()` trả về `False`, khiến hàm lấy mật khẩu `PASS CHATGPT` (Cột L / 11) trả về `None`. Bộ lọc `get_gpm_candidates(provider="hotmail")` bỏ qua toàn bộ 5 tài khoản Hotmail với log warning: `[<email>] Thiếu PASS CHATGPT; bỏ qua Hotmail candidate.`
- **Quy tắc xử lý**:
  Luôn fallback qua danh sách các đường dẫn biến thể dấu cách:
  ```python
  CANDIDATE_PATHS = [
      Path(r"D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx"),
      Path(r"D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated.xlsx"),
  ]
  UPDATED_XLSX = next((p for p in CANDIDATE_PATHS if p.exists()), CANDIDATE_PATHS[0])
  ```
  Nếu dependency upstream chưa hoàn thiện hoặc bị blocker, supervisor phải gắn cờ `BLOCKED_DEPENDENCY` và dừng bước đó cho profile, không được tiếp tục sang các bước yêu cầu tài khoản đã reg xong.
