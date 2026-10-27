# Khắc Phục Bẫy INVALID_MEDIA_FILE Do Stale Receipt Cũ & Ép Buộc Soi Mắt Thật Sự

## 1. Bản Chất Yêu Cầu Của User: "Ép Agent Phải Tự Đọc Ảnh Xong Mới Được Suy Luận Trả Lời"
- Khi người dùng phàn nàn Gate bị over-engineered, phản xạ sai lầm của Agent là hạ cấp Gate thành kiểm tra tầm thường (`os.path.isfile` và `size > 0`). Người dùng đã lập tức chấn chỉnh:
  > *"Sửa guard... Nhưng tóm lại ép agent phải tự đọc ảnh xong ms đc suy luận trả lời"*
- **Nguyên tắc bất biến:**
  1. CẤM buông lỏng Gate thành kiểm tra file rỗng. Bắt buộc Agent phải thực sự soi mắt đọc ảnh (`browser_vision` hoặc `run_winrt_ocr.py`) thì mới có bằng chứng để suy luận và gửi `MEDIA:`.
  2. CẤM báo cáo mồm hoàn thành UI nếu không có ảnh chứng minh (`MISSING_MEDIA_EVIDENCE`).
  3. CẤM gửi ảnh mù nếu ảnh đó chưa được Agent soi mắt trong phiên hiện tại (`NO_RECEIPT`).
  4. CẤM dùng OCR text để bảo lãnh cho visual claims/avatar proposals (`UNVERIFIED_BY_VISION`).

## 2. Lỗi Over-Engineering & Cách Khắc Phục Triệt Để
1. **Bẫy So Sánh Hash Với Receipt Cũ Quá Hạn (Stale Receipt Tamper Trap):**
   - Các đường dẫn ảnh chụp màn hình tái sử dụng (như `D:/OneDrive/TaadaaData/admin_screen.png`, `screen.png`) từng có receipt được ký từ nhiều ngày trước trong `vision_receipts.jsonl`.
   - Hàm `_media_file_verdict` ban đầu gọi `_latest_signed_receipt` mà **không kiểm tra TTL**. Khi file được chụp mới hôm nay, SHA-256 mới lệch với receipt cũ từ 2 ngày trước, Gate ngộ nhận file bị "tampered" và chặn gửi tin nhắn với mã `INVALID_MEDIA_FILE`.
   - **Cách sửa chuẩn:** Trong `_media_file_verdict`, chỉ kiểm tra hash tamper đối với receipt **còn trong khung TTL (`0 <= age <= DEFAULT_TTL_SECONDS`)**:
     ```python
     signed = _latest_signed_receipt(image_path, receipt_store)
     if signed is not None:
         now = time.time()
         age = now - float(signed.get("timestamp", 0))
         if 0 <= age <= ttl_seconds:
             if not hmac.compare_digest(str(signed.get("sha256", "")), actual_sha256):
                 return _verdict("INVALID_MEDIA_FILE", f"MEDIA file SHA-256 differs: {image_path}", [image_path])
     ```
     Nếu receipt đã hết hạn (> 300s), nó không đại diện cho trạng thái hiện tại; Gate trả về `NO_RECEIPT` để ép Agent soi mắt lại ảnh mới, tuyệt đối không vu khống file là "tampered".

2. **Tự Động Cấp Receipt Khi Agent Đã Soi Mắt Bằng `browser_vision`:**
   - Agent tuân thủ Invariant bằng cách gọi `browser_navigate("file:///...")` và `browser_vision(...)`, nhưng Gate lại yêu cầu phải chạy script phụ `run_winrt_ocr.py` hoặc `--record-vision` thì mới có receipt.
   - **Cách sửa chuẩn:** Hàm `transform_llm_output_check` tích hợp `_extract_seen_images_from_tool_calls(tool_calls)`. Khi Agent đã gọi `browser_vision` trên file ảnh trong lượt, Gate tự động ghi nhận vé kiểm chứng `tool_called="browser_vision"`, `reason_code="SEEN_BY_NATIVE_VISION"` cho file đó.

3. **Dung Sai Mtime Trên Windows NTFS (`MTIME_TOLERANCE = 2.0s`):**
   - Mức dung sai cũ `1e-6` microsecond gây lỗi giả khi file được copy qua SMB/OneDrive dù SHA-256 đã khớp tuyệt đối 100%. Nâng lên 2.0s để triệt tiêu false-positive do làm tròn float trên Windows.

4. **Triệt Tiêu Egress Prompt Leak:**
   - Khi Gate quật ngã tin nhắn, mã lỗi chỉ dùng nội bộ trong agent loop. Tầng egress cấm xuất bản nguyên khối `[CONTRADICTION_GATE_TRIGGERED]` ra màn hình chat Telegram của người dùng.

## 3. Quy Trình Kiểm Thử Hồi Quy (Regression Testing)
Mọi chỉnh sửa trên `guard_media_vision_gate.py` bắt buộc phải chạy bộ test toàn diện:
```bash
pytest D:/Taadaa/tools/tests/test_guard_media_vision_gate.py -q
```
Bộ test bắt buộc bao phủ:
- `test_expired_receipt_does_not_falsely_flag_tampered_when_file_rewritten`: File chụp đè lên receipt cũ > TTL phải trả về `NO_RECEIPT`, cấm trả về `INVALID_MEDIA_FILE`.
- `test_tool_calls_browser_vision_auto_registers_receipt`: `tool_calls` có `browser_vision` trên file cục bộ phải tự động cấp vé và PASS tin nhắn `MEDIA:`.
- Toàn bộ 100 tests phải PASS 100% (Green).
