# Autonomous AI Recovery & Direct AI Reasoning Pipeline (2026-08-19)

## 1. Bản Chất Kiến Trúc 2 Phần (Farm Alerts)

### Phần 1: Báo Lỗi Hiện Trường (Producer Alert)
- Chụp ảnh màn hình điện thoại qua ADB, đóng dấu Banner Đỏ `[MÁY XX] - HH:MM DD/MM` ở đỉnh ảnh.
- Gửi Tin nhắn 1 vào nhóm Telegram **Farm Alerts** (`-5373649734`):
  `🚨 [MÁY XX] DỪNG PHIÊN` | `Script` | `Tài khoản` | `Lý do` | `Trạng thái: 🟢 ĐANG MỞ`.
- **Bảo toàn hiện trường:** Tuyệt đối không bấm Home, không tắt app, giữ nguyên trạng thái kẹt trên màn hình.

### Phần 2: AI Auto-Recovery (Trực Tiếp Trong Pipeline)
- **Vì sao không dùng Telegram Bot self-message loop?** Telegram Bot API theo thiết kế bảo mật sẽ KHÔNG BAO GIỜ gửi webhook/getUpdates cho các tin nhắn do CHÍNH bot token đó gửi ra (`outgoing message`), nhằm chống bot tự lặp vô hạn.
- Do đó, pipeline `send_farm_machine_alert` trong `automation-core/src/automation_core/alerts.py` kích hoạt trực tiếp Não AI (LLM / Vision Reasoning Engine):
  1. Trích xuất toàn bộ các node giao diện thực tế (text, desc, resource-id, bounds).
  2. Nạp vào Não AI suy luận ngữ cảnh: xác định loại màn hình, tính toán tâm tọa độ `bounds=[x1,y1][x2,y2]` -> center `((x1+x2)//2, (y1+y2)//2)`.
  3. Bắn lệnh ADB tương ứng (Tap / Swipe / Back / Home) giải phóng máy tại hiện trường.
  4. Gửi Tin nhắn 2 phản hồi vào nhóm:
     ```text
     🛠️ [AI AUTO-RECOVERY - MÁY XX]
     • Hướng sửa: <Giải thích lỗi kỹ thuật & phân tích cách giải quyết của AI>
     • Kết quả: <Hành động ADB thực tế đã can thiệp & trạng thái giải phóng máy>
     • (Nếu đúng ý bạn im lặng bỏ qua, cần sửa cách khác hãy nhắn lại)
     ```

## 2. Quy Tắc Vàng Khi Sửa Lỗi / Vá Code: CODE TRƯỚC -> CHẠY SCRIPT THAY TAY
- **CẤM** bấm tay / gửi ADB thô trước rồi mới viết code, vì sẽ làm mất hiện trường lỗi, không còn màn hình thật để kiểm chứng code.
- **Thứ tự bắt buộc 5 bước:**
  1. Giữ nguyên hiện trường.
  2. AI đọc ảnh/XML thật -> Viết code / thêm rule vào repo runner (`feed_swipe_smoke.py`, `benign_popup.py`) TRƯỚC.
  3. Kích hoạt chính hàm vừa code chạy thử trực tiếp trên máy đang kẹt tại hiện trường để kiểm chứng code tự vượt qua lỗi.
  4. Xuất git diff gọi Model Plan-Review audit (`VERDICT: APPROVED`) + pytest pass -> Commit & Push Git master.
  5. Báo cáo Tin nhắn 2 vào nhóm Farm Alerts.

## 3. Các Quy Tắc Xử Lý Thẻ & Popup Feed Đặc Thù
- **Thẻ "Người bạn có thể biết" / "Follow lại" trên Feed:** BẤM NÚT "Follow lại" màu đỏ (`follow_back_suggestion`), không bấm "Không quan tâm".
- **Kẹt ở bước nào gỡ tại bước đó:** Không máy móc ép mọi màn hình về Feed / Home. Nếu đang ở Login, OTP, Profile, Live, Shop... thì thực thi đúng thao tác logic của bước đó để tiếp tục luồng.
