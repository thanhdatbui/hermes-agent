# Bẫy Thường Gặp & Kỷ Luật Đối Soát Khi Chuẩn Hoá Kênh TikTok Farm

## 1. Bẫy Lệch Ngách Giữa Video Thực Tế Và Workbook (Niche Drift)
- **Hiện tượng:** Trên file Excel `Tik*.xlsx`, cột Keyword/Hashtag ghi một đằng (ví dụ: `Âm nhạc`, hashtag `#nhac #amnhac...`), nhưng video thực tế đăng trên kênh lại là chủ đề hoàn toàn khác (ví dụ: video nấu nướng, đồ ăn, giò chả).
- **Hành động bắt buộc:** Luôn soi mắt kiểm tra lưới video thực tế qua ảnh Profile trước khi quyết định Hashtag/Bio/Avatar. Nếu phát hiện lệch ngách, phải cập nhật lại cột Keyword/Hashtag trong `Tik*.xlsx` và đổi hashtag pool đúng với video thực tế.

## 2. Bẫy Lệch Chủ Thể Avatar (Creator Mismatch)
- **Hiện tượng:** Video thực tế toàn bộ là nam thanh niên phát biểu/quay vlog, nhưng avatar kênh lại để hình nữ MC hoặc selfie nữ (do các đợt reg/gán avatar ngẫu nhiên trước đó).
- **Hành động bắt buộc:** Avatar phải phản ánh đúng nhân vật trong video hoặc hình ảnh tối giản, trung tính phù hợp ngách (góc setup, công cụ, sản phẩm).

## 3. Bẫy Rác Dư Thừa Sau Reg (Donation / Campaign Badges)
- **Hiện tượng:** Tài khoản TikTok sau khi reg thường dính các liên kết từ thiện hoặc badge mặc định như `Đang hỗ trợ: WWF-UK`.
- **Hành động bắt buộc:** Khi nạp bio tiếng Việt mới, phải làm sạch hoàn toàn các liên kết/badge này để trang cá nhân sạch sẽ và tự nhiên.

## 4. Phong Cách Tên Hiển Thị (Teencode & Tên Người Dùng Tự Nhiên)
- **Kinh nghiệm thực tế (User Feedback):** Các dạng tên viết hoa teencode tự nhiên của người dùng (ví dụ: `Ngọc TRinh` với chữ `R` viết hoa kiểu teen) là **hoàn toàn bình thường và phổ biến** trên TikTok.
- **Hành động bắt buộc:** GIỮ NGUYÊN các tên teencode/style tự nhiên nếu người dùng không yêu cầu sửa; CẤM tự ý "chuẩn hoá" bẻ tên sang danh từ riêng hành chính cứng nhắc. Chỉ can thiệp sửa tên khi tên là dãy số ngẫu nhiên rác lúc reg nick (`user12345678`) hoặc lỗi font/encoding.

## 5. Kỷ Luật Cấm Lock Tên Hiển Thị (`.manual_name_locked`)
- **Nguyên tắc:** TikTok giới hạn đổi tên 7 ngày 1 lần. Khi chuẩn hoá tên, chỉ cắm cờ `.manual_avatar_locked` và `.manual_hashtag_locked` cho thư mục media.
- **TUYỆT ĐỐI KHÔNG** tạo cờ `.manual_name_locked` trong thư mục video gốc/render trừ khi có lệnh đích danh của User, để hệ thống có thể linh hoạt đổi tên sau thời gian cooldown.

## 6. Kỷ Luật Ghim Bài (Pin Top Video)
- Kênh có video đạt view cao ($\ge 1.000$ views) bắt buộc phải ghim lên ô số 1.
- Nếu không có video nào đạt trần view thì giữ nguyên, không ghim video view lẹt đẹt (< 100 views).

## 7. Bẫy Phân Trần Văn Xuôi Thay Vì Đưa Ra Visual Proposal (The "Lải Nhải" Trap)
- **Sai lầm:** Khi user bảo "chuẩn hoá 2 kênh này", agent chỉ dùng text liệt kê 4 lỗi rồi kết thúc bằng "Anh duyệt kế hoạch trên em sẽ làm". User cần chọn avatar thực tế ngay, việc nói suông không có avatar làm user khó chịu ("ava chuẩn bị lại đâu? Cứ lải nhải đéo làm...").
- **Cách làm đúng:** Lập tức viết script chạy trích frame và dựng file ảnh canvas tổng hợp `avatar_proposals_*.jpg` (ghép ảnh tròn 512x512 của các phương án) trong lượt chat đầu tiên. Phản hồi luôn phải có `MEDIA:<canvas>` đi kèm để user chỉ cần bấm chọn 1A hay 1B.
- **Xử lý khi User yêu cầu "Tạo ava khác":** Khi User chốt một kênh nhưng yêu cầu kênh còn lại "tạo ava khác", TUYỆT ĐỐI KHÔNG quay lại lặp lại kế hoạch hay nói suông. Lập tức quét các video khác trong kho để trích xuất 3-4 góc cảnh hoàn toàn mới (ví dụ: góc bàn làm việc/workspace, coder làm việc trước màn hình, chân dung nụ cười, tech speaker thuyết trình), tạo ngay canvas phương án mới gửi cho User chọn dứt điểm.

