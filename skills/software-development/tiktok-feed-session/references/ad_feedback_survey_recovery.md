# Ad Feedback Survey Benign Popup Recovery (TikTok Feed Session)

## 1. Tình Huống & Dấu Hiệu Lỗi
- **Màn hình kẹt**: Overlay khảo sát quảng cáo in-feed hiển thị câu hỏi: *"Bạn có quan tâm đến quảng cáo này không?"* / *"Are you interested in this ad?"* với các lựa chọn nút No/Yes hoặc Không/Có.
- **Log lỗi nhận diện**:
  ```text
  popup is not in the shared TikTok allowlist; manual review required; swipe recovery (2 swipes) still stuck
  ```
- **Hiện tượng**: Bị core allowlist từ chối, rơi vào trạng thái `manual-needed:popup`, khiến luồng lướt video bị đình trệ.

## 2. Nguyên Nhân Gốc (Root Cause)
1. Trong `automation-core/src/automation_core/tiktok/benign_popup.py`:
   - Hàm `detect_sponsored_ad_feedback_overlay` kiểm tra quá khắt khe khi yêu cầu đủ cả 4 markers đồng thời:
     - `sponsored_or_ad_marker` ("Được tài trợ", "Sponsored", "quảng cáo", "ad")
     - `feedback_question` ("Bạn có quan tâm đến quảng...", "Are you interested in this ad")
     - `yes_button_present` ("Yes", "Có")
     - `no_button` ("No", "Không")
   - Khi video ad không có nhãn "Được tài trợ" độc lập hoặc text nút có khoảng trắng/ký tự đặc biệt, matcher của core thất bại.
2. Hệ thống fallback swipe recovery ở cấp độ smoke test từ chối bypass nếu màn hình vẫn bị phân loại là unhandled popup.

## 3. Quy Trình Khắc Phục Chuẩn (B3 Patch Script)
Thực hiện thêm handler chuyên biệt tại `D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/benign_popup_registry.py` (Registry-first dispatch):

### A. Detector:
```python
def _detect_ad_feedback_survey(xml_content: str = "", ocr_text: str = "") -> bool:
    combined = ((xml_content or "") + " " + (ocr_text or "")).lower()
    ad_survey_markers = (
        "bạn có quan tâm đến quảng",
        "quan tâm đến quảng cáo",
        "interested in this ad",
        "are you interested in this ad",
    )
    return any(marker in combined for marker in ad_survey_markers)
```

### B. Dismisser:
- **Chiến lược 1 (Tap No / Dismiss)**: Tìm node có text hoặc content-desc tương ứng với "Không", "No" hoặc nút đóng `✕` trong bounds của dialog để click.
- **Chiến lược 2 (Bounded Swipe Up qua Video Ad)**: Vì khảo sát gắn liền với video quảng cáo hiện tại, nếu không tìm thấy nút hoặc tap không thành công, gọi swipe up (`_FULLSCREEN_SHOP_AD_SWIPE_COMMAND`) qua video kế tiếp.

### C. Đăng ký Handler:
```python
register_popup_handler(
    RegistryEntry(
        "tiktok_ad_feedback_survey",
        75,  # Priority cao hơn core fallback
        _detect_ad_feedback_survey,
        _dismiss_ad_feedback_survey,
        True,
        "manual",
    )
)
```

## 4. Nghiệm Thu Canary (B4 Canary Test)
Chạy lệnh kiểm thử canary trên đúng máy gặp lỗi:
```powershell
powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines <N> -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
```

## 5. Cảnh Báo Điều Tra (Pitfalls)
- **Tuyệt đối không quét đĩa**: CẤM dùng `os.walk` hoặc `glob(recursive=True)` trên thư mục `D:/Taadaa` hoặc `.ai-runs`. Thư mục này chứa hàng triệu artifacts sẽ gây timeout 900s và làm cạn kiệt tool-call limit.
- Chỉ mở đúng file đích đã biết: `flows/benign_popup_registry.py`, `flows/benign_popup.py`.
