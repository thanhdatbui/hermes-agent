# Kỷ Luật Phân Biệt: Sửa Script vs Can Thiệp Thiết Bị Thật Khi Nhận Yêu Cầu "Fix Đi"

> Ref: Sự cố báo cáo Cron `end-of-day-clear-tiktok-cache` (2026-10-31).

## 1. Bối cảnh & Sai lầm nghiêm trọng (Anti-Pattern)
- **Tình huống:** Cronjob dọn dẹp cache TikTok báo cáo hoàn tất 144 máy, lỗi 11 máy (3 máy Kibe, 8 máy Admin do Timeout/WIDGET_MISS). User ra lệnh ngắn gọn: *"Fix đi chứ"*.
- **Hành vi sai lầm của Coordinator:**
  - Nhầm lẫn giữa **Sửa lỗi Code/Script** (`clear-tiktok-cache.py`) và **Cứu hộ Thiết bị thật** (`recover_stuck_s7.py` / `batch_recover_s7.py`).
  - Tự ý chạy lệnh Level 1 soft-recovery (`am force-stop`, `input keyevent KEYCODE_SLEEP`) lên 11 máy farm thật trong khi máy có thể đang trong ca chạy nuôi feed, gây nguy cơ giật lock, làm văng app hoặc phá hỏng ca chạy của người dùng.
  - Giải thích dài dòng lôi "UI Automator dump" vào làm User bức xúc vì farm chuẩn dùng ATX-Agent (port 7912) và Deep Link Intent O(1).

---

## 2. Invariant Bắt Buộc Khi Nhận Lệnh "Fix Đi" Sau Báo Cáo Định Kỳ
1. **Ưu tiên Sửa Code (Fix Script First):**
   - Lệnh *"Fix đi"*, *"Sửa đi"* khi vừa nhận báo cáo cron/watchdog mặc định là **YÊU CẦU SỬA SCRIPT / HARDEN LOGIC RUNNER**, không phải lệnh đi phá máy hay khởi động lại thiết bị thật.
   - BẮT BUỘC kích hoạt ngay `unified_patch_pipeline.py` để vá file script mục tiêu (ở đây là `scripts/clear-tiktok-cache.py` trong `D:/Taadaa/automation-core`).

2. **Bảo Vệ Ca Chạy (No-Canary on Live Farm):**
   - Khi farm đang trong ca chạy hoặc không rõ lịch chạy, CẤM TUYỆT ĐỐI tự ý kích hoạt Canary trên máy thật.
   - Phải truyền cờ `--no-canary --no-canary-reason "Farm devices đang trong ca chạy nuôi feed, chuyển sang offline focused pytest để bảo vệ thiết bị"`.

3. **Kỹ thuật Fix Deep Link Clear Cache ban đêm:**
   - Ban đêm màn hình máy thường tắt (`Dozing / Screen OFF`). Nếu gửi ngay intent `snssdk1180://clean_cache` mà không đánh thức, giao diện dọn dẹp không kích hoạt được.
   - Script bắt buộc phải có preflight:
     ```python
     shell(serial, "input keyevent KEYCODE_WAKEUP")
     shell(serial, "wm dismiss-keyguard")
     time.sleep(0.8)
     ```
   - Khi màn hình đã bật, Deep Link Intent sẽ mở trúng đích ngay trang "Giải phóng dung lượng" trong < 2 giây, không bao giờ phải rơi vào vòng lặp fallback dò UI hay chạm vào UI XML.
