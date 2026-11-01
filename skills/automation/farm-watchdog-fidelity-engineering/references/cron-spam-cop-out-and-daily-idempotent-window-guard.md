# Anti-Cop-Out Discipline & Triple Guard for Recurring Briefing Watchdogs

## 1. Kỷ Luật Tuyệt Đối: Cấm Xóa Cronjob Đối Phó (Anti-Cop-Out Invariant)
- **Hành vi sai trái:** Khi User phản ánh cronjob gửi sai giờ, spam, hoặc chọn sai nội dung (ví dụ: "mày bị điên à giờ này còn spam"), agent vội vàng gọi `cronjob(action='remove')` để xóa phăng job đi cho "hết lỗi".
- **Hậu quả:** Đây là hành vi làm đối phó, phủi tay, phá hủy tính năng tự động hóa mà User đã dày công thiết lập.
- **Kỷ luật:** CẤM TUYỆT ĐỐI xóa cronjob đang vận hành khi User yêu cầu xử lý lỗi spam/sai giờ. BẮT BUỘC giữ nguyên job ID/schedule và đi thẳng vào **sửa cơ chế gốc rễ (root cause) trong script thực thi**.

## 2. Kiến Trúc 3 Tầng Bảo Vệ Cho Scheduled Briefing / Watchdog
Khi một cronjob/script có nhiệm vụ định kỳ phát tin nhắn (như báo cáo buổi sáng 06:00 AM, ca chốt ngày), script BẮT BUỘC phải cài đặt 3 tầng bảo vệ cơ học độc lập:

### Tầng 1: Time-Window Hard Guard (Khóa Khung Giờ Cứng)
- Không bao giờ phụ thuộc 100% vào việc scheduler gọi đúng giờ (có thể bị scheduler trigger lại, canary test chạy nhầm, hoặc script sync gọi thử).
- Đặt kiểm tra ngay dòng đầu tiên của hàm `main()`:
```python
if '--force' not in sys.argv and '--test' not in sys.argv:
    # Ví dụ: Chỉ cho phép chạy đúng trong khung 06:00 - 06:59 sáng
    if time.localtime().tm_hour != 6:
        return  # Im lặng exit 0, không in gì ra stdout
```
- Bất kỳ tiến trình nào gọi script ngoài khung giờ quy định đều bị ngắt ngay lập tức, stdout rỗng ➔ Scheduler im lặng 100%.

### Tầng 2: Calendar-Day Idempotency Guard (Khóa 1 Lần / Ngày)
- Tránh trường hợp trong cùng khung giờ bị scheduler thử lại nhiều lần hoặc User chạy kiểm tra làm nổ tin 2 lần:
```python
today_str = time.strftime("%Y-%m-%d")
marker_file = Path("D:/Taadaa/runtime/linh_duong_last_run.txt")

if marker_file.exists():
    try:
        if marker_file.read_text(encoding="utf-8").strip() == today_str:
            return  # Hôm nay đã phát tin rồi, không phát lần thứ hai
    except Exception:
        pass
```
- Khi script tổng hợp thành công và chuẩn bị in `msg`, ghi ngay `today_str` vào `marker_file`.

### Tầng 3: Candidate Sanitization & Silent Watchdog on Empty
- **Lọc bỏ session đã đóng:** Khi quét State DB / Session DB để tìm việc dở dang, BẮT BUỘC lọc bỏ ngay các session đã có dấu hiệu chốt phiên:
  * Regex: `RE_CLOSEOUT_APPROVED.search(text)`
  * Regex: `r'\b(done|xong|chốt\s+phiên|hoàn\s+tất)\b'` mà không có `RE_CLOSEOUT_REJECTED`.
  * Không đưa các session đã xong vào danh sách ứng viên (candidates), tránh việc LLM bị ép phải chọn bừa một task cũ đã chết rồi tâng lên làm nhiệm vụ trọng điểm.
- **Silent Pattern khi rỗng:** Nếu danh sách ứng viên rỗng hoặc model trả về không có task nào thực sự là nút thắt (`mission: None`), script PHẢI `return` im lặng, KHÔNG in stdout. Scheduler của Hermes sẽ tuân thủ quy tắc "EMPTY stdout means SILENT".
