# Device Lock & 3-Tier Architecture Rules

## 1. Vấn đề cốt lõi (Root Cause)
Worker subagent là đơn vị thực thi ngắn hạn (<2 phút, giới hạn 600s). Nếu để Worker tự ý chờ đợi máy bận (rolling-wait 15-30 phút khi máy đang chạy ca nuôi TikTok) -> Worker sẽ bị TimeoutError chết cháy và đốt token vô nghĩa.

## 2. Kiến trúc 3 tầng (3-Tier Decoupling)
- **Tầng 1 - Preflight Probe O(1) (Coordinator):**
  Coordinator trước khi dispatch worker BẮT BUỘC probe lock trước bằng `TaskQueue.check_preflight_free(machine, serial)`.
  * Nếu máy RẢNH: Dispatch worker thực thi ngay (<2 phút).
  * Nếu máy ĐANG BẬN CRON: TUYỆT ĐỐI CẤM dispatch worker. Đưa task vào `TaskQueue.enqueue()` và báo cáo user máy đang bận, sẽ canh chạy cuốn chiếu.
- **Tầng 2 - Persistent Task Queue:**
  Lưu trữ trạng thái task cần chạy vào `C:/Users/Kibe/.codex/device-locks/operator_task_queue.json`.
- **Tầng 3 - Watchdog ngoài band:**
  Tiến trình script nền poll định kỳ ngoài band (không tốn token LLM, không timeout). Khi máy vừa nhả lock -> Kích hoạt thực thi task ngay.

## 3. SafeAdb & AdbGuard Enforcement (Tầng Code)
- Không tin tưởng vào Prompt/Memory của AI. Khóa cứng ở tầng code:
- Mọi thao tác ADB qua class `SafeAdb` (`automation_core.safe_adb`):
  * Hardcode `force_preempt=False`. TUYỆT ĐỐI CẤM cướp máy làm hỏng cronjob đang chạy.
  * Chỉ thực thi lệnh ADB khi đã giữ lock hợp lệ (`self._lock_held = True`).
- `adb_guard.install_adb_guard()`:
  * Monkey-patch `subprocess.run`, ném `LockNotHeldError` chặn đứng mọi câu lệnh `adb -s <serial>` nếu chưa được bọc trong lock của serial đó.

## 4. Quy trình chuẩn Bật 2FA Gmail Farm
- **Trên Samsung S7:** Google luôn chặn truy cập Security Settings bằng WebView reCAPTCHA không thể giải tự động qua ADB. CẤM cố bật 2FA trực tiếp trên S7.
- **Quy trình chuẩn:**
  1. Đưa Gmail lên GPM Profile (gắn đúng Proxy 4G của máy S7 đó).
  2. Đăng nhập Google trên GPM. Nếu gặp màn hình thêm email/sdt khôi phục -> bấm Hủy/Để sau. Nếu gặp prompt -> S7 bấm xác nhận hoặc lấy mã 10 số.
  3. Vào `myaccount.google.com/two-step-verification/authenticator` trên GPM -> Bóc Base32 Secret Key -> Tính TOTP True UTC -> Kích hoạt 2FA.
  4. Lưu Secret Key vào `gmail_clean_v2.xlsx`.
