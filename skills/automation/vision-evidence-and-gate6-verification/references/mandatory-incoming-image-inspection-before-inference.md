# Kỷ Luật Đọc Ảnh Đầu Vào Bằng LLM Vision Trước Khi Suy Luận (Anti-Premature-Inference)

## 1. Bản Chất Sự Cố & Lời Nhắc Nhở Từ User
Trong phiên chuẩn hoá kênh ngày 2026-10-31, khi User gửi ảnh chụp màn hình một kênh TikTok kèm lệnh *"Chuẩn hoá kênh này"*, Coordinator đã mắc lỗi suy luận vội vã:
- Thay vì nạp ảnh người dùng gửi vào `browser_vision` để soi mắt tận nơi xem kênh thực tế đang có gì (Avatar là gì, video đã đăng là gì, giao diện ra sao), Coordinator nhảy ngay vào chạy `lookup_channel.py`, đọc Excel và quét video trong ổ đĩa.
- Khi User yêu cầu *"Đổi ava khác"*, Coordinator lại tiếp tục suy diễn chủ quan từ các video khác trong kho đĩa (tìm ra video có nữ) rồi tự tiện đề xuất avatar nữ, trong khi kênh thực tế và video đang đăng là cún cưng!
- User đã phản ứng gay gắt:
  > *"Lồn mẹ mày có guard ép đọc ảnh bằng llm trc khi suy luận r sao mày k tuân thủ"*

## 2. Invariant Đọc Ảnh Đầu Vào Trước Khi Suy Luận (Input Vision Gate)
1. **CẤM TUYỆT ĐỐI SUY LUẬN MÙ KHI CÓ ẢNH ĐÍNH KÈM:**
   - Khi tin nhắn người dùng có đính kèm ảnh (`[Image attached at: ...]`), hoặc khi câu lệnh mang tính tham chiếu thị giác (*"kênh này"*, *"ảnh này"*, *"sửa lỗi này"*, *"đổi ava khác"*):
   - **BƯỚC ĐẦU TIÊN CỦA TURN 1 BẮT BUỘC PHẢI LÀ STAGING VÀ MỞ ẢNH QUA `browser_vision`**.
   - CẤM chạy bất kỳ lệnh tra cứu database/Excel, quét đĩa hay lập kế hoạch nào TRƯỚC KHI LLM đã tận mắt đọc ảnh đầu vào.

2. **Quy Trình Staging & Soi Mắt Ảnh Đầu Vào O(1):**
   - Stage ảnh an toàn qua bash / script helper (`copy_user_img.py` hoặc copy ra staging).
   - Nạp vào `browser_navigate` trỏ tới file URL.
   - Gọi `browser_vision` với câu hỏi bóc tách đầy đủ:
     1. Tên hiển thị (Nickname) & Username (@handle) chính xác.
     2. Chỉ số: Following, Followers, Thích.
     3. Nội dung Avatar hiện tại: Là hình gì (người, vật, thú cưng, hay ảnh rác reg nick).
     4. Lưới video đã đăng: Có bao nhiêu video, view count từng video, và **CHỦ THỂ VIDEO ĐANG ĐĂNG LÀ GÌ** (đây là mỏ neo nhận diện thương hiệu của kênh).

3. **Chống Bẫy Lệch Nguồn (Source Desync Trap):**
   - Không được tin tưởng 100% vào nhãn Keyword trong Excel (ví dụ Excel ghi `Anime` nhưng thực tế video là `Thú cưng`).
   - Không được dùng các file video khác trong thư mục nguồn để phủ định video đã đăng trên kênh của User. Video đã đăng và ảnh trên profile của User là **CHÂN LÝ TỐI CAO (Ground Truth)**.

4. **Khi User Yêu Cầu "Đổi ava khác" / "Phương án khác":**
   - BẮT BUỘC rà soát lại đúng chủ thể của kênh mà mắt đã nhìn thấy ở ảnh đầu vào.
   - Nếu kênh là cún cưng -> Tìm thêm các góc chụp khác của chính chú cún cưng đó.
   - CẤM chuyển đổi đột ngột sang chủ thể hoàn toàn khác (từ cún sang người hoặc ngược lại) trừ khi có chỉ đạo rõ ràng từ User.
