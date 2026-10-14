# Kỹ Thuật Ghim Top View Video TikTok & Pitfalls Cuộn Lưới Profile

## 1. Bản chất nghiệp vụ: "Ghim clip nhiều view" vs "Clip đầu tiên"
- **Không bao giờ ghim clip đầu tiên một cách mù quáng**: Clip đầu tiên trên lưới profile (vị trí row 1, col 1) thường chỉ là clip mới đăng gần nhất theo thời gian (ví dụ: clip 345 view), hoàn toàn không phải clip nhiều view nhất.
- **Top View thực sự nằm rải rác hoặc sâu dưới fold**: Video viral ăn đề xuất (hàng chục nghìn view, ví dụ 21K view) thường là các clip cũ đã đăng từ lâu. Nếu chỉ dump UI ở viewport ban đầu (1 màn hình đầu ~9-12 ô lưới), script sẽ bỏ sót toàn bộ các clip nhiều view thực sự.

## 2. Quy trình quét & ghim Top View chuẩn (Scroll Accumulation)
1. **Mở Profile và chờ Cold Start ổn định**:
   - Trên các thiết bị Android cũ/yếu (Samsung S7 / Android 7), lệnh mở TikTok (`am start com.ss.android.ugc.trill/.MainActivity`) cần thời gian chờ `time.sleep(5.0 - 6.0s)` trước khi bắt đầu dump UI hoặc tương tác switcher, tránh lỗi `PROFILE_ROOT_NOT_CONFIRMED`.
   - Bắt buộc kiểm tra và mở khóa màn hình (`input keyevent 82` + `KEYCODE_WAKEUP`).
2. **Cuộn sâu quét tích lũy (Deep Scroll Scan)**:
   - Thực hiện cuộn xuống (`swipe 540 1400 540 600 400`) theo số lần định cấu hình (ví dụ `scrolls=3-5`).
   - Sau mỗi lần cuộn, dump UI ATX (port 7912), parse danh sách video tiles và merge vào tập hợp tổng, loại trùng theo `views` hoặc định danh tile.
   - Sắp xếp toàn bộ video đã quét theo `views` giảm dần (`reverse=True`).
3. **Đưa video mục tiêu vào Viewport trước khi tương tác**:
   - Sau khi xác định được video top view, nếu video đó hiện không nằm trong màn hình hiện tại (do đã cuộn đi), cần đưa video đó vào tầm nhìn (scroll/bring to view) để lấy tọa độ bounds chính xác trước khi tap.
4. **Quy trình ghim từng video**:
   - Tap vào tile video mục tiêu $\rightarrow$ Chờ player mở.
   - Tìm nút "Chia sẻ" (Share) qua ngữ nghĩa hoặc tọa độ fallback $\rightarrow$ Bấm mở Action Sheet.
   - Bắt nút "Ghim lên đầu" (Pin to top) $\rightarrow$ Tap nút ghim $\rightarrow$ Bấm Back quay lại Profile.
   - Read-back độc lập: Dump lại Profile và xác nhận số lượng video mang nhãn "Đã ghim" tăng lên và đúng video mục tiêu.
   - Lặp lại quy trình cho đến khi đủ số lượng ghim tối đa (mặc định 3 clip).
