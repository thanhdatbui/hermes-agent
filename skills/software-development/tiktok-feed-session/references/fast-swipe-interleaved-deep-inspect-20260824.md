# Fast Swipe Xen Kẽ Deep Inspect & Timeout Calibration (2026-08-24)

## Bối cảnh & Vấn đề gốc
Trên các dòng thiết bị cấu hình cũ như Samsung Galaxy S7 (Exynos 8890, Android 8), việc thực hiện full chuỗi ATX XML dump + chụp ảnh screenshot sau 100% các video lướt feed (`feed_swipe_smoke.py`) tiêu tốn từ 15–25 giây cho mỗi video. 

Hệ quả:
1. **Nghẽn thời gian:** Một phiên 8–11 video kéo dài tới 25–30 phút, thường xuyên vượt ngưỡng `DEFAULT_DEVICE_TIMEOUT_SECONDS` (1800s / 30 phút) và quăng lỗi `run plan max_duration_seconds exceeded before navigate profile`.
2. **Fingerprint bất thường:** Người dùng thật trên TikTok không bao giờ xem 100% các video dừng lại đúng 30s. Người thật lướt qua nhanh (~1–4s) với 60–70% video không thích, chỉ dừng lại xem lâu (10–20s) và like ở các video hay.

---

## Kiến trúc Tối ưu: Fast Swipe xen kẽ Deep Inspect

### 1. Fast Swipe (Lướt nhanh ~70% video):
- **Timing:** Watch delay ngắn ngẫu nhiên `2.0s – 5.0s`.
- **Thao tác:** Gửi lệnh ADB swipe trực tiếp (`input swipe ...`).
- **Tối ưu:** Tuyệt đối KHÔNG gọi ATX dump XML (port 7912), KHÔNG chụp ảnh.
- **Lightweight Guardrail (<0.2s):** Gửi lệnh kiểm tra nhanh `get_focused_activity(ctx)` qua `dumpsys window / activity`. Nếu phát hiện mất focus TikTok (do popup ngoài, crash app hoặc mở nhầm app khác) -> Lập tức ép chuyển sang `Deep Inspect` để chạy recovery ladder xử lý.
- **Summary Row:** Ghi row `action="fast_swipe"`, `xml_available=False`, `status=success`, `safety_status="ok"`.

### 2. Deep Inspect (Kiểm tra đầy đủ ~30% video):
- **Điều kiện kích hoạt:**
  1. Video đầu tiên của phiên (`is_first_video = (swipe_count == 1)` — làm baseline).
  2. Định kỳ ngẫu nhiên sau mỗi `2 – 4` video Fast Swipe (`videos_until_deep_inspect <= 0`).
  3. Khi chuyển tab feed (`for-you` <-> `following`).
  4. Video cuối cùng của phiên (`is_last_video = (swipe_count == selected_total_videos)`).
  5. Khi Lightweight Guardrail phát hiện bất thường.
- **Thao tác:** Chạy full chuỗi `_capture_step` (ATX XML dump, screenshot, popup check, keyboard cleanup, safe-guard).
- **Tương tác Like:** Chỉ xét Like ở các lượt Deep Inspect với tỷ lệ nâng lên `20%` (tương đương ~9.5% - 10% Like trên tổng số video toàn phiên, đúng chuẩn hành vi người thật chỉ like video xem lâu).
- **Reset Counter:** Reset `videos_until_deep_inspect = random.randint(fast_swipe_interval_min, fast_swipe_interval_max)`.

---

## Timeout Calibration (1800s -> 600s)
- **Hạ `DEFAULT_DEVICE_TIMEOUT_SECONDS` từ `1800.0s (30 phút)` xuống `600.0s (10 phút)`:**
  - Thời gian chạy thực tế của phiên mới 12–16 video chỉ mất ~3–4 phút.
  - Ngưỡng timeout 10 phút (gấp 2.5–3 lần thời gian thực) là đủ an toàn khi mạng trễ hoặc có popup xử lý lại.
  - Nếu máy bị đơ thật (treo USB, chết adbd), hệ thống ngắt ngay sau 10 phút và gửi alert, tránh chiếm dụng worker trong 30 phút làm nghẽn hàng đợi của 80 máy.
