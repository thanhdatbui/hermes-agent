# Quy trình nghiệm thu bằng chứng (Evidence First) cho Farm Device Automation

## 1. Lỗi phổ biến: Teardown-Before-Capture & Assumption-Over-Observation
- **Nguyên nhân**: Agent gửi lệnh `am force-stop` và `input keyevent KEYCODE_HOME` để teardown máy trước, rồi mới gọi chụp màn hình `screencap`. Hoặc Agent giả định rằng lệnh ADB tap đã thực thi thành công mà không quan sát thực tế màn hình.
- **Hậu quả**: Ảnh gửi về là màn hình chính (Android Launcher Home) hoặc màn hình Feed, hoàn toàn vô giá trị trong việc chứng minh tính đúng đắn của tác vụ.

## 2. Quy tắc Invariant cho Bằng Chứng Nghiệm Thu (MEDIA:)
1. **Chụp bằng chứng TRƯỚC KHI Teardown**:
   - Chụp ảnh màn hình `screencap` ngay khi đang ở màn hình kết quả của app (màn hình xác nhận cuối cùng).
   - Sau khi lưu ảnh thành công, mới được phép chạy lệnh teardown (`am force-stop`, `KEYCODE_HOME`).
2. **Quy trình Dọn Dẹp Bộ Nhớ TikTok (Clear Cache & Downloads)**:
   - Script `clear-tiktok-cache.py` bắt buộc xóa cả 2 mục: **Bộ nhớ đệm** (Cache) và **Tải về** (Downloads).
   - Ảnh nghiệm thu BẮT BUỘC là màn hình **"Giải phóng dung lượng"** hiển thị cả 2 mục:
     + `Bộ nhớ đệm: 0,0MB`
     + `Tải về: 0,0MB`
   - TUYỆT ĐỐI CẤM gửi ảnh màn hình Home làm bằng chứng nghiệm thu cho tác vụ clear cache.
3. **Pre-Send OCR / XML Inspection Gate**:
   - Trước khi đính kèm tag `MEDIA:<path>`, Agent bắt buộc phải kiểm tra XML hoặc text của ảnh xem có đúng artifact mong đợi không. Nếu không thấy artifact, không được báo hoàn thành.
