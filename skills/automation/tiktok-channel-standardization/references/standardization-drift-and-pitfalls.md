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

## 4. Bẫy Viết Hoa Sai Chính Tả Trên Tên Hiển Thị
- **Hiện tượng:** Tên hiển thị bị viết hoa lệch lạc (ví dụ: `Ngọc TRinh`, `thanh KHoa`).
- **Hành động bắt buộc:** Format lại chuẩn danh từ riêng tiếng Việt (`Ngọc Trinh`, `Thanh Khoa`).

## 5. Kỷ Luật Cấm Lock Tên Hiển Thị (`.manual_name_locked`)
- **Nguyên tắc:** TikTok giới hạn đổi tên 7 ngày 1 lần. Khi chuẩn hoá tên, chỉ cắm cờ `.manual_avatar_locked` và `.manual_hashtag_locked` cho thư mục media.
- **TUYỆT ĐỐI KHÔNG** tạo cờ `.manual_name_locked` trong thư mục video gốc/render trừ khi có lệnh đích danh của User, để hệ thống có thể linh hoạt đổi tên sau thời gian cooldown.

## 6. Kỷ Luật Ghim Bài (Pin Top Video)
- Kênh có video đạt view cao ($\ge 1.000$ views) bắt buộc phải ghim lên ô số 1.
- Nếu không có video nào đạt trần view thì giữ nguyên, không ghim video view lẹt đẹt (< 100 views).
