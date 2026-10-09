# CapCut Template Dismissal & UIAutomator Helper App Recovery (2026-09-04)

## 1. Coordinator Invariant (Zero-Direct-Debug During Delegation)
- **Quy tắc cốt lõi:** Khi nhận Farm Alert `[MÁY N]` hoặc task debug/recovery:
  - Coordinator **BẮT BUỘC** gọi `delegate_task` cho subagent xử lý từ Turn 1.
  - **CẤM TUYỆT ĐỐI** Coordinator tự ý chạy lệnh terminal, inspect ADB, dump UI, hoặc debug trực tiếp trên máy farm — kể cả khi user hỏi tiến độ ("Ủa lâu thế à", "xong chưa").
  - Khi user hỏi tiến độ: Báo cáo trạng thái hiện tại của background subagent ngắn gọn, tuyệt đối không panic chạy thêm lệnh ADB song song gây tranh chấp thiết bị và race condition.

---

## 2. UIAutomator Helper App Occlusion (`com.github.uiautomator` / `io.appium.uiautomator2.server`)
- **Hiện tượng:** Quá trình capture UI hoặc khởi động app khiến app helper `com.github.uiautomator/.MainActivity` nhảy lên foreground, che khuất màn hình TikTok (`com.ss.android.ugc.trill`).
- **Triệu chứng:** `_wait_for_feed`, `OPEN_TIKTOK`, `ACCOUNT_SWITCHER` liên tục báo không tìm thấy root surface, dumpsys window báo `mCurrentFocus` là `com.github.uiautomator`.
- **Giải pháp chuẩn:**
  - Trong `bring_to_foreground`, `_wait_for_feed`, `OPEN_TIKTOK`, `ACCOUNT_SWITCHER`: Bổ sung kiểm tra package foreground `com.github.uiautomator` hoặc `io.appium.uiautomator2.server`.
  - Tự động chạy `adb shell am force-stop com.github.uiautomator` và `am force-stop io.appium.uiautomator2.server` để nhường foreground cho TikTok mà không làm chết daemon `atx-agent` ngầm.
  - Mang TikTok trở lại foreground qua `am start -n com.ss.android.ugc.trill/com.ss.android.ugc.aweme.splash.SplashActivity`.

---

## 3. CapCut Template Preview & Creation Hub Auto-Dismissal
- **Hiện tượng:** Khi bấm nút `+` (Quay/Tải lên) hoặc sau khi đăng video, TikTok mở vào màn hình xem trước Mẫu CapCut hoặc Creation Hub:
  - **Template Preview:** Nút CTA "Thử mẫu này" / "Thử mẫu trong CapCut" / "Use this template", nút quay lại `<` (id `:id/bq3`) ở góc trên bên trái.
  - **Creation Hub:** Các công cụ "Video mới", "Mẫu", "AutoCut", "Trình chỉnh sửa ảnh", "Phụ đề", nút đóng `X` (id `:id/h32` / content-desc="Đóng").
- **Giải pháp chuẩn trong `state_machine.py`:**
  - `_is_capcut_template_surface(xml_text)`:
    - Loại trừ media picker thật (`_is_verified_media_picker_xml`).
    - Nhận diện template CTA markers (`thử mẫu này`, `use this template`, resource-id `use_template`).
    - Nhận diện hub tool markers (2+ công cụ như `autocut`, `phụ đề`, `tách nền`, `trình chỉnh sửa ảnh` kèm hub title `mẫu`, `templates`, `bài hát lan truyền`, `xu hướng` hoặc nav id `:id/bq3`, `:id/h32`).
  - `_dismiss_capcut_template_surface(adapter, xml_text)`:
    - Vòng lặp tối đa 4 lần.
    - Tìm và tap nút back/close ở góc trên (`top <= 400`, id `:id/bq3`, `:id/h32`, `content-desc="Đóng"` / `"Quay lại"`).
    - Fallback gửi semantic `adapter.back()`.
    - Fail-closed: trả về `False` nếu recapture lỗi hoặc surface vẫn còn sau 4 lần thử.
  - Tích hợp tại tất cả các điểm kiểm tra UI: `_wait_for_feed`, `_handle_account_switcher`, `_handle_open_tiktok`, `_handle_video_pick`, `_handle_post`, `_dismiss_core_benign_popup`.
