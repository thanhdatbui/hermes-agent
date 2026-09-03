# Fast Swipe vs Deep Inspect Cadence & Session Deadline Optimization

## Bối cảnh & Nguyên nhân lỗi Max Duration
Trên các thiết bị cấu hình cũ (như Samsung Galaxy S7 / Android 8), mỗi chu kỳ swipe nếu thực hiện full chuỗi kiểm tra (`capture_screenshot` + `dump_ui_xml` qua ATX + `keyboard_cleanup` + `gem_blind_probe`) sẽ tốn từ **25s – 45s/video** (thậm chí 100s+ khi nghẽn I/O).

Hậu quả khi chạy 8–11 video:
- 100% video đều bị xem quá lâu (~30s/video), không tự nhiên so với hành vi người dùng thật.
- Tổng thời gian phiên tích lũy vượt ngưỡng `_deadline_monotonic` (1800s / 30 phút), dẫn đến crash dừng phiên ở bước cuối:
  `run plan max_duration_seconds exceeded before navigate profile`.

---

## Thiết kế Kiến trúc: Fast Swipe xen kẽ Deep Inspect

Mô phỏng hành vi người thật: lướt nhanh qua các video không thích và chỉ dừng lại xem kỹ ở một số video nhất định.

### 1. Fast Swipe (Lướt nhanh không dump XML)
- **Tần suất:** 2 – 4 video liên tiếp ngẫu nhiên.
- **Thao tác:** Chỉ `time.sleep(random(3.0, 6.0))` rồi gọi `input swipe` ADB. Không chụp ảnh, không dump XML, không gọi ATX.
- **Thời lượng:** ~3 – 6s/video.
- **Tương tác:** Bỏ qua kiểm tra like/follow (vì không có tọa độ UI XML).

### 2. Deep Inspect (Lướt đầy đủ có dump XML)
- **Tần suất:** Sau mỗi cụm 2 – 4 fast swipes, hoặc khi đổi feed tab.
- **Thao tác:** Chạy đầy đủ `capture_required_ui`, `dump_ui_xml`, kiểm tra popup/quảng cáo/bàn phím.
- **Thời lượng:** ~15 – 25s/video.
- **Tương tác Like/Follow:** Đẩy tỷ lệ like tại bước này lên **30% – 40%** (bù cho các video fast swipe không like) để đạt tỷ lệ trung bình **~10% like/tổng video toàn phiên**.

### 3. Baseline & End of Session
- **Đầu phiên (Baseline):** Bắt buộc Full XML dump để dọn sạch popup khởi động và xác nhận feed.
- **Cuối phiên (Profile Verification):** Bắt buộc Full XML dump để chuyển tab Hồ sơ và đối soát identity.

---

## Đánh giá Hiệu năng & An toàn
- **Tổng video/phiên:** Nâng lên **12 – 16 video/phiên** (vừa đủ độ dày tương tác nuôi acc).
- **Thời gian 1 phiên 14 video:**
  - 10 fast swipes (~40s) + 4 deep inspects (~80s) + Preflight/Profile (~40s) = **~2.5 – 3.5 phút/máy**.
  - Giảm ~85-90% thời gian thực thi so với phiên cũ (28-30 phút).
- **Phản xạ popup:** Nếu popup xuất hiện ở nhịp fast swipe, máy chỉ quẹt trượt trên modal 1–3 lần (~10s) trước khi gặp nhịp Deep Inspect để đóng X. Hoàn toàn tự nhiên và an toàn.
