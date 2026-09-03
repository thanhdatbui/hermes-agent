# Operator Preempt Lock Policy & Targeted App Kill (2026-08-22)

## 1. Nguyên tắc Preempt (Chiếm quyền ưu tiên)
- Khi User/Operator ra lệnh chạy một tác vụ can thiệp (như nạp Hotmail, Reg TikTok, cài đặt, debug máy lẻ), script của tác vụ đó được phép **chiếm quyền lock cao nhất**, cướp lock từ tiến trình cron nền đang chạy (`multi-machine-feed-session`).

## 2. Quy chuẩn thực thi 3 bước
1. **Acquire Lock với `force_preempt=True`**:
   Sử dụng `DeviceLock(serial=serial, machine=m, project=..., force_preempt=True, user_authorized=True)`.
2. **Targeted Stop (Ngắt app nền trên đúng máy đích)**:
   Gửi lệnh ADB `am force-stop` đối với app nền (ví dụ `com.ss.android.ugc.trill`) với cờ `-s <serial>` để chỉ ngắt riêng luồng của máy đó, tránh va chạm UI. Tuyệt đối không ảnh hưởng các máy khác trong batch.
3. **Dọn dẹp & Về Home**:
   Sau khi hoàn tất (dù SUCCESS hay lỗi), script gửi `am force-stop` app vừa dùng (ví dụ Outlook) và `input keyevent 3` (Home) trước khi nhả lock để tránh để lại màn hình che khuất cho các ca cron sau.
