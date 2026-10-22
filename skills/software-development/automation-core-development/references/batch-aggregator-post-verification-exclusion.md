# Batch Aggregator: Post Verification Timeout vs Challenge Detection

## Context
In `automation-core/src/automation_core/batch_aggregator.py`, batch runs across the fleet are evaluated for systemic and critical errors.
The aggregation logic checks:
```python
CHALLENGE_KEYWORDS: tuple[str, ...] = (
    "verification",
    "manual_challenge",
    "checkpoint",
    "captcha",
    "xác minh",
    "xac minh",
)
```

## Problem (Keyword Collision False Positive)
When TikTok upload workflows in consumer repos (`Tiktok-video` / `scripts.tiktok_workflow.state_machine`) perform post-verification via `PostVerifier.verify_post()` with a 120-second timeout, if TikTok or the network is slow, it emits:
```text
UploadHook: 2026-10-22 06:44:35,695 [ERROR] scripts.tiktok_workflow.state_machine: Post verification inconclusive/failed: TIMEOUT
```
Because `"verification"` is in `CHALLENGE_KEYWORDS`, `batch_aggregator.py` matches `post verification` and marks the failure as a `challenge_failure`.
This leads to false-positive alerts on Telegram:
`⚠️ [CẢNH BÁO XÁC MINH / CAPTCHA TẠM THỜI]: Phát hiện N máy gặp captcha/xác minh (chưa mất phiên)`
even when the devices are clean, at Home screen, and completely free of any Captcha or verification challenges.

## Pitfall: Blunt Exclusion List vs Prefix Stripping Architecture
Khi khắc phục va chạm từ khóa `"verification"`, **CẤM** chỉ thêm `"post verification"` vào tuple `CHALLENGE_EXCLUSIONS`.
- **Lý do (Lỗ hổng mù Adversarial Blind-spot):** Nếu dùng `any(ex in message for ex in CHALLENGE_EXCLUSIONS)`, bất kỳ thông báo lỗi thực tế nào chứa `"post verification"` kèm theo Captcha (ví dụ: `"post verification inconclusive: captcha required"`) sẽ bị loại trừ toàn bộ, gây che giấu sự cố bảo mật nghiêm trọng.
- **Giải pháp chuẩn kiến trúc:**
  1. Định nghĩa `_CHALLENGE_STRIP_PREFIXES` và hàm `_strip_challenge_prefixes(text)` dùng `str.replace(prefix, "")` để gọt bỏ các tiền tố vô hại (`"profile verification"`, `"post verification"`).
  2. Từ khóa nhạy cảm còn lại trong chuỗi (`captcha`, `checkpoint`, `manual_challenge`, `xác minh`) vẫn được phát hiện bình thường.
  3. Bổ sung hàm `_is_challenge_excluded(machine)` có debug telemetry log có cấu trúc:
     `logger.debug("[CHALLENGE_EXCLUSION] event=challenge_excluded serial=%s matched_exclusion=%r error_message=%r", ...)`
     tương tự như `_is_session_lost_excluded`.

## 3-Layer Testing Discipline (Bắt buộc cho Logic Phân Loại An Toàn Farm)
Mọi thay đổi trên bộ lọc Challenge/Session-lost BẮT BUỘC phải có đủ 3 lớp test trong `tests/test_batch_aggregator.py`:
1. **Suppression Test (Triệt tiêu báo động giả):**
   `"UploadHook: Post verification inconclusive/failed: TIMEOUT"` -> `challenge_count == 0`, `should_alert is False`.
2. **Negative Test (Không triệt tiêu challenge thật):**
   `"Verification challenge required: please complete the CAPTCHA"` -> `challenge_count == 1`, `should_alert is True`.
3. **Adversarial Hybrid Test (Tiền tố kết hợp từ khóa thật):**
   `"post verification inconclusive: captcha required"` -> `challenge_count == 1`.
4. **Telemetry Audit Test:**
   Dùng pytest fixture `caplog` ở level `DEBUG` kiểm chứng log `[CHALLENGE_EXCLUSION]` được ghi nhận đúng khi các exclusion hợp lệ kích hoạt.

## Phân Biệt Sol Review vs Sol Repair
- **Sol Review (`closeout_gate.py`):** Cổng thẩm định độc lập bắt buộc ở cuối phiên (gọi qua model `claude-sonnet` hoặc endpoint `:20129`). Chấm điểm nghiêm ngặt từ 0-100, chỉ cho phép commit/push khi `APPROVED >= 85`.
- **Sol Repair (`sol_repair.py`):** First Responder độc quyền khi `closeout_gate.py` trả về `REJECTED` (Strike 1 & 2). Tự động phân tích key findings & judge notes để tạo proposal patch O(1) giải quyết đúng điểm reviewer yêu cầu. Coordinator áp dụng proposal của Sol Repair và kiểm tra lại focused test trước khi rerun gate.
