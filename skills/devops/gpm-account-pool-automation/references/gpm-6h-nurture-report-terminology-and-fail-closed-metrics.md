# Chuẩn Hóa Thuật Ngữ và Đo Lường Fail-Closed Cho Báo Cáo 6H GPMLogin

## 1. Nguyên Tắc Phân Biệt Nguồn Dữ Liệu và Tránh Nhãn Suy Đoán
Khi tổng hợp báo cáo định kỳ từ GPM SQLite DB (`profile_data.db`) và state file (`gpm_gmail_nurture_state.json`), cần tuân thủ nghiêm ngặt tính chính xác của dữ liệu nguồn:

- **Không dùng nhãn vượt quá dữ liệu:** Tránh ghi nhãn `Google Live Ready` nếu chỉ truy vấn `GroupId = 10` từ GPM DB mà chưa chạy live check thực tế. Dùng nhãn chính xác: `Gmail Group 10 (GPM DB)`.
- **Không khẳng định tuyệt đối khi thiếu chứng cứ:** Tránh câu `100% cookie sống tốt` khi state không có `NEEDS_LOGIN`, vì state rỗng hoặc lỗi đọc DB cũng có thể tạo ra kết quả không có `NEEDS_LOGIN`. Dùng câu trung thực theo dữ liệu: `Không có profile nào ghi nhận NEEDS_LOGIN trong state`.
- **Đúng ngữ nghĩa sự kiện:** Tránh gọi `văng cookie trong 6h qua` khi dữ liệu chỉ dựa trên `last_checked`. Dùng nhãn chuẩn: `phát hiện NEEDS_LOGIN trong 6h qua`.

## 2. Thiết Kế Fail-Closed Cho Hàm Truy Vấn DB
Hàm truy vấn profile (`get_group10_emails`) bắt buộc phân biệt rõ ràng 2 trạng thái:
1. **Lỗi hệ thống / DB không đọc được:** Trả về `None`. Báo cáo phải xuất `⚠️ LỖI DB: Không thể đọc danh sách Group 10 từ GPM DB (Fail-Closed)!` và dừng xử lý để không rò rỉ dữ liệu ngoài nhóm.
2. **Nhóm rỗng nhưng DB bình thường:** Trả về `set()`. Báo cáo phải xuất `⚠️ CẢNH BÁO: Group 10 rỗng, không có profile Gmail nào (Fail-Closed)!`.
3. **Chỉ đọc (Read-Only):** Kết nối SQLite bắt buộc dùng URI `file:<path>?mode=ro`, không fallback sang chế độ mở ghi thông thường.

## 3. Lọc Chỉ Số Nuôi và Session Ấm
- **Chỉ đếm lượt thành công:** Biến `nurtured_6h` bắt buộc kiểm tra `status == "success"` và `last_n > 0` cùng `(now_ts - last_n) <= (6 * 3600)`. Tuyệt đối không đếm profile mang trạng thái lỗi/crash.
- **Session ấm (`warm_48h`):** Bắt buộc `status == "success"`, `last_n > 0` và `(now_ts - last_n) <= (48 * 3600)`.
- **Tính xác định về thời gian (Deterministic Clock):** Trong hàm tạo báo cáo (`build_report_lines`), mọi phép so sánh ngày (như `today_str`) phải lấy từ `datetime.fromtimestamp(now_ts)` thay vì `datetime.now()` để đảm bảo unit test xác định ranh giới ngày chính xác.

## 4. Cooldown Cho Profile NEEDS_LOGIN
Trong script nuôi chính (`cron_gpm_gmail_nurture.py`), profile có `status == "NEEDS_LOGIN"` không được bỏ qua vĩnh viễn (gây nghẽn vòng chọn) mà áp dụng `NEEDS_LOGIN_COOLDOWN_SECONDS = 86400` (24h). Sau 24h, profile được đưa vào danh sách đánh giá lại để watchdog hoặc luồng nuôi thử phục hồi.
