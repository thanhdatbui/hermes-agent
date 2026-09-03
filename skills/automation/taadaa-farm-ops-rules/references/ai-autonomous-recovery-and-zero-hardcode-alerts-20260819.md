# AI Autonomous Recovery & Zero-Hardcode Alert Architecture (2026-08-19)

## 1. Bản Chất Của "AI Auto-Recovery" (Autonomous AI vs Hardcoded If/Else)

User phạt nặng khi hệ thống "fake AI recovery" bằng các nhánh if/else string matching cứng nhắc (`if "follow" in err... elif "live"... else "Dừng phiên bất thường"`):
- **CẤM TUYỆT ĐỐI** dùng chuỗi if/else rập khuôn để sinh câu báo cáo hay điều khiển máy.
- **BẮT BUỘC** gọi Model AI thực thụ (Claude CLI `--effort max` / LLM Vision) nạp trực tiếp toàn bộ UI context (text, bounds, id) của máy đang kẹt.
- AI tự tính toán tọa độ tâm của bounds `((x1+x2)//2, (y1+y2)//2)` và quyết định lệnh ADB tối ưu (`tap`, `swipe`, `back`, `home`).
- Hệ thống nhận quyết định JSON từ AI ➔ thực thi ADB lên máy ➔ gửi nguyên văn phân tích thông minh của AI về Telegram Farm Alerts.

---

## 2. Chuẩn 2 Tin Nhắn Báo Cáo Tại Nhóm Farm Alerts

### Tin Nhắn 1 (Ảnh Hiện Trường Nguyên Trạng)
- Ảnh chụp màn hình tại thời điểm kẹt, vẽ Banner Đỏ `[MAY XX] - HH:MM DD/MM`.
- Caption:
  ```html
  🚨 <b>[MÁY XX] DỪNG PHIÊN</b>
  • <b>Script:</b> <code>multi-machine-feed-session</code>
  • <b>Tài khoản:</b> <code>username</code>
  • <b>Lý do:</b> <i>unexpected popup/dialog marker detected: ...</i>
  • <b>Trạng thái:</b> 🟢 <b>ĐANG MỞ</b> <i>(Tự động chạy tiếp phiên sau)</i>
  ```

### Tin Nhắn 2 (AI Auto-Recovery - Hướng Sửa & Kết Quả Thật)
- Báo cáo do AI tự sinh sau khi phân tích UI XML và thực thi ADB:
  ```html
  🛠️ <b>[AI AUTO-RECOVERY - MÁY XX]</b>
  • <b>Hướng sửa:</b> <Phân tích chi tiết của AI về blocker và định hướng xử lý>
  • <b>Kết quả:</b> <b><Hành động thực tế đã làm: tap tọa độ, vuốt qua hay back></b>
  • <i>(Nếu đúng ý bạn im lặng bỏ qua, cần sửa cách khác hãy nhắn lại)</i>
  ```

---

## 3. Quy Tắc Xử Lý Thẻ Gợi Ý Bạn Bè ("Người mà bạn có thể biết" / "Hằng nguyễn")
- Khi xuất hiện thẻ gợi ý kết bạn trên TikTok Feed:
  - User quy định: **BẤM NÚT "Follow lại"** (màu đỏ) để tăng follow chéo tự nhiên theo kịch bản farm.
  - Trigger selector XPath: Thu hẹp vào header text `'//node[contains(@text, "Người mà bạn có thể biết")]'` (tránh bắt nhầm các nút Follow lại ở trang profile/search).
  - Action selector: `'//node[@text="Follow lại" or @content-desc="Follow lại" or contains(@text, "Follow lại")]'`.

---

## 4. Dọn Dẹp Tiến Trình Stale Trong RAM Sau Khi Vá Code
- **Cảnh báo bẫy bộ nhớ:** Khi cập nhật code alert/flow mới, các tiến trình Python cron (`run_tiktok.py`, `multi_machine_feed_session.py`) đang chạy ngầm trong RAM vẫn giữ module cũ trong bộ nhớ và tiếp tục gửi alert theo template cũ.
- **Thao tác bắt buộc:** Sau khi cập nhật code (`pip install -e` / git commit), phải quét `psutil` / `tasklist` và kill sạch các tiến trình runner cũ đang chạy để ép hệ thống nạp module mới.
