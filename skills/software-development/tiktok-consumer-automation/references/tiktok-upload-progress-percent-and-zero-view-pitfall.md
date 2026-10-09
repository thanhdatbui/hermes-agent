# Pitfall: TikTok Upload Loading Overlay (%) vs Zero View

## Hiện tượng thực tế trên Android / Farm
- Khi bấm "Đăng" (Post), TikTok trên Android (Samsung S7) lập tức tạo một item/container ở ô đầu tiên trong lưới Profile (RecyclerView `[col=0, row=0]`).
- Trên ô đó xuất hiện vòng tròn loading hiển thị phần trăm chạy từ từ (ví dụ: `96%`).

## Sai lầm phổ biến trong automation script
1. **False-Positive do đếm số ô (`current > baseline`)**:
   - Khi container ô mới xuất hiện, XML hierarchy đã sinh ra node `FrameLayout`/`clickable="true"`.
   - Script nếu chỉ so sánh số lượng video trước và sau khi đăng (`current > baseline`) sẽ kết luận `SUCCESS` quá sớm khi file mới tải được 96%.
   - Hậu quả: Script vội switch account, đóng app hoặc dọn Recent apps làm đứt gánh upload ngầm của TikTok.
2. **Sai lầm khi chờ mốc "100%"**:
   - TikTok **không bao giờ** hiện "100%". Khi upload/transcode hoàn tất, vòng tròn loading biến mất hoàn toàn và tile chuyển thành video tĩnh bình thường.
3. **Sai lầm khi lấy mốc "0 view" làm dấu hiệu video mới**:
   - Video cũ mới đăng gần đây chưa cắn đề xuất hoặc video bị flop cũng mang số view là `0` (hoặc icon play không có số view).
   - Lấy `0 view` làm điều kiện verify sẽ bắt nhầm video cũ flop.

## Quy tắc Verify chuẩn xác (Clean Completion Gate)
1. **Kiểm tra đang tải (In-Progress Gate)**:
   - Quét ô trên cùng bên trái `[col=0, row=0]` của lưới Profile.
   - Nếu phát hiện node có text match regex `r"\d+%"`, hoặc node là `android.widget.ProgressBar`, hoặc loading icon -> BẮT BUỘC poll loop (ngủ 2-3s) chờ tiếp.
2. **Xác nhận hoàn tất sạch sẽ (Clean Completion Gate)**:
   - Sạch bóng Progress: Không còn bất kỳ node nào chứa `%` hay `ProgressBar` trên lưới Profile.
   - Top-left tile ổn định: Ô đầu tiên là tile video hoàn chỉnh (chỉ còn thumbnail cover + thông số play bình thường, không còn loading overlay).
3. **Timeout Watchdog**:
   - Cho phép timeout chờ vòng xoay biến mất trong khoảng 60s - 120s (tùy dung lượng video và tốc độ proxy).
   - Quá thời gian vẫn kẹt `%` (ví dụ rớt mạng/proxy ở 96%): dừng lại ngay, chụp ảnh hiện trường, mark `MANUAL_REVIEW / BLOCKED`, CẤM ghi đè `UPDATE_WORKBOOK` và CẤM switch account.
