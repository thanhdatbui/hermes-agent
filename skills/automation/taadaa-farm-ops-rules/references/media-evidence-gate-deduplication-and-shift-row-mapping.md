# Media Evidence Gate Deduplication & Shift-Row Mapping (Taadaa Phone Farm)

## 1. MEDIA Evidence Gate Deduplication (Chống Gửi Lặp Ảnh Nghiệm Thu)
- **Bối cảnh**: Gate 6 (Media Evidence Gate) yêu cầu các báo cáo can thiệp thiết bị farm (run, test, fix lỗi, recovery) phải có `MEDIA:<path_anh>` ở dòng riêng biệt.
- **Hiện tượng / Phản hồi của User**: Khi thảo luận nhiều lượt (turns) về cùng một sự cố sau khi đã gửi ảnh nghiệm thu, bot tiếp tục đính kèm lại cùng một đường dẫn ảnh ở mỗi câu trả lời khiến user khó chịu ("Ủa sao cứ gửi hình này v").
- **Quy tắc chuẩn hóa**:
  1. **Chỉ gửi 1 lần khi nghiệm thu**: Chỉ đính kèm thẻ `MEDIA:<path>` trong tin nhắn báo cáo kết quả nghiệm thu ban đầu hoặc khi có bằng chứng ảnh mới phát sinh từ thiết bị.
  2. **Các lượt trả lời tiếp theo (Follow-up turns)**: Khi user hỏi thêm về nguyên nhân, phân tích log, đối soát số liệu hoặc thảo luận sau đó, TUYỆT ĐỐI KHÔNG đính kèm lại ảnh cũ trừ khi user yêu cầu xem lại.
  3. **Giải thích rõ ràng bằng chứng**: Khi user hỏi tại sao lại gửi ảnh đó, giải thích ngắn gọn: đó là ảnh chụp màn hình máy thật chứng minh trạng thái tài khoản/màn hình đích tại thời điểm hoàn tất ca.

## 2. Shift-Row Mapping & Account Allocation Invariant (Đối Soát Ca & Row)
- **Bối cảnh**: Hệ thống farm Taadaa phân bổ 8 slot/máy tương ứng với 8 Rows trong workbook (`taikhoan_run_safe.xlsx` / `Tik1-Tik8.xlsx`).
- **Hiện tượng**: User thắc mắc "Vì sao sáng chạy row 1 lại đi lấy nick này" khi thấy ảnh chụp màn hình chứa tài khoản mới tạo (`@beheo5746`, 0 video, 0 follow).
- **Quy tắc phân định 4 Ca / Ngày**:
  - **Ca 1 (Sáng 06:00 - 12:00)**: Chạy **Row 1** (ngày lẻ) hoặc **Row 2** (ngày chẵn). Tài khoản chạy thường là nick chính/nick đã nuôi lâu (đã có nhiều video).
  - **Ca 2 (Chiều 12:00 - 18:00)**: Chạy **Row 3** (ngày lẻ) hoặc **Row 4** (ngày chẵn).
  - **Ca 3 (Tối 18:00 - 00:00)**: Chạy **Row 5** (ngày lẻ) hoặc **Row 6** (ngày chẵn).
  - **Ca 4 (Đêm 00:00 - 06:00)**: Chạy **Row 7** (ngày lẻ) hoặc **Row 8** (ngày chẵn). Tài khoản chạy thường là nick mới đăng ký (0 video, đang ngâm tài khoản).
- **Quy tắc đối soát khi điều tra**:
  - Khi xem ảnh hoặc log của một máy, BẮT BUỘC kiểm tra timestamp và xác định rõ ca chạy:
    - Nếu timestamp vào khoảng 00:00 - 03:00 sáng, đó là **Ca 4 (Đêm) chạy Row 7**, nick nạp vào là nick của Row 7 (ví dụ `@beheo5746`), KHÔNG ĐƯỢC nhầm lẫn là Ca Sáng (Row 1).
    - Đến Ca 1 (06:00 sáng), hệ thống mới chuyển sang nạp nick của Row 1 (ví dụ `@lipsellczaw`).
