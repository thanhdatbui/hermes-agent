# Quy Trình Tự Động Xử Lý Lỗi & Giám Sát Thụ Động (Self-Healing Farm Alerts & Passive Monitoring)

## 1. Triết Lý Vận Hành: "Management by Exception"
- **Vấn đề**: Farm 80 máy vận hành 3 ca liên tục, nếu mỗi lỗi nhỏ (kẹt popup, lạc phòng Live, dính dialog) đều dừng máy chờ operator xử lý tay thì operator bị quá tải thông báo và gián đoạn ca chạy.
- **Mô hình chuẩn**: Khi máy phát sinh sự cố, AI/Script **TỰ ĐỘNG CHẨN ĐOÁN & THỰC HIỆN GIẢI CỨU TẠI HIỆN TRƯỜNG TRƯỚC** ➔ Bắn báo cáo kèm ảnh chụp màn hình đóng dấu `[MÁY XX]` và kết quả xử lý về nhóm Telegram **Farm Alerts** (`-5373649734`).
- **Cơ chế duyệt của Operator**:
  - **Đúng ý**: Operator **im lặng bỏ qua**, máy tiếp tục vào ca chạy bình thường.
  - **Chưa đúng ý / Cần can thiệp**: Operator reply tin nhắn cảnh báo để ra lệnh điều chỉnh.

---

## 2. Quy Trình Xử Lý Sự Cố Tự Động (Auto-Resolution Loop)
1. **Phát hiện Block/Stuck**: Worker phát hiện máy dừng vì popup, Live room, hoặc mất focus.
2. **Auto-Resolver tại chỗ**:
   - *Lạc vào phòng Live*: Dừng xem 3-6s tự nhiên ➔ Tap nút `✕` góc trên bên phải (`[1020, 78]`, `id/close`, `id/e63`) hoặc vuốt mạnh lướt qua video tiếp theo.
   - *Dính Popup bạn bè / Suggestion*: Tự động tap nút `✕` hoặc *"Không quan tâm"*.
   - *Dính Modal Repost / Shop Detail*: Dừng xem 3-6s ➔ Tap nút `✕` đóng bảng.
   - *Mất focus giả SystemUI*: Lọc bỏ `com.android.systemui`, xác nhận lại dominant package TikTok để tiếp tục luồng.
3. **Chụp ảnh đóng dấu & Báo cáo Telegram**:
   - Chụp lại màn hình sau khi đã áp dụng biện pháp giải cứu.
   - Vẽ banner đỏ định danh: `[MAY XX] - HH:MM DD/MM`.
   - Gửi ảnh kèm nội dung:
     - 🚨 `[MÁY XX] DỪNG PHIÊN`
     - • `Script`: Tên script
     - • `Chẩn đoán`: Chi tiết blocker
     - • `Tự động xử lý`: Biện pháp đã thực hiện (thoát Live / tắt popup)
     - • `Trạng thái`: 🟢 ĐANG MỞ (Đã tự xử lý & sẵn sàng phiên sau)

---

## 3. Ngôn Ngữ & Phong Cách Giao Tiếp (User Rule 19/08)
- Toàn bộ báo cáo, giải thích kỹ thuật, kết quả audit/review gửi cho Operator **BẮT BUỘC dùng TIẾNG VIỆT dân dã, trực diện, dễ hiểu**.
- Tránh trích dẫn nguyên văn tiếng Anh kỹ thuật dài dòng từ các subagent reviewer gây khó theo dõi.

---

## 4. Giả Lập Pin Ngẫu Nhiên (>50%)
- Mức pin giả lập qua ADB không set cứng 80% đều tăm tắp.
- Tự động chọn ngẫu nhiên trong dải **55% đến 95%** (`random.randint(55, 95)`):
  - `dumpsys battery set level <55-95>`
  - `dumpsys battery set status 2` (Đang sạc)
  - `dumpsys battery set ac 1` (Cắm nguồn AC)
