# Phân tích Workflow: TIKTOK - ĐỀ XUẤT VÀ TIM BẠN BÈ (.gemphonefarm)

## 1. Thông tin file
- **File gốc**: `TIKTOK-ĐỀ-XUẤT-VÀ-TIM-BẠN-BÈ_Protected.gemphonefarm`
- **Tình trạng**: Giải mã thành công bằng tool `D:\Taadaa\tiktok-follow\tools\decrypt_gemphonefarm.py` (password `!#gemlogin$#&^%*`).
- **Quy mô**: 193 nodes, 288 edges.

## 2. Variables & Inputs
- `Đường_dẫn_tài_khoản`: Excel path, range `TaiKhoan!B1:E9999`, match `deviceId` -> `taiKhoan`.
- `Số_lần_lướt`: Số video duyệt trong vòng lặp chính.
- `Random1`: 1-2 (số lượt quẹt mồi khởi động: 2 hoặc 4 video).
- `Random2`, `%_Tim`: Tỷ lệ thả tim (1-100).
- `Random3`, `%_Comment`: Tỷ lệ comment (1-100).
- `Đường_dẫn_Comment`: File text comment (mặc định trỏ `D:\TiktokComment.txt`, đọc ngẫu nhiên từng dòng).

## 3. Cấu trúc Flow chính
1. **Dọn app ngầm**: Menu Recents -> Bấm `Đóng tất cả` / `ĐÓNG TẤT CẢ` / `CLOSE ALL` -> `HOME`.
2. **Khởi động app**: Package `com.ss.android.ugc.trill`, đợi load `Trang chủ` / `Home`.
3. **Switch account**:
   - Mở tab `Hồ sơ` / `Profile`.
   - Dập popup: `Xác minh email của bạn` (Đóng), `Liên kết email` (Để sau), `Truy cập Facebook` (Không cho phép), `Bật lịch sử người xem` (Lưu), Captcha bar `verify-bar-close` (Đóng), `Từ Chối`.
   - Kiểm tra text `@{{taiKhoan}}`. Nếu chưa đúng, mở switcher (`//node[@resource-id="...:id/rfm"]/node[2]/node[1]`), chọn đúng account.
4. **Vòng lặp For You & Friend Interaction**:
   - Quẹt mồi ban đầu.
   - Vòng lặp `Số_lần_lướt`:
     - Nhận diện bạn bè qua text: `//node[@text="Bạn bè của bạn"]`, `//node[@text="Được follow bởi  "]`, `//node[@text="Bạn bè với  "]`.
     - Nếu là bạn bè:
       - Kiểm tra `Đã thích video`. Nếu chưa thích và `Random2 <= %_Tim` -> Tap `//node[@content-desc="Thích"]`.
       - Nếu `Random2 <= 10` -> Tap `//node[@content-desc="Thêm hoặc xóa video này khỏi mục Yêu thích."]`.
       - Nếu `Random3 <= %_Comment` -> Mở panel comment `//node[@content-desc="Đọc hoặc viết bình luận. Bóc tem bình luận"]`, đọc 1 dòng text -> gõ -> tap `Tán thành`.
     - Nếu không phải bạn bè -> Quẹt lướt qua (Swipe up).

## 4. Đánh giá kiến trúc khi port sang Farm 80 máy S7
- **Dump XML liên tục**: Rất nặng trên S7, gây nóng máy và nghẽn CPU nếu dump mỗi lượt swipe.
- **Rủi ro spam cluster**: Tương tác chéo giữa các nick farm trong vòng kín dễ bị thuật toán TikTok phát hiện Sybil network.
- **Spam comment từ file text**: Nguy cơ cao bị Action Block / shadowban do nội dung không khớp video.
- **Tag 'Bạn bè của bạn bè' trên For You**: Bản chất là social proof signal thuật toán gắn vào For You. Codebase hiện tại (`feed_swipe_smoke.py`) đã phân bổ sẵn tab `friends` (like 80%) và feed For You (like ngẫu nhiên tự nhiên nhịp Deep Inspect), video bạn bè hiện trên For You vẫn được like theo phân phối tự nhiên mà không cần ép rule cưỡng bức.
- **Ngày dưỡng sinh (Day 2, 5)**: Mục tiêu là hạ Trust Score rủi ro và xả 48h Action Cooldown. Tuyệt đối không tích hợp tính năng đi lùng bạn bè để like/comment dạo vào ngày dưỡng sinh vì sẽ phá vỡ cooldown và làm lộ mạng bot khép kín.
- **Khuyến nghị**: Không bê nguyên xi flow tương tác bạn bè vào script nuôi acc. Toàn bộ các popup trong script GemPhone (`verify-bar-close`, `Bật lịch sử người xem`, `Liên kết email`, `Xác minh email`, `Nhật ký của bạn`) hệ thống `automation-core` (`benign_popup.py` & `tiktok_popup.py`) đã xử lý đầy đủ và tối ưu hơn.
