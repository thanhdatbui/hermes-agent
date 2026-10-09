# Canary Parity Row Resolution & Event Space Overlay Recovery (07/09/2026)

## 1. Sự cố Farm Alert Hardcode `-Row 1` & Lệch Nick Ca Nuôi (User Correction 07/09/2026)

### Triệu chứng & Sai lầm
- Watchdog cảnh báo máy lỗi tạo mẫu tin alert với bước B4 hardcode cứng tham số `-Row 1`:
  `run-feed-session.ps1 -Machines <M> -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run`
- Metadata alert và agent báo cáo mặc định nick của Row 1 (ví dụ `jxlmiaxr6gt`).
- **Phản ứng của User**: *"ủa sao cái này là row 1 đc nhỉ, mà cái farrm alert thông báo cũng ngu nữa làm gì phải row 1. Làm luôn. Báo đúng nick"*.

### Phân tích Root Cause
- Farm vận hành theo lịch Parity Lanes (Ngày chẵn / Ngày lẻ) chia 3 ca/ngày:
  - **Ngày Lẻ**: Ca 1 (06:00) -> Row 1 | Ca 2 (12:30) -> Row 3 | Ca 3 (19:00) -> Row 5.
  - **Ngày Chẵn**: Ca 1 (06:00) -> Row 2 | Ca 2 (12:30) -> Row 4 | Ca 3 (19:00) -> Row 6.
- Sự cố xảy ra lúc 14:39 ngày 07/09 (ngày lẻ) -> Thực tế là **Ca 2 (Row 3)**.
- Nếu chạy canary test bằng `-Row 1`:
  + Script sẽ switch sang account của Row 1 thay vì test nick đang chạy bị dừng.
  + Báo cáo sai nick, làm mất tính xác thực của canary test trên tài khoản thực tế.

### Quy tắc Bắt buộc cho Coordinator & Worker
1. **Tuyệt đối không chạy mù theo `-Row 1` của template alert**:
   - Coordinator / Worker khi tiếp nhận alert BẮT BUỘC kiểm tra timestamp sự cố và lịch Parity để xác định chính xác số Row của ca đang chạy:
     ```python
     # Xác định ca và row từ timestamp (giờ Việt Nam GMT+7)
     if day % 2 != 0:  # Ngày lẻ
         row = 1 if hour < 12 else (3 if hour < 18 else 5)
     else:             # Ngày chẵn
         row = 2 if hour < 12 else (4 if hour < 18 else 6)
     ```
2. **Đối soát chính xác Nick từ Safe Workbook**:
   - Đọc `D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx` theo `(Máy, Row)` để lấy đúng username TikTok.
3. **Chạy Canary đúng Row**:
   - Luôn truyền đúng `-Row <K>` của ca đó vào script `run-feed-session.ps1`.
   - Báo cáo rõ: Máy M, Ca C (Row K), Nick `@username` đã test thành công.

---

## 2. Xử lý Overlay "Không gian sự kiện" (Event Space Ad Overlay)

### Hiện trường & Triệu chứng
- Alert: `sponsored/ad feedback overlay requires manual review`.
- Màn hình thiết bị kẹt tại giao diện **"Không gian sự kiện"**:
  - Top bar có nút mũi tên quay lại (`←`).
  - Danh sách thẻ sự kiện LIVE ("MEGALIVE MỸ PHẨM...", "SIÊU SALE NGÀY ĐÔI...", các nút "Đăng ký").
  - Màn hình này là một subpage/web-view độc lập được kích hoạt từ quảng cáo video in-feed.
  - Thao tác swipe up thông thường của runner feed không thoát được trang này.

### Giải pháp Code (Áp dụng tại `python_runner`)
1. **File `flows/benign_popup.py`**:
   - Thêm detector:
     ```python
     def detect_event_space_overlay(xml_content: str | None = None, ocr_text: str | None = None) -> bool:
         markers = [
             "Không gian sự kiện",
             "Sự kiện LIVE",
             "Khong gian su kien",
             "Su kien LIVE",
         ]
         text_data = (xml_content or "") + " " + (ocr_text or "")
         return any(m in text_data for m in markers)
     ```
   - Thêm dismiss handler:
     ```python
     def dismiss_event_space_overlay(ctx: Any) -> PopupDismissResult:
         before = {"screen": "event_space_overlay"}
         send_device_back_key(ctx)
         time.sleep(1.0)
         return PopupDismissResult(
             dismissed=True,
             reason="dismissed_event_space_overlay",
             before_attempt=before,
             popup_closed=True,
         )
     ```
2. **File `flows/benign_popup_registry.py`**:
   - Đăng ký handler vào registry với priority 79 (ngang hàng `live_campaign_overlay`):
     ```python
     register_popup_handler(RegistryEntry(
         "event_space_overlay",
         79,
         _detect_event_space_overlay,
         _dismiss_event_space_overlay,
         True,
         "manual",
     ))
     ```
   - Chạy test suite xác nhận: `pytest tests/test_benign_popup_registry.py` (159 passed).

---

## 3. Coordinator Patch Contract cho File Monolith (Anti-Loop Budget Rule)

- Các file core như `benign_popup.py` (>5300 dòng) và `benign_popup_registry.py` rất lớn.
- Nếu Coordinator dispatch worker với goal chung chung ("Hãy đọc và sửa..."), worker sẽ đọc nhiều file, nhanh chóng chạm ngưỡng budget (35 tool calls) và dừng lại trước khi kịp áp dụng code và chạy canary.
- **Quy tắc Patch Contract**:
  - Coordinator phải phân tích cấu trúc, chỉ định chính xác tên hàm, signature, marker, và file đích.
  - Hạn chế worker đọc lan man: yêu cầu worker ghi patch trong 2 tool call đầu tiên, sau đó kích hoạt lệnh canary ngay.
