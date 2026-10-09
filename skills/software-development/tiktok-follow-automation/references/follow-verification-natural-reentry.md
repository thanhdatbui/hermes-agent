# Follow Verification & Anchor Pre-engagement (Anti-Release Pattern)

## 1. Gốc rễ lỗi "Nhả liền" (27/80 máy sau 5 ngày cooldown vẫn bị nhả)
- **Sai lầm giả định**: Cooldown thời gian (2-5 ngày) sẽ tự hết bị nhả follow.
  - **Thực tế số liệu**: Sau 5 ngày nghỉ, máy bấm follow phát đầu tiên vẫn bị TikTok drop ngay lập tức. Nguyên nhân do tài khoản đã bị gắn cờ trust-score thấp hoặc bị drop hành vi lặp lại.
- **Tử huyệt kỹ thuật**: Động tác `pull-to-refresh` (vuốt kéo reload tại chỗ) ngay sau khi tap follow để kiểm tra nút.
  - Người dùng thật KHÔNG BAO GIỜ vừa follow ai xong cũng kéo reload trang.
  - Đây là bot signature lộ liễu nhất kích hoạt shadow-drop của TikTok server.

## 2. Quy trình tương tác Anchor chuẩn xác (Mode 2)
Trước khi mở tab Following của Anchor:
1. **Kiểm tra video trên Profile Anchor**:
   - Nếu KHÔNG CÓ video (ví dụ nick mới chưa kịp đăng video): Back ra ngay lập tức, bỏ qua anchor này (safe-skip).
2. **Xem video tự nhiên**:
   - Cuộn nhẹ trang profile xuống danh sách video.
   - Bấm mở 1 video bất kỳ (cover).
   - Xem hết / xem đủ thời lượng video từ **8 đến 15 giây** (random dwell).
3. **Tương tác trên màn hình Video**:
   - Thả tim ngẫu nhiên tỷ lệ **50% – 70%** (nút Thích trên video).
   - Bấm nút **FOLLOW TRỰC TIẾP TRÊN VIDEO PLAYER** (nút dấu `+` đỏ cạnh avatar tác giả).
   - Đợi **2 – 4 giây** tại màn hình video để server TikTok ghi nhận.
4. **Trở về Profile (Natural Re-entry)**:
   - Bấm Back quay lại trang Profile của Anchor.
5. **Xác minh trạng thái (CẤM Pull-to-refresh)**:
   - Profile tự động nạp trạng thái mới từ server khi back về.
   - Đọc nút action (delay settling 1.5s, poll thêm 1 lần nếu cần):
     - `Đã follow` / `Bạn bè` / `Nhắn tin`: Thành công, mở tab Following.
     - `Follow` đỏ: Bị TikTok nhả -> Dừng session ngay lập tức (Canary bảo vệ acc).

## 3. Cadence Spot-check trong danh sách Following
- **Lượt follow #1 (Canary)**: Bắt buộc verify qua `_path_b_verify` (bấm mở profile đọc nút rồi back về). Nhả -> dừng ngay.
- **Lượt #2 trở đi**: Bấm follow trực tiếp trên row trong list, delay 1.5–3.5s. KHÔNG mở profile, KHÔNG reload.
- **Nhịp kiểm tra định kỳ**: Cứ sau mỗi **3 đến 5 nick** (adaptive/random gap 3..5, cap 5) mới chọn 1 nick chạy `_path_b_verify`.
- Nếu phát hiện nhả ở bất kỳ lần spot-check nào -> Dừng session ngay lập tức.
