# Khắc Phục Bẫy INVALID_MEDIA_FILE Do Stale Receipt Cũ & Ép Buộc Soi Mắt Thật Sự

## 1. Bản Chất Yêu Cầu Của User: "Ép Agent Phải Tự Đọc Ảnh Xong Mới Được Suy Luận Trả Lời"
- Khi người dùng phàn nàn Gate bị over-engineered, phản xạ sai lầm của Agent là hạ cấp Gate thành kiểm tra tầm thường (`os.path.isfile` và `size > 0`). Người dùng đã lập tức chấn chỉnh:
  > *"Sửa guard... Nhưng tóm lại ép agent phải tự đọc ảnh xong ms đc suy luận trả lời"*
- **Nguyên tắc bất biến:**
  1. CẤM buông lỏng Gate thành kiểm tra file rỗng. Bắt buộc Agent phải thực sự soi mắt đọc ảnh (`browser_vision` hoặc `run_winrt_ocr.py`) thì mới có bằng chứng để suy luận và gửi `MEDIA:`.
  2. CẤM báo cáo mồm hoàn thành UI nếu không có ảnh chứng minh.
  3. CẤM gửi ảnh mù nếu ảnh đó chưa được Agent soi mắt trong phiên hiện tại.

## 2. Lỗi Over-Engineering Cần Khắc Phục
1. **Bẫy So Sánh Hash Với Receipt Cũ Quá Hạn (Stale Receipt Tamper Trap):**
   - Các đường dẫn ảnh chụp màn hình tái sử dụng (như `D:/OneDrive/TaadaaData/admin_screen.png`, `screen.png`) từng có receipt được ký từ nhiều ngày trước.
   - Hàm `_media_file_verdict` ban đầu gọi `_latest_signed_receipt` mà **không kiểm tra TTL**. Khi file được chụp mới hôm nay, SHA-256 mới lệch với receipt cũ từ 2 ngày trước, Gate ngộ nhận file bị "tampered" và chặn gửi tin nhắn với mã `INVALID_MEDIA_FILE`.
   - **Cách sửa:** Trong `_media_file_verdict`, chỉ kiểm tra hash tamper đối với receipt **còn trong khung TTL (`0 <= age <= DEFAULT_TTL_SECONDS`)**. Nếu receipt đã hết hạn (> 300s), nó không đại diện cho trạng thái hiện tại; Gate trả về `NO_RECEIPT` để ép Agent soi mắt lại ảnh mới, tuyệt đối không vu khống file là "tampered".

2. **Tự Động Cấp Receipt Khi Agent Đã Soi Mắt Bằng `browser_vision`:**
   - Agent tuân thủ Invariant bằng cách gọi `browser_navigate("file:///...")` và `browser_vision(...)`, nhưng Gate lại yêu cầu phải chạy script phụ `run_winrt_ocr.py` hoặc `--record-vision` thì mới có receipt.
   - **Cách sửa:** Hàm `transform_llm_output_check` tích hợp `_extract_seen_images_from_tool_calls(tool_calls)`. Khi Agent đã gọi `browser_vision` trên file ảnh trong lượt, Gate tự động ghi nhận vé kiểm chứng cho file đó.

3. **Dung Sai Mtime Trên Windows NTFS (`MTIME_TOLERANCE = 2.0s`):**
   - Mức dung sai cũ `1e-6` microsecond gây lỗi giả khi file được copy qua SMB/OneDrive dù SHA-256 đã khớp tuyệt đối 100%. Nâng lên 2.0s để triệt tiêu false-positive do làm tròn float trên Windows.
