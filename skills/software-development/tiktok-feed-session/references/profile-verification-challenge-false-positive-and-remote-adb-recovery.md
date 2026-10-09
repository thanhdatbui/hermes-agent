# Profile Verification False Challenge Alert & Remote ADB Transport Recovery

## 1. False Positive: "CẢNH BÁO XÁC MINH / CAPTCHA TẠM THỜI" do Profile Verification
- **Triệu chứng:** Batch Alert từ `batch_aggregator.py` báo:
  `⚠️ [CẢNH BÁO XÁC MINH / CAPTCHA TẠM THỜI]: Phát hiện 1 máy gặp captcha/xác minh (chưa mất phiên):`
  `• Máy M239: profile verification navigation-failed: focused package unavailable`
- **Thực tế hiện trường:** Máy đã hoàn thành 100% video (ví dụ 18/18 swipes), không hề bị văng nick hay dính captcha. Bước fail là `verify_profile` hậu swipe (chuyển sang tab Hồ sơ để ghi nhận follower).
- **Nguyên nhân cốt lõi trong `batch_aggregator.py`:**
  Bộ lọc `CHALLENGE_KEYWORDS` có chứa chuỗi con `"verification"`. Khi chuỗi lỗi kỹ thuật nội bộ của runner là `profile verification navigation-failed...`, hàm phân loại match nhầm từ `"verification"` và kết luận nhầm là lỗi Captcha/Challenge.
- **Xử lý chuẩn:**
  1. Loại trừ chuỗi `"profile verification"` trước khi match `CHALLENGE_KEYWORDS` (chỉ coi là challenge nếu có từ khóa thực sự như `"captcha"`, `"manual_challenge"`, `"checkpoint"`).
  2. Bổ sung cơ chế fallback cho `canary_machine` trong `format_alert_message`: khi `systemic_signatures` rỗng (0 cụm lỗi hệ thống), tự lấy serial máy lỗi đầu tiên trong `challenge_failures`, `session_lost_failures` hoặc `auth_failures` thay vì in `N/A`.

## 2. Remote ADB Transport Wedged Socket Recovery
- **Triệu chứng:** Khi chạy `python D:/Taadaa/tools/inspect_machine.py <N>` trên máy Admin Remote (`192.168.110.119:5037`), lệnh ADB bị treo timeout (10s–15s), `get_focused_activity` trả về None / `focused package unavailable`.
- **CẤM:** Tuyệt đối cấm reboot phone bừa bãi hoặc kill adb server trên host remote làm ảnh hưởng 79 máy khác đang chạy.
- **Lệnh giải cứu O(1) duy nhất:**
  `adb -H 192.168.110.119 -P 5037 -s <serial> reconnect`
  Lệnh này reset riêng socket transport của thiết bị mục tiêu, ngay lập tức khôi phục phản hồi ADB mà không làm gián đoạn các thiết bị khác trên fleet.
