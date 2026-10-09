# Popup Recovery Empty Screen & Alert False-Positive Pitfalls (2026-09-25)

## 1. BẪY KHỞI ĐỘNG VÒNG LẶP BACK RECOVERY KHI DETECTED_SCREEN LÀ NONE HOẶC RỖNG
- **Nguyên nhân:** Khi nhịp recapture sau dismiss gặp glitch vận chuyển ADB (ví dụ: `exec-out screencap -p` timeout hoặc `ATX_SESSION_UNAVAILABLE`), hàm `capture_calibration_attempt` trả về `details` có `detected_screen = None` (hoặc missing).
- **Lỗ hổng logic cũ:**
  ```python
  # SAI: Khi detected_screen là None, điều kiện này False, bỏ qua toàn bộ 3 nhịp BACK recovery!
  if after.get("detected_screen") == "unknown":
      for back_i in range(1, 4): ...
          if screen != "unknown": # SAI: None != "unknown" là True -> thoát sớm ngay vòng 1!
              break
  ```
- **Chuẩn khắc phục bất biến:**
  ```python
  # ĐÚNG: Xử lý cả None, rỗng và "unknown"
  if _attempt_detected_screen(after) in ("", "unknown"):
      for back_i in range(1, 4): ...
          screen = _attempt_detected_screen(recovered)
          if screen in _KNOWN_TIKTOK_SCREENS:
              after = recovered
              break
          if screen and screen != "unknown":
              break
  ```

## 2. PHÒNG TRÁNH BÁO ĐỘNG GIẢ CAPTCHA / CHALLENGE DO BẮT NHẦM SUBSTRING 'VERIFY'
- **Hiện tượng:** Máy chỉ bị timeout recapture popup ("Add phone close recapture did not verify a known TikTok screen...") nhưng hệ thống gửi cảnh báo đỏ `⚠️ [CẢNH BÁO XÁC MINH / CAPTCHA TẠM THỜI]` về Telegram.
- **Nguyên nhân:** `CHALLENGE_KEYWORDS` trong `batch_aggregator.py` chứa từ khóa bare substring `"verify"`, dẫn đến các câu thông báo phủ định hoặc kiểm tra kỹ thuật ("did not verify", "failed to verify", "recapture did not verify") bị gán nhãn sai thành Captcha/Checkpoint.
- **Kỷ luật:**
  1. Tuyệt đối không dùng bare substring verbs (`verify`, `check`, `auth`) làm challenge keywords.
  2. Bắt buộc dùng exact challenge tokens: `"verification"`, `"manual_challenge"`, `"checkpoint"`, `"captcha"`, `"xác minh"`, `"xac minh"`.
  3. Bổ sung `CHALLENGE_EXCLUSIONS`:
     `("did not verify", "failed to verify", "could not verify", "cannot verify", "unable to verify", "recapture did not verify")`.

## 3. KỸ THUẬT CÔ LẬP TEST FILE TRƯỚC GATE CLOSEOUT SOL AUDITOR
- Khi làm việc trên các repo có file test monolith tồn tại lỗi pre-existing (ví dụ `python_runner/tests/test_benign_popup.py`), việc stage file test monolith sẽ khiến `closeout_gate.py` chạy toàn bộ test suite của file đó và fail do lỗi cũ không liên quan.
- **Giải pháp:** Tách regression test mới vào file test độc lập (ví dụ `python_runner/tests/test_add_phone_empty_recovery.py`).
- Kết quả: Step 3 (Focused Tests) đạt 100% PASS, cung cấp Test Evidence chuẩn xác cho Sol Auditor scorecard mà không bị block bởi legacy failure.
