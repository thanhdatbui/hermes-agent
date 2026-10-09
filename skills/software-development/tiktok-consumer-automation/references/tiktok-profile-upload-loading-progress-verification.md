# Pitfall: TikTok Profile Grid Video Upload Loading & Verification

## Hiện tượng
Khi vừa bấm "Đăng" (Post), TikTok trên máy Android (đặc biệt dòng Samsung S7) bắt đầu tiến trình upload ngầm. Tại màn hình Profile grid (lưới video cá nhân):
- Ô đầu tiên (top-left tile) xuất hiện một vòng tròn phần trăm loading (ví dụ: `96%`).
- Video cũ bị dịch chuyển sang bên phải.
- Node container (`FrameLayout`/item của `RecyclerView`) cho video mới này có thể đã được sinh ra sớm trong UI XML, kèm theo các thuộc tính `clickable="true"`.

## Bẫy sai lầm phổ biến (Pitfalls)
1. **Hiểu lầm TikTok sẽ hiện 100%:** Khi tải xong, TikTok **KHÔNG BAO GIỜ hiện 100%**. Vòng tròn loading phần trăm sẽ tự động biến mất và ô chuyển thành thumbnail video bình thường.
2. **Dùng "0 view" để verify thành công:** Sau khi upload xong, video mới thường hiển thị 0 view (hoặc icon Play). **Tuyệt đối không lấy 0 view làm điều kiện verify**, vì các video cũ flop hoặc vừa đăng trước đó cũng có thể có 0 view, dẫn tới false-positive nghiêm trọng.
3. **Đếm tile tăng ảo (`current > baseline`):** Nếu script chỉ đếm số lượng video tile trên Profile mà không kiểm tra trạng thái loading, việc container xuất hiện với vòng tròn 96% sẽ làm tile count tăng lên ngay lập tức. Script vội vàng kết luận `SUCCESS`, chuyển sang tắt app/switch account/xóa file tạm, dẫn tới việc upload ngầm bị đứt gánh hoặc biến thành Draft.

## Tiêu chuẩn kiểm chứng chuẩn (Clean Verification Gates)
1. **In-Progress Gate:**
   - Quét toàn bộ lưới Profile (đặc biệt tile góc trên bên trái `[col=0, row=0]`).
   - Nếu có node con match regex phần trăm `r"\d+%"`, hoặc có `android.widget.ProgressBar`, hoặc icon/vòng tròn loading:
     - **BẮT BUỘC PHẢI CHỜ (Poll loop):** Ngủ 2-3s rồi dump XML lại. Tuyệt đối không được chuyển state tiếp theo.
2. **Clean Completion Gate:**
   - Video chỉ được coi là đã lên sóng thật sự khi thỏa mãn **đồng thời cả 2 điều kiện**:
     1. Toàn bộ lưới Profile sạch bóng, không còn bất kỳ node nào chứa `%` hay `ProgressBar`.
     2. Ô đầu tiên (top-left tile) đã ổn định ở dạng video hoàn chỉnh (thumbnail cover + thông số play bình thường, không còn overlay trạng thái tải).
3. **Watchdog & Timeout:**
   - Đặt timeout tối đa 60s - 120s tùy proxy/kích thước video.
   - Nếu hết timeout mà vẫn kẹt ở `%`: dừng ngay, chụp ảnh màn hình, đánh dấu `MANUAL_REVIEW / BLOCKED`. Cấm ghi `UPDATE_WORKBOOK` và cấm đổi tài khoản.
