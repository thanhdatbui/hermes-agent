# Batch Aggregator: Post Verification Timeout False Positive Triage (2026-10-22)

## 1. Hiện tượng & Triệu chứng
Watchdog hoặc runner gửi cảnh báo Telegram:
```text
🚨 [BATCH ALERT: LỖI HỆ THỐNG] PHÁT HIỆN LỖI LAN RỘNG - 【FARM ADMIN - MÁY 201-280】
⚠️ [CẢNH BÁO XÁC MINH / CAPTCHA TẠM THỜI]: Phát hiện N máy gặp captcha/xác minh (chưa mất phiên):
   • Máy M222: UploadHook: 2026-10-22 06:44:35,695 [ERROR] scripts.tiktok_workflow.state_machine: Post verification inconclusive/failed: TIMEOUT
```

## 2. Nguyên nhân gốc (Root Cause)
1. **Cơ chế UploadHook**:
   - Khi chạy ca 2 có bật upload (`--allow-upload-hook`), sau khi bấm nút Post, state machine vào state `VERIFY_POST` (`PostVerifier.verify_post()` với timeout 120s).
   - Nếu mạng lag hoặc TikTok render/index video chậm quá 120s không thấy video xuất hiện trên profile grid, script ghi log:
     `Post verification inconclusive/failed: TIMEOUT`.
   - Script tự động ngắt an toàn (`_recheck_ambiguous_post()`) để tránh post đè video rác, sau đó đóng TikTok về Launcher.
2. **Bẫy từ khóa trong `batch_aggregator.py`**:
   - `batch_aggregator.py` định nghĩa:
     ```python
     CHALLENGE_KEYWORDS: tuple[str, ...] = (
         "verification", "manual_challenge", "checkpoint", "captcha", "xác minh", "xac minh"
     )
     ```
   - Hàm lọc `challenge_failures` quét chuỗi lỗi tìm `kw in (error_message).lower()`.
   - Do chuỗi lỗi chứa `"post verification"`, nó bắt dính chữ `"verification"` và gán nhầm máy vào nhóm `challenge_failures` (`[CẢNH BÁO XÁC MINH / CAPTCHA TẠM THỜI]`).
   - `CHALLENGE_EXCLUSIONS` có loại trừ `"profile verification"` nhưng thiếu `"post verification"`.

## 3. Quy trình Triage Hiện trường O(1)
1. **Kiểm tra trạng thái thiết bị**:
   - Chạy `python D:/Taadaa/tools/inspect_machine.py <M>`
   - Kiểm tra `Current Focus`: Nếu là `com.sec.android.app.launcher/...LauncherActivity` hoặc `mWakefulness=Asleep`, phiên trước đã đóng sạch.
2. **Kiểm tra Proxy**:
   - Test proxy tương ứng qua curl/HTTP request. Nếu proxy trả về IP sạch, mạng hoàn toàn bình thường.
3. **Phân loại**:
   - Xác định rõ đây là **FALSE POSITIVE** của watchdog cảnh báo Captcha do trùng từ khóa `"verification"`, không phải máy bị dính checkpoint hay Captcha thật.
   - Giải thích cho User: nói thẳng vào nguyên nhân kỹ thuật (watchdog bắt nhầm chữ, hiện trường sạch, thiết bị an toàn).
