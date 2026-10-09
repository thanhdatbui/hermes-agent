# Anti-Spam Alert & Debounce Discipline (Alert-Once Invariant)

## 1. Bối cảnh & Nguyên tắc cốt lõi
Trong hệ thống tự động hóa Phone Farm, các tác vụ bảo trì định kỳ (dọn cache, checklive, đồng bộ dữ liệu) thường chạy theo lịch cron chu kỳ ngắn (mỗi 5–15 phút).
Khi phát sinh lỗi (kể cả lỗi nhỏ, lỗi cục bộ trên 1-2 máy hay sự cố lớn):
- **BẮT BUỘC Alert-Once (Báo đúng 1 lần)**: Lỗi chỉ được gửi cảnh báo Telegram duy nhất 1 lần cho mỗi phiên / ngày đối với cùng một nội dung sự cố.
- **CẤM TUYỆT ĐỐI**: Để cron tick lặp lại bắn cảnh báo spam liên tục mỗi chu kỳ vào group / channel Farm Alert.

## 2. Các cạm bẫy gây Spam Alert (Pitfalls)
1. **Lỗi logic tính tỷ lệ retry (False-Positive Farm Failure)**:
   - *Hiện tượng*: Một batch có 80 máy, 78 máy đã hoàn thành, chỉ còn 2 máy retry. Nếu công thức kiểm tra là `f_count > total_attempted / 2`, thì 2/2 máy fail sẽ cho tỷ lệ 100% fail → script ngộ nhận là sự cố sập farm diện rộng.
   - *Giải pháp*:
     - Phải có ngưỡng cứng số máy lỗi tuyệt đối (ví dụ: `f_count >= 5`).
     - Tỷ lệ fail phải tính trên quy mô tổng thể hoặc có phân biệt rõ giữa "lượt chạy đầu (full batch)" và "lượt retry cuốn chiếu".
2. **Thiếu bộ lọc Dedup / Debounce trạng thái**:
   - *Hiện tượng*: Khi một máy bị timeout (ví dụ ADB socket đơ), script cron cứ mỗi 15 phút thức dậy thấy chưa xong lại gọi `send_farm_script_alert` bắn 1 tin nhắn mới.
   - *Giải pháp*:
     - Lưu `last_alert_msg` và `last_alert_date` (hoặc hash của message) vào file trạng thái (`*_state.json`).
     - Trước khi bắn alert: Kiểm tra nếu `last_alert_date == today` và `last_alert_msg == current_alert_msg` → Bỏ qua gửi tin (silent exit), không quấy rầy user.
3. **Phục hồi ADB socket trước khi timeout**:
   - Khi thiết bị Android bị đơ adbd (không phản hồi lệnh shell dù `get-state` ra `device`), cần có bước ping nhanh (timeout 5s). Nếu không phản hồi, tự động chạy `adb -s <serial> reconnect` thay vì để worker treo suốt 240s rồi fail hàng loạt.
