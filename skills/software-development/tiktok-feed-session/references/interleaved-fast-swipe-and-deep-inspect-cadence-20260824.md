# Interleaved Fast Swipe and Deep Inspect Cadence (2026-08-24)

## Bối cảnh & Nguyên nhân lỗi `run plan max_duration_seconds exceeded`
- **Hiện tượng:** Máy lướt feed (đặc biệt các dòng máy yếu như Samsung Galaxy S7) bị dừng phiên với lỗi `run plan max_duration_seconds exceeded before navigate profile`.
- **Nguyên nhân gốc:**
  - 100% video đều thực hiện chuỗi capture đầy đủ: `capture_screenshot` -> `dump_ui_xml` (qua ATX) -> `keyboard_cleanup` -> `blind_popup probe` -> `watch_delay`.
  - Trên Galaxy S7 / Android cũ, mỗi chu kỳ capture và dump UI XML mất ~20–30 giây.
  - Kết hợp với `watch_delay` (3–8s), máy dừng ở 1 video lên tới 25–40 giây.
  - Một phiên 8–11 video tích lũy thời gian lên tới 25–30 phút, chạm ngưỡng timeout `DEFAULT_DEVICE_TIMEOUT_SECONDS = 1800.0` (30 phút) ngay lúc chuẩn bị bấm sang tab `Profile` (`navigate profile`).
  - Ngoài ra, việc 100% video đều dừng xem 30–40s là fingerprint không tự nhiên (người thật lướt nhanh 60–70% video dở và chỉ dừng lại xem 20–30% video hay).

---

## Thiết kế tối ưu: Fast Swipe xen kẽ Deep Inspect

### 1. Phân loại 2 chế độ vuốt:
1. **Fast Swipe (Lướt nhanh):**
   - Không gọi ATX dump XML, không chụp ảnh.
   - Chỉ chờ `watch_delay` ngẫu nhiên **3.0s – 6.0s** rồi gửi lệnh ADB swipe (`input swipe ...`) vuốt qua ngay.
   - Thời gian thực tế: ~3.5s – 6.5s / video.
2. **Deep Inspect (Lướt đầy đủ):**
   - Đầy đủ dump UI XML, chụp ảnh, kiểm tra và dismiss benign popup, keyboard cleanup, live room invites.
   - Thời gian thực tế: ~20s / video (đóng vai trò là video người dùng dừng lại xem kỹ).

### 2. Chu kỳ và phân bổ tỷ lệ:
- **Chu kỳ xen kẽ:** Sau ngẫu nhiên **2 – 4 video lướt nhanh** (`fast_count = random.randint(2, 4)`), thực hiện **1 video Deep Inspect**.
- **Tỷ lệ thực tế:** ~70% video lướt nhanh (3–6s) và ~30% video xem kỹ (20s), khớp với mô hình hành vi người dùng thật trên short-video platforms.
- **Tổng video/phiên:** Nâng lên **12 – 16 video/phiên**.
- **Thời gian toàn phiên:** Rút gọn từ **28–30 phút** xuống chỉ còn **~3 – 4 phút/máy**, giải phóng 80% tải CPU/RAM cho S7 và dứt điểm lỗi timeout.

---

## Quy tắc bù tương tác (Like Compensation) & Safety Guardrails

### 1. Tương tác Like theo hành vi người thật:
- Lượt Fast Swipe không có XML -> Không tìm tọa độ nút Thích -> Không Like (hợp lý vì người thật không like video vừa lướt qua 2 giây).
- Tăng xác suất xét Like ở các lượt Deep Inspect lên **~30% – 35%** (thay vì 10% như cũ).
- Kết quả toàn phiên vẫn đạt chuẩn **1 – 2 like / 15 video (~10% tổng thể)**, mà Like lại rơi đúng vào các video xem lâu.

### 2. Bắt buộc Deep Inspect ở biên:
- **Video 0 (Baseline / Startup):** Bắt buộc 100% Deep Inspect để dọn sạch mọi popup mở app, kiểm tra feed tab hợp lệ trước khi vào vòng lặp swipe.
- **Video cuối (Verify Profile):** Bắt buộc 100% Deep Inspect để chuyển tab Hồ sơ, kiểm tra username/identity và hoàn tất phiên.

### 3. Xử lý rủi ro Popup trong chu kỳ Fast Swipe:
- Khi popup modal bất ngờ xuất hiện giữa chu kỳ Fast Swipe, máy có thể quẹt 1–3 lần trên popup trước khi đến nhịp Deep Inspect (kéo dài tối đa 10–20s).
- Đây là phản xạ bình thường của người dùng thật (quẹt tay 1–2 lần theo quán tính, thấy không trôi mới nhìn và bấm nút đóng).
- **Stuck Fallback:** Nếu sau 2 lần Fast Swipe liên tiếp phát hiện màn hình không thay đổi hoặc có dấu hiệu kẹt, tự động ngắt Fast Swipe và chuyển ngay sang Deep Inspect để dọn popup.
