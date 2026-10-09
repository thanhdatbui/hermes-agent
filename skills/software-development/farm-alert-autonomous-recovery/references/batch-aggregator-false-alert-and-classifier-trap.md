# Batch Aggregator & Classifier False Alert Triage (Fix Lỗi Báo Ngu)

## 1. P0 Cảnh Báo Mất Phiên / Văng Account: Profile Verification Navigation/Focus Failures Trap

### Hiện tượng & Bản chất
- Telegram bắn alert: `⚠️ [P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]: Phát hiện N máy dính lỗi login/mất phiên`
  kèm chi tiết: `profile verification navigation-failed: TikTok focus lost after navigation tap: unknown` (hoặc `focused package unavailable`).
- **Nguyên nhân gốc rễ trong `batch_aggregator.py`**:
  1. `error_type` của runner là `login-gms-verification` (chứa substring `"login"`).
  2. `SESSION_LOST_KEYWORDS` chứa `"login"`. Khi bộ lọc kiểm tra:
     `any(kw in (m.error_type or "").lower() for kw in SESSION_LOST_KEYWORDS)`
     -> Lỗi điều hướng chuyển activity xác minh hồ sơ (`profile verification`) bị bắt nhầm thành sự cố mất phiên nghiêm trọng.
  3. Trên thực tế: máy đã lướt feed hoàn tất (ví dụ M224 chạy xong 21/21 swipes), tài khoản đang đăng nhập 100% bình thường (WinRT OCR thấy đủ 5 tab điều hướng và `@username`).

### Khắc phục chuẩn hóa trong `automation-core/src/automation_core/batch_aggregator.py`
1. **SESSION_LOST_EXCLUSIONS Gate**:
   Bổ sung bộ lọc loại trừ các lỗi điều hướng, chuyển trang và mất focus:
   ```python
   SESSION_LOST_EXCLUSIONS: tuple[str, ...] = (
       "profile verification",
       "navigation-failed",
       "navigation failed",
       "focus lost",
       "focused package unavailable",
       "failed to focus",
       "feed swipe",
       "swipe",
   )
   ```
2. **Khử trùng lặp `login-gms-verification`**:
   Khi `error_type == "login-gms-verification"`, không được dùng kiểm tra từ khóa `"login"` trên `error_type` để gán nhãn mất phiên; chỉ kiểm tra trên `error_message` thật sự (như `"logged out"`, `"require_login"`).
3. **Telemetry & Observability Gate**:
   Khi một lỗi bị loại khỏi `session_lost`, ghi log debug:
   ```python
   logger.debug("[SESSION_LOST_EXCLUSION] event=session_lost_excluded serial=%s reason=%s", m.serial, m.error_message or m.error_type)
   ```

---

## 2. Cảnh Báo Xác Minh / Captcha Tạm Thời: Long News/Video Caption With "xác minh"

### Hiện tượng & Bản chất
- Telegram bắn alert: `⚠️ [CẢNH BÁO XÁC MINH / CAPTCHA TẠM THỜI]: Phát hiện N máy gặp captcha/xác minh (chưa mất phiên)`
  kèm chi tiết: `verification marker detected` trên máy đang lướt feed bình thường (ví dụ M251).
- **Nguyên nhân gốc rễ trong `classifier.py` (`python_runner/core/classifier.py`)**:
  - `manual_challenge_terms` chứa cụm `"xác minh"`.
  - Khi máy lướt trúng một video phóng sự, bản tin tin tức dài hàng nghìn ký tự (như tin công an điều tra bạo hành trẻ em dài 2.364 ký tự), caption video chứa cụm *"Quá trình điều tra xác minh, Công an..."*.
  - Hàm `_is_manual_challenge_match` quét toàn bộ text trong XML. Nếu video không có đủ 3 feed controls chuẩn (ví dụ chỉ có avatar + follow marker do format video đặc thù), hàm sẽ gắn nhãn `manual-needed:verification`.

### Cạm bẫy khi sửa (Bẫy Sol Reviewer Closeout Gate < 85đ)
- **Bẫy 1 (Global length bypass `len(value) > 80: return False`)**:
  - Reviewer Sol Auditor đánh rớt (82/100 REJECTED) vì vi phạm an toàn: các màn hình challenge thật sự (`manual_challenge`, `kiểm tra bảo mật`) có thể đi kèm đoạn mô tả hướng dẫn dài > 80 ký tự. Bỏ qua toàn bộ sẽ gây **False Negative (lọt lưới challenge thật)**.
- **Bẫy 2 (Thiếu Telemetry Logging)**:
  - Bỏ qua keyword mà không phát log telemetry sẽ bị trừ điểm Observability (10/15đ).

### Giải pháp chuẩn hóa bền vững (Pass Gate >= 85/100)
1. **Phân tách từ khóa đặc hiệu (Explicit) vs từ khóa đời thường (Generic)**:
   - Các từ khóa đặc hiệu bảo mật cao (`"manual_challenge"`, `"kiểm tra bảo mật"`): **TUYỆT ĐỐI KHÔNG BYPASS**, kể cả khi chuỗi dài.
   - Chỉ từ khóa đời thường/phổ thông (`"xác minh"`): chỉ bypass khi độ dài `len(value) > 40` ký tự (bản chất là câu văn/đoạn văn dài thay vì nút bấm/tiêu đề challenge).
2. **Telemetry Log**:
   ```python
   if term.lower() in ("xác minh", "x\u00c3\u00a1c minh") and len(value) > 40:
       logger.debug(
           "[CLASSIFIER_CHALLENGE_BYPASS] event=challenge_keyword_bypassed reason=generic_xac_minh_in_long_text length=%d prefix=%s",
           len(value),
           value[:40],
       )
       continue
   ```
3. **Bộ test hồi quy đa diện**:
   - Test short verification (`"Vui lòng xác minh"`) -> vẫn phải là `manual-needed:verification`.
   - Test long news caption (`"Quá trình điều tra xác minh..."`) -> phân loại an toàn về `home` hoặc `for-you`.
   - Test long explicit marker (`"manual_challenge"` hoặc `"kiểm tra bảo mật"` trong đoạn văn dài) -> vẫn phải giữ `manual-needed:verification`.
   - Test assert log telemetry debug được phát ra khi bypass.

---

## 3. P0 Cảnh Báo Mất Phiên: Switcher Open Failure Trap (`SWITCHER_NOT_CONFIRMED` / `PROFILE_ROOT_NOT_CONFIRMED`)

### Hiện tượng & Bản chất
- Telegram bắn alert: `⚠️ [P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]: Phát hiện N máy dính lỗi login/mất phiên`
  kèm chi tiết: `UploadHook: [ACCOUNT_SWITCHER_FAILED] open_switcher failed: SWITCHER_NOT_CONFIRMED: switcher markers were not confirmed. Cần MANUAL_REVIEW: kiểm tra TikTok đã login chưa...` (hoặc `open_profile_root failed: PROFILE_ROOT_NOT_CONFIRMED`).
- **Căn nguyên**:
  1. Trong runner (`state_machine.py`), hàm `_fail_account_switcher()` tự động gắn thêm chuỗi hướng dẫn xử lý thủ công:
     `f"[ACCOUNT_SWITCHER_FAILED] {err_msg}. Cần MANUAL_REVIEW: kiểm tra TikTok đã login chưa, dismiss popup/onboarding thủ công rồi retry."`
  2. Chuỗi này chứa từ khóa `"login"`, vô tình khớp với `SESSION_LOST_KEYWORDS` trong `batch_aggregator.py`.
  3. Lỗi mở switcher (`SWITCHER_NOT_CONFIRMED`) thực chất là lỗi tương tác giao diện (ví dụ màn hình profile bị popup milestone che phủ hoặc animation chậm), tài khoản vẫn đang đăng nhập hoàn toàn bình thường trên Profile (chứng minh qua WinRT OCR trên `account-switcher-profile.png`).
  4. Nếu `SESSION_LOST_EXCLUSIONS` không loại trừ `switcher_not_confirmed`, `switcher markers were not confirmed`, `open_switcher`, aggregator sẽ tính nhầm thành sự cố mất phiên và bắn cảnh báo đỏ P0 sai sự thật dù số cụm lỗi hệ thống bằng 0.

### Khắc phục chuẩn hóa trong `automation-core/src/automation_core/batch_aggregator.py`
1. Bổ sung các cụm từ switcher vào `SESSION_LOST_EXCLUSIONS`:
   ```python
   SESSION_LOST_EXCLUSIONS: tuple[str, ...] = (
       ...
       "profile_root_not_confirmed",
       "profile root was not confirmed",
       "open_profile_root",
       "switcher_not_confirmed",
       "switcher markers were not confirmed",
       "open_switcher",
   )
   ```
2. **Unit Test & Telemetry Gate**:
   - Viết test trong `tests/test_batch_aggregator.py` giả lập `MachineResult` với lỗi `[ACCOUNT_SWITCHER_FAILED] open_switcher failed: SWITCHER_NOT_CONFIRMED...`.
   - Assert `report.session_lost_count == 0`, `report.should_alert is False`.
   - Assert telemetry log debug `[SESSION_LOST_EXCLUSION] event=session_lost_excluded` phát ra ghi nhận serial và reason.
3. **Thực tế Hiện Trường & Nghiệm Thu Closeout Gate (2026-10-02)**:
   - *Hiện trường thực tế (M18 & M74)*: WinRT OCR trên ảnh `account-switcher-profile.png` xác nhận tài khoản vẫn đăng nhập 100% trên Profile (M74 nick `@angan6670` bị popup milestone *"Tổng Số Lượt thích"* che phủ; M18 nick `@huy010822` active). Không có hiện tượng văng phiên.
   - *Commit Audit Trail*: `[L2-surgery] fix(batch_aggregator): exclude switcher_not_confirmed from session-lost P0 alerts with telemetry` (numstat 19 dòng <= 30 dòng).
   - *Sol Auditor Reviewer*: Đạt 86/100 APPROVED (`closeout_gate.py` exit code 0).

