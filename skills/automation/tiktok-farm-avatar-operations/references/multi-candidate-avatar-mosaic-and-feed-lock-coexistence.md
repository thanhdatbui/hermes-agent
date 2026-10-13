# Quy Trình Trích Xuất Đa Phương Án Avatar & Kỷ Luật Khóa Thiết Bị (Lock Coexistence)

## 1. Trích Xuất Đa Phương Án Avatar từ Video Gốc
Khi người dùng yêu cầu đổi sang avatar khác hoặc muốn nhiều lựa chọn ("Hình ava khác đi"):
1. **Quét nhiều video Full HD trong thư mục gốc:** Không chỉ quét một video đầu tiên mà nên quét các video chất lượng cao (1080x1920 như `4.mp4`, `5.mp4`, `10.mp4`, `20.mp4`).
2. **Bộ lọc khuôn mặt chất lượng cao (Composite Scoring):**
   - Độ sắc nét (Laplacian variance).
   - Biểu cảm tự nhiên: Tránh các khung hình há miệng quá to (phát âm), nhắm mắt/nháy mắt (asymmetry mắt), hoặc bị chữ phụ đề/caption che khuất (clutter score).
   - Headroom chuẩn: Crop khung vuông 512x512 giữ khoảng cách đỉnh đầu tới mép ~15-20% để khi hiển thị trong hình tròn TikTok không bị lẹm trán.
3. **Ghép Mosaic So Sánh Trực Quan:**
   - Ghép 3 phương án cạnh nhau kèm nhãn rõ ràng (Cand 1, Cand 2, Cand 3) thành 1 ảnh mosaic (`m67_cand_mosaic_all.jpg`).
   - Mở `browser_vision` soi mắt kiểm tra trước khi gửi thẻ `MEDIA:` cho người dùng chọn.

## 2. Kỷ Luật Tránh Xung Đột Khóa Nuôi Feed (Lock Coexistence)
1. **Kiểm tra hiện trường máy thật:**
   - Chạy `python D:/Taadaa/tools/inspect_machine.py <M>` để xác nhận màn hình và app đang chạy.
   - Kiểm tra `~/.codex/device-locks/` xem máy có đang bị giữ lock bởi ca nuôi feed (`run_tiktok.py --mode multi-machine-feed-session`) hay không.
2. **Nguyên tắc không cướp lock:**
   - Nếu máy đang trong ca nuôi feed (PID active), **TUYỆT ĐỐI KHÔNG** can thiệp ép chạy avatar ngay làm gãy ca nuôi.
   - Đặt trạng thái hàng đợi `avatar_replace_queue` và Excel sang `PENDING`.
   - Báo cáo rõ ràng cho người dùng: Dữ liệu đã sẵn sàng trên đĩa và trong hàng đợi, tiến trình upload avatar sẽ tự động thực hiện ngay khi máy hoàn tất ca nuôi và giải phóng device lock.
