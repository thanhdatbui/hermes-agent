# Quy Chuẩn Tách Biệt Pipeline Cuốn Chiếu: 2FA Gmail Sau Ca Sáng & Reg Gmail + Add 2FA TikTok Sau Ca Trưa (2026-09-13)

## 1. Bối cảnh & Yêu cầu Người Vận Hành
- **Bỏ hẳn Reg TikTok** khỏi các chuỗi tự động định kỳ (chỉ chạy on-demand hoặc bổ sung thủ công).
- **Hủy bỏ toàn bộ các cron cố định giờ ban đêm / chiều**:
  - Hủy cron `night-chain-reg-pipeline` (`38ea60c09825`, giờ cũ 01:00 AM) để chống xung đột đè máy với Ca 4 (00:00 & 01:30).
  - Hủy cron `post-noon-aged-gmail-2fa-watchdog` (`c38cbf36a1e8`, giờ cũ 15:00).
- **Chuyển dịch sang mô hình 2 Watchdog Cuốn Chiếu (Event-driven Rolling Watchdogs)**:
  1. **Sau Ca Sáng (Ca 1)**: Chạy Bật 2FA Gmail ngâm $\ge 24\text{h}-48\text{h}$.
  2. **Sau Ca Trưa (Ca 2)**: Chạy chuỗi Reg Gmail $\longrightarrow$ Add 2FA TikTok.

---

## 2. Chi Tiết Kiến Trúc 2 Watchdog Cuốn Chiếu

### A. Watchdog 1: 2FA Gmail Sau Ca Sáng (`post_morning_gmail_2fa_watchdog.py`)
- **Lịch Cron:** `*/5 8,9,10,11 * * *` (Job ID: `0dcc4a0a35bb`).
- **Khung giờ hợp lệ:** `08:30 – 11:30` (HCM timezone).
- **Điều kiện kích hoạt (Event-driven & Idle Gate):**
  1. Ca 1 Phiên 2 đã hoàn tất: kiểm tra trong `feed_session_reported.json` có bản ghi `<today>_ca1_phien2` hoặc `<today>_ca1`.
  2. Idle Gate: Không có tiến trình nuôi feed nào chạy (`multi_machine_feed_session`, `run-feed-session.ps1`, `run_follow`), không có active device lock.
  3. Idempotency: Kiểm tra `D:\Taadaa\runtime\kibe\cron-state\post_morning_gmail_2fa_state.json` chưa chạy trong ngày hôm nay (`last_success_date != today`).
- **Nghiệp vụ:** Quét kho `gmail_clean_v2.xlsx`, lấy candidate Gmail ngâm $\ge 24\text{h}-48\text{h}$ chưa bật 2FA, gọi tuần tự `enable_gmail_2fa_device.py`.
- **Định dạng báo cáo (stdout gửi Telegram):**
  ```text
  [BÁO CÁO 2FA GMAIL SAU CA SÁNG]
  - Thời gian: HH:MM -> HH:MM (X phút)
  - Tổng máy đủ điều kiện: N
  - Success (S): [danh sách máy]
  - Fail (F): [danh sách máy kèm lỗi]
  ```

### B. Watchdog 2: Chuỗi Reg Gmail -> Add 2FA TikTok Sau Ca Trưa (`post_noon_chain_watchdog.py`)
- **Lịch Cron:** `*/5 14,15,16,17 * * *` (Job ID: `7d32d8c1907e`).
- **Khung giờ hợp lệ:** `14:30 – 17:30` (HCM timezone) — khoảng đệm rảnh rỗi 3 tiếng trước Ca 3 (18:00).
- **Điều kiện kích hoạt (Event-driven & Idle Gate):**
  1. Ca 2 Phiên 2 đã hoàn tất: kiểm tra trong `feed_session_reported.json` có bản ghi `<today>_ca2_phien2` hoặc `<today>_ca2`.
  2. Idle Gate: Không có feed runner active, không có active device lock (`C:\Users\Kibe\AppData\Local\automation-core\device-locks` & `~/.codex/device-locks`).
  3. Idempotency: Kiểm tra `D:\Taadaa\runtime\kibe\cron-state\post_noon_chain_state.json` (`last_success_date != today`).
- **Nghiệp vụ tuần tự 2 Phase:**
  - **Phase 1:** Reg Gmail qua PowerShell `D:\Taadaa\register gmail\run_all.ps1`.
  - Nghỉ 15s nhả kết nối.
  - **Phase 2:** Add 2FA TikTok qua Python `D:\Taadaa\tiktok-add-bao-mat-f2a\python_runner\run_batch_live_2fa.py --all-online --workers 10`.
  - Tuyệt đối **BỎ HẲN Phase Reg TikTok**.
- **Định dạng báo cáo (stdout gửi Telegram):**
  ```text
  [BÁO CÁO CHUỖI SAU CA TRƯA] Reg Gmail -> Add 2FA TikTok
  - Thời gian: HH:MM -> HH:MM (X phút)

  - Phase 1 (Reg Gmail - Code N):
    + Tổng máy: X
    + Success (Y)
    + Fail (Z)

  - Phase 2 (Add 2FA TikTok - Code N):
    + Tổng máy: A
    + Success (B)
    + Fail (C)
  ```

---

## 3. Quy Chuẩn Đồng Bộ Sang Máy Admin & Multi-Host
1. Toàn bộ file kịch bản của cả 2 Watchdog BẮT BUỘC nằm đồng thời tại:
   - `C:\Users\Kibe\AppData\Local\hermes\scripts\` (Local máy Kibe)
   - `D:\Taadaa\Hermes\deploy\hermes-home\scripts\` (Kho deployment Git)
   - `D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\scripts\` (Thư mục OneDrive sync dùng chung cho Admin)
   - `D:\Taadaa\tools\` (Thư mục công cụ liên kết farm)
2. Trên máy Admin, cả 2 watchdog đều dùng `taadaa_host.load_host_config()` và biến môi trường `TAADAA_HOST_CONFIG` trỏ `admin.yaml`, đảm bảo đường dẫn workbook và runtime tự động phân giải về `D:\OneDrive\TaadaaData\admin` và `D:\Taadaa\runtime\admin`.
