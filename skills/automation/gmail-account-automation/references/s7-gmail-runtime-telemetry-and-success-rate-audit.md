# S7 Gmail Registration: Runtime Telemetry, Log Paths & Success Rate Audit

**Cập nhật:** 2026-10-12  
**Mục đích:** Quy định vị trí lưu trữ artifact thực tế của runner S7, baseline tỉ lệ thành công chuẩn, và phương pháp trích xuất thống kê O(1) chống quét đĩa diện rộng.

---

## 1. Canonical Log Directory & Artifact Structure
- **Vị trí lưu trữ logs thực tế:**
  Khi watchdog `post_noon_chain_watchdog.py` hoặc runner `run_all.ps1` / `run_parallel.ps1` thực thi, thư mục logs **KHÔNG** nằm tại `D:/Taadaa/register gmail`, mà được ghi tại:
  `D:/CodexRuntime/codex_gmail_debug-register-gmail/logs_parallel_<YYYYMMDD_HHMMSS>/`
- **Cấu trúc bên trong mỗi đợt chạy (`logs_parallel_*`):**
  - `summary.json` (Encoded `utf-8-sig` do PowerShell sinh UTF-8 BOM): Chứa metric tổng hợp toàn đợt:
    ```json
    {
      "total": 15,
      "success": 5,
      "failed": 10,
      "skip_safe": 0,
      "failure_breakdown": {
        "platform_errors": {
          "phone_verify": 6,
          "account_creation_error": 0
        },
        "script_errors": {
          "failed_cleanup": 0,
          "failed_other": 4
        }
      }
    }
    ```
  - `results/machine_<N>.success.json`: Chứa email và thông tin tài khoản vừa reg thành công của máy `<N>`.
  - `machine_<N>.log`: File log chi tiết từng bước của máy `<N>`.

---

## 2. Baseline Hiệu Suất & Phân Phối Thất Bại (S7 Non-SIM Proxy 4G)
Dữ liệu kiểm chứng thực tế toàn farm S7 (Tháng 10/2026):
- **Tỉ lệ thành công chuẩn (Normal Success Rate):** **~40.0%** (dao động 33.3% – 53.3% tùy chất lượng dải IP 4G của nhà mạng).
- **Phân bổ nguyên nhân thất bại (Failures Breakdown):**
  1. **Lỗi Nền Tảng Google (Chiếm ~61.6% tổng lỗi / ~37% tổng số máy):**
     - `phone_verify` (~28% tổng máy): Google bắt nhập SĐT xác minh OTP do nhận diện IP/Proxy hoặc Fingerprint thiết bị. Đây là cơ chế bảo vệ tự nhiên của Google khi tạo tài khoản không SIM.
     - `account_creation_error` (~9% tổng máy): Google từ chối tạo ở bước submit cuối cùng.
  2. **Lỗi Kỹ Thuật / Script / Ngoại Cảnh (`failed_other` - Chiếm ~38.4% tổng lỗi / ~17% tổng máy):**
     - `[PREFLIGHT_PROXY] device is offline or ADB/USB disconnected`: Cáp USB lỏng hoặc mất ADB transport trước khi kiểm tra proxy.
     - `[04_google] Không chọn được provider Google`: Kẹt khi load giao diện Accounts / Sync Settings trên Android.

---

## 3. Quy Tắc Trích Xuất Thống Kê O(1) (Chống Quét Đĩa)
- Khi User yêu cầu kiểm tra tỉ lệ reg Gmail gần đây:
  - **CẤM** dùng `search_files` hay quét đĩa toàn bộ ổ `D:/Taadaa` hay `D:/`.
  - **TRUY XUẤT THẲNG O(1):** Đọc danh sách thư mục `logs_parallel_*` trong `D:/CodexRuntime/codex_gmail_debug-register-gmail/`, đọc trực tiếp `summary.json` bằng Python (`encoding='utf-8-sig'`) để tổng hợp số liệu theo ngày/đợt.
