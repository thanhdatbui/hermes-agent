# Device Lock Reaping & Foreign App Focus Conflict Guard (2026-08-20)

## 1. Bối Cảnh Sự Cố & Chuỗi Tranh Chấp (Root Cause Analysis)
Khi chạy các script tác vụ theo lô / on-demand (như Hotmail login `scripts/hotmail_list_runner.py`, Register Gmail, Add mail khôi phục...):
1. **Gỡ Lock Nhầm Do Dead-Owner Watchdog (`reap-dead-owner-locks`)**:
   - Operator hoặc script tạo file lock `machine_<N>.lock.json` với `status: running` / `user_authorized: True`.
   - Cron watchdog `reap-dead-owner-locks.py` (chạy mỗi 30 phút) kiểm tra PID gắn với lock file. Khi tiến trình con kết thúc hoặc PID thay đổi / worker kết thúc nhưng operator muốn giữ lock máy, watchdog thấy PID dead và tự động chuyển lock file vào thư mục cách ly `~/.codex/device-locks-reaped/<timestamp>`.
2. **Cron Nuôi Acc Chiếm Quyền Chạy**:
   - Runner nuôi acc (`multi-machine-feed-session`) quét `~/.codex/device-locks/`. Do file lock đã bị dọn đi, runner coi máy là rảnh và kích hoạt phiên nuôi acc (Row 2/4/6).
3. **Mất Focus TikTok Do App Khác Đang Hoạt Động**:
   - Máy đang mở ứng dụng khác (`com.microsoft.office.outlook` - màn hình *"Chọn loại tài khoản"*, `com.google.android.gm`, `com.sec.android.app.sbrowser`...).
   - Runner nuôi acc kiểm tra `focused_package` thấy không phải TikTok (`com.ss.android.ugc.trill`) $\rightarrow$ Kích hoạt `preserve_blocker_screen` và bắn alert: `🚨 [MÁY XX] DỪNG PHIÊN - Lý do: TikTok focus lost`.
4. **AI Auto-Recovery Can Thiệp Sai Mục Tiêu**:
   - Bot AI Auto-Recovery trong nhóm Farm Alerts nhận alert `TikTok focus lost` và tự động kích hoạt flow recovery (định force-stop hoặc mở đè TikTok), dẫn đến tranh chấp và phá vỡ hiện trường đăng nhập Hotmail/Gmail.

---

## 2. Quy Tắc Phòng Chống Tranh Chấp & Guard Ngoại Vi

### A. Guard AI Auto-Recovery Không Can Thiệp Khi App Ngoại Vi Đang Mở
- **Danh sách Whitelist Foreign Business Apps**:
  - `com.microsoft.office.outlook` (Outlook App)
  - `com.google.android.gm` (Gmail App)
  - `com.sec.android.app.sbrowser` / `com.android.chrome` (Trình duyệt Web đăng nhập mail/shop)
  - `com.google.android.gms` (Google Play Services / Setup Wizard)
- **Quy tắc**: Khi nhận alert `TikTok focus lost`, AI Auto-Recovery **BẮT BUỘC kiểm tra package và UI hiện tại**:
  - Nếu thuộc danh sách Foreign Business Apps $\rightarrow$ **CẤM Auto-Recovery tự ý can thiệp, CẤM force-stop, CẤM mở đè TikTok**.
  - Giữ nguyên hiện trường và ghi nhận trạng thái: `Tác vụ ngoại vi (Mail/Browser) đang hoạt động`.

### B. Bảo Vệ Device Lock Trong Quá Trình Chạy Script Batch
- Khi chạy script batch (Hotmail / Gmail / Reg), nếu lock được tạo cho dải máy, lock file phải luôn được duy trì với `user_authorized=True` hoặc tiến trình giám sát chính phải duy trì PID sống để tránh bị `reap-dead-owner-locks` dọn nhầm.
- Khi kiểm tra máy rảnh chạy batch: Phải luôn đối soát lịch ca nuôi acc (`farm-schedule-preflight-check`) và chỉ chạy trong khung giờ rảnh an toàn (cách ca nuôi >= 60 phút).
