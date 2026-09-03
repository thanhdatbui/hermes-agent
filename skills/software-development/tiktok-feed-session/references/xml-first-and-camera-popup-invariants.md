# TikTok UI Automation & XML-First Invariants (Session 2026-08-21)

## 1. Tọa độ thanh điều hướng đáy & Ranh giới nút Tạo (+)
Trên màn hình 1080x1920 (Samsung Galaxy S7 Farm):
- **Trang chủ (Home)**: `[0, 1794][216, 1920]` (Tâm: X=108, Y=1857)
- **Cửa hàng (Shop)**: `[216, 1794][432, 1920]` (Tâm: X=324, Y=1857)
- **Nút Tạo/Camera (+)**: `[432, 1794][648, 1920]` (Tâm: **X=540, Y=1857**) — Nguy hiểm
- **Hộp thư (Inbox)**: `[648, 1794][864, 1920]`
- **Hồ sơ (Profile)**: `[864, 1794][1080, 1920]` (Tâm: X=972, Y=1857)

### Quy tắc an toàn tọa độ:
1. **Vuốt đóng thanh thông báo (Notification shade)**:
   - CẤM: `input swipe 540 1800 540 300` (Y=1800 chạm đỉnh nút `+`).
   - BẮT BUỘC: `input swipe 540 1540 540 300` (Y <= 1540, cách thanh bottom bar > 250px).
2. **CẤM Hardcode Fallback Tap Bottom Center**:
   - Mọi fallback click ở `(540, 1700~1850)` đều có rủi ro nhảy vào camera quay video/LIVE nếu modal đã đóng.

---

## 2. Bắt buộc XML-First & Runtime Node Validation
- **Ở tầng Navigation (`calibrate_screens.py`)**:
  - Xóa bỏ hoàn toàn fallback bấm tọa độ mù tỷ lệ màn hình (`_fallback_navigation_point`).
  - BẮT BUỘC phải đọc XML, tìm đúng Node UI (`text="Hồ sơ"` hoặc `content-desc="Profile"`) rồi mới tap vào tâm Node. Nếu không thấy Node $\rightarrow$ fail-closed / `not-found`.
- **Ở tầng AI Auto-Recovery (`vision_client.py` & `agent.py`)**:
  - Khi `action_type == "tap"`: Bắt buộc đối soát `(tx, ty)` xem có nằm trong `bounds` của Node UI hợp lệ trong XML dump trực tiếp hay không.
  - Nếu không có Node khớp $\rightarrow$ Tự động đổi sang phím `BACK` (Keyevent 4), TUYỆT ĐỐI CẤM tap mù.

---

## 3. Classifier Camera Mode vs Feed Caption AI
- **Vấn đề**: Caption video có chữ `"Ảnh"` (nút carousel) và nhãn cảnh báo TikTok `"Có chứa nội dung do AI tạo"` (từ `"tạo"`) bị bộ phân loại cũ khớp chuỗi con tưởng nhầm là màn hình Camera quay video.
- **Quy tắc nhận diện Camera/Creation mode chuẩn**:
  - Quét element ở vùng cận đáy (`Y >= 1000`).
  - So khớp EXACT text/content-desc với danh sách chế độ quay: `{"10 phút", "60s", "15s", "văn bản", "10m", "templates", "photo", "camera"}`.
  - Bắt buộc phải xuất hiện ít nhất **2 chế độ quay KHÁC NHAU (`distinct modes >= 2`)**.

---

## 4. Quy tắc tương tác các Popup đặc thù
1. **Popup "Follow bạn bè của bạn"**:
   - Khi xuất hiện danh sách bạn bè gợi ý kèm nút `"Follow lại"` / `"Follow back"` $\rightarrow$ Quét và bấm toàn bộ các nút `"Follow lại"` để tăng follow chéo tự nhiên, sau đó bấm `"X"` hoặc `BACK` để thoát.
2. **Popup "Để phát LIVE, bạn cần"**:
   - Xuất hiện khi vô tình rơi vào setup LIVE $\rightarrow$ Tìm node `"Đã hiểu"` để click và gửi phím `BACK` thoát sạch sẽ về For You Feed.
3. **Popup / Overlay Quảng cáo & Survey**:
   - BẮT BUỘC `swipe up` lướt qua video khác, CẤM click vào CTA hay nút Đóng.
