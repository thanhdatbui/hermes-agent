# ATX Stub "Already Started" Pitfall & Fast Swipe Launcher Escalation Collision (2026-08-24)

## 1. Hiện tượng & Triệu chứng
- Máy farm (S7/Android 7) đang chạy `multi-machine-feed-session` / `feed_swipe_smoke` thì dừng phiên đột ngột:
  `🚨 [MÁY XX] DỪNG PHIÊN • Lý do: capture-invalid: ATX_SESSION_UNAVAILABLE artifact=.../sponsored_check`.
- Kiểm tra thiết bị thực tế: TikTok vẫn đang mở ở feed For You bình thường, hoặc vừa văng Launcher nhưng app chưa chết.

## 2. Phân tích nguyên nhân kép (Dual Root Cause)

### A. Lỗ hổng trong `reset_atx_agent` (`automation-core`):
1. Tiến trình UiAutomator stub (`com.github.uiautomator`) bị Android kernel dọn dẹp hoặc crash ngầm.
2. `atx-agent` daemon vẫn còn process trong RAM và giữ cache trạng thái đã start.
3. Khi `reset_atx_agent` gọi `atx-agent curl -X POST http://127.0.0.1:7912/uiautomator`, atx-agent trả về:
   `2026/08/24 22:30:44 curl.go:116: Already started <nil>`
   nhưng **thực tế không hề spawn lại process `com.github.uiautomator`**.
4. Hậu quả: Dù vòng lặp retry 3 lần và gọi `reset_atx_agent`, stub vẫn vắng bóng trong `ps -A` (`ATX_SESSION_STUB_NOT_RUNNING`) $\rightarrow$ raise `UIDumpError("ATX_SESSION_UNAVAILABLE")`.

**Khắc phục chuẩn:**
Trong `reset_atx_agent`, sau khi start `atx-agent server -d`, bắt buộc trigger stub qua ADB monkey:
`adb shell "monkey -p com.github.uiautomator 1"`
thay vì chỉ dựa vào endpoint HTTP `/uiautomator`.

### B. Thứ tự thực thi khi Fast Swipe mất focus (`tiktok-luot nuoi acc`):
1. Chu kỳ **Fast Swipe** phát hiện `focused_package == com.sec.android.app.launcher` $\rightarrow$ log cảnh báo và escalate xuống nhánh **Deep Inspect**.
2. Tại Deep Inspect, code kiểm tra ngay:
   `if is_feed_session and _sponsored_present(ctx):`
   Hàm `_sponsored_present` gọi `_capture_xml_text(ctx, "sponsored_check")` để dump XML.
3. Vì thiết bị đang ở Launcher và stub đang chập chờn, lệnh dump XML ném `ATX_SESSION_UNAVAILABLE` và dừng toàn bộ phiên trước khi flow kịp chạy tới `_recover_post_swipe_launcher_focus`.

**Khắc phục chuẩn:**
1. `_sponsored_present(ctx)` bắt buộc bọc try-except fail-safe (nếu dump XML thất bại thì return `False` thay vì để exception phá hỏng cả phiên).
2. Khi Fast Swipe phát hiện focus loss về Launcher, phải ưu tiên relaunch/re-focus TikTok trước khi thực hiện các bước parse XML của video feed.
