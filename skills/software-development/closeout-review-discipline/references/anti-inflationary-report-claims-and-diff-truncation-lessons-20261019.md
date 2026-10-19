# Kỷ Luật Tránh Thổi Phồng Tuyên Bố Telemetry & Bài Học Tránh Truncation Diff (2026-10-19)

## 1. Ngữ Cảnh & Vấn Đề Thực Tế
Trong phiên vận hành chốt phiên `gpm_gmail_nurture_6h_report.py` và `cron_gpm_gmail_nurture.py`, test suite đạt 50/50 passed (100% green), luồng logic fail-closed được kiểm thử hoàn chỉnh, nhưng Closeout Gate bị kẹt ở mức 76-78 điểm (Strike 1..4) do Sol Auditor liên tục trừ điểm ở hai hạng mục:
1. **Telemetry & Observability:** Báo cáo in ra các nhãn vượt quá bằng chứng thực tế được kiểm chứng bởi code.
2. **Test Evidence Truncation:** File test phình to (>250 dòng diff) khiến diff text gửi lên Reviewer vượt ngân sách 20KB, kích hoạt cắt tỉa (`[... diff truncated ...]`), khiến Reviewer từ chối duyệt vì "phần test bị lược chưa được review".

---

## 2. Kỷ Luật Tránh Thổi Phồng Tuyên Bố (Anti-Inflationary Claim Invariant)
Reviewer trừ điểm nghiêm khắc khi chuỗi văn bản do script tạo ra hứa hẹn hoặc khẳng định nhiều hơn những gì câu lệnh truy vấn thực tế có thể chứng minh:

| Tuyên Bố Bị Trừ Điểm (Thổi Phồng) | Lý Do Reviewer Bắt Lỗi | Chuẩn Hóa Theo Thực Tế (Approved) |
| :--- | :--- | :--- |
| `Tổng số profile Group 10 (Google Live Ready): N` | Query chỉ lọc `GroupId = 10` và email trong Name, không chứng minh profile đã login hay live thật. | `Tổng số profile Gmail Group 10 (GPM DB): N` |
| `Trạng thái session Google: ✓ 100% cookie sống tốt, không có acc văng` | Khi `pending_relogin` rỗng, state file có thể thiếu profile hoặc DB lỗi/chưa quét hết; khẳng định "100% cookie sống tốt" là suy đoán vô căn cứ. | `Trạng thái session Google: ✓ Không có profile nào ghi nhận NEEDS_LOGIN trong state` |
| `⚠️ Acc văng cookie trong 6h qua: N acc` | `last_checked` chỉ là timestamp của lần kiểm tra gần nhất, không phải timestamp sự kiện cookie bị hủy; tên chỉ số gây hiểu lầm. | `⚠️ Acc phát hiện NEEDS_LOGIN trong 6h qua: N acc` |

---

## 3. Bài Học Về Fail-Closed & Ngữ Nghĩa Nguồn Dữ Liệu
Khi đọc SQLite DB để phục vụ báo cáo định kỳ:
1. **Phân biệt Lỗi Đọc DB vs Nhóm Rỗng:**
   - Hàm `get_group10_emails()` không được trả về `set()` khi gặp lỗi truy vấn. Bắt buộc trả về `None` khi file không tồn tại hoặc truy vấn gặp exception.
   - Báo cáo phải in rõ `⚠️ LỖI DB: Không thể đọc danh sách Group 10... (Fail-Closed)` khi kết quả là `None`.
   - Chỉ in `⚠️ CẢNH BÁO: Group 10 rỗng...` khi truy vấn thành công nhưng bảng trả về 0 bản ghi (`set()`).
2. **Đồng Bộ Đồng Hồ (Deterministic Clock):**
   - Trong hàm dựng báo cáo (`build_report_lines`), mọi biến thời gian (kể cả xác định ngày hôm nay `today_str`) bắt buộc phải tính từ tham số `now_ts` (`datetime.fromtimestamp(now_ts)`), cấm gọi lẫn `datetime.now()` để đảm bảo tính xác định và có thể kiểm thử biên chuẩn xác.

---

## 4. Ngân Sách Diff & Khống Chế Truncation
1. **Cắt tỉa do Test Suite phình to:** Khi một PR thêm nhiều unit test dày đặc, nếu gom toàn bộ file test lớn vào một commit đơn lẻ, unified diff dễ dàng vượt ngưỡng 20KB.
2. **Khắc phục:** 
   - Tách biệt commit triển khai logic (O(1)) và commit bổ sung test nếu cần thiết.
   - Luôn kiểm tra `git diff --stat HEAD~1` trước khi chạy Closeout Gate để đảm bảo diff nằm trong ngưỡng an toàn (~15-18KB) chống kích hoạt `TRUNCATION_MANIFEST`.
