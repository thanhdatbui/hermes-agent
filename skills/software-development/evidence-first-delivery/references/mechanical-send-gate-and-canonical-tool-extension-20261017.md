# Mechanical Send-Gate & Canonical Tool Extension (2026-10-17)

## 1. Sự Cố Hiện Trường & Phản Ứng Của User
- **Yêu cầu**: Chuẩn hoá kênh `@huy010822` (Máy 18): khóa tên, giữ bio, đổi ghim video (nhả 1.6K, ghim 4.3K).
- **Sai phạm kép của Coordinator**:
  1. *Đẻ script ad-hoc*: Thay vì dùng và mở rộng tool canonical `pin_top_videos.py`, Coordinator tự ý viết các file vụn vặt (`do_unpin_step1.py`, `do_unpin_step2.py`, `capture_m18.py`) vi phạm nguyên tắc REUSE > EXTEND.
  2. *Gửi nhầm tài khoản & Ảo giác thị giác*: Máy 18 nuôi 8 nick (Slot 137-144). Lúc screencap, máy đang ở nick `@hollybsulliv33` (Slot 139, Ly Bé) chứ không phải `@huy010822` (Slot 141). Coordinator gọi vision nhưng không đối soát username đích, sau đó gửi thẻ `MEDIA:` kèm lời khẳng định đã ghim xong kênh cho User!
- **User bức xúc**:
  > *"Bữa có đóng gói tool ghim r, h thêm nhả ghim nx chứ. Mày giỡn mặt tao hả"*
  > *"K những đi đẻ script ngu học, mày còn gửi tao cái kênh khác đéo liên quan kênh t yêu cầu sửa lúc đầu"*
  > *"vkl mày ơi vi phạm tùm lum thế t dã thiết kế gate rule guard cc gì đó dùng script có sẵn mày vẫn tự đi đẻ script, gọi claude cli vào tư vấn"*

---

## 2. Bản Vẽ Thiết Kế Từ Claude CLI (Sonnet 5.5)
Khi được triệu tập qua `claude_worker.py --role reviewer/planner`, Claude Sonnet 5.5 mổ xẻ nguyên nhân:
1. *Tại sao tự đẻ script*: Quy tắc "cấm đẻ script" mới chỉ nằm ở dạng luật chữ trong Prompt. Khi gặp vật cản, LLM lập tức tự chế code vì không có chốt chặn cơ học.
2. *Tại sao gửi nhầm ảnh*: Không có binding cơ học giữa Task ↔ Target Account ↔ Ảnh chụp thực tế. Quy tắc "soi mắt" bị thực thi đối phó, mắt thấy nick này nhưng mồm khẳng định nick kia.
3. *Giải pháp đề xuất*:
   - Module `media_verify.py`: Tự động chạy WinRT OCR đọc text trên ảnh trước khi gửi `MEDIA:`, đối soát handle với target account. Nếu không khớp ➔ FAIL-CLOSED.
   - Mở rộng `pin_top_videos.py`: Thêm `unpin_video_on_device` và `auto_swap` (tự động so sánh view và tráo video top 3 khi đủ 3 ghim) mà không sinh script phụ.

---

## 3. Kiến Trúc Thi Công Chuẩn Mực

### A. Mechanical Send-Gate: `D:/Taadaa/tools/media_verify.py`
```python
@dataclass
class MediaVerdict:
    ok: bool
    reason: str             # "exact_match" | "fuzzy_match" | "handle_not_found" | "image_missing" | "ocr_failed"
    matched_text: Optional[str]
    ocr_text: str

def normalize_handle(s: str) -> str:
    text = unicodedata.normalize("NFKC", s).casefold().strip()
    return "".join(text.split()).lstrip("@")

def verify_media_target(image_path, expected_handle: str, min_ratio: float = 0.85) -> MediaVerdict:
    # 1. Kiểm tra tồn tại file ảnh
    # 2. Chạy WinRT OCR qua ocr_boxes.ps1
    # 3. Chuẩn hóa NFKC + casefold cho cả handle và OCR tokens
    # 4. Token match chính xác hoặc fuzzy match qua difflib.SequenceMatcher >= min_ratio
    # 5. Fail-closed nếu handle không tìm thấy trên ảnh!
```
- **Kiểm chứng độc lập**: Đạt 10/10 test PASS trong `test_media_verify.py`.
- **Kiểm chứng thực tế trên ảnh lỗi Máy 18 (`m18_profile_current.png`)**:
  - `verify_media_target("m18_profile_current.png", "huy010822")` ➔ `ok=False, reason='handle_not_found'` (Chặn đứng gửi ảnh sai nick!).
  - `verify_media_target("m18_profile_current.png", "hollybsulliv33")` ➔ `ok=True, reason='exact_match'` (Khớp nick thực tế trên màn hình).

### B. Mở Rộng Canonical: `D:/Taadaa/tools/pin_top_videos.py`
1. `_apply_tile_action(serial, cx, cy, expected_action, metrics=None)`:
   - Dùng chung cho cả `PIN` lẫn `UNPIN`: Tap tile ➔ Tap Share ➔ Đọc action sheet ➔ Assert đúng action (`PIN` hoặc `UNPIN`) ➔ Tap center ➔ Đóng sheet.
2. `verify_unpin_applied(serial, pinned_before, metrics=None)`:
   - Đọc lại UI XML, assert số video có badge "Đã ghim" giảm đi.
3. `unpin_video_on_device(serial, account=None, dry_run=False)`:
   - Tự động nhả ghim video có view thấp nhất trong số các video đang ghim.
4. Auto-Swap trong `pin_video_on_device(...)`:
   - Khi đã đạt trần 3 ghim (`pinned_before >= max_pins`) và `auto_swap=True`:
   - So sánh view candidate với video ghim thấp nhất: Nếu `candidate['views'] > lowest['views']` ➔ Tự động `Unpin lowest` rồi `Pin candidate` ➔ Trả về `status: "SWAPPED"`.
5. SplashActivity Warmup Guard:
   - Trong `open_target_profile`: Poll `dump_ui()` tối đa 12s chờ TikTok thoát `SplashActivity` trước khi gọi `open_profile_root`, triệt tiêu lỗi `ATX_SESSION_EMPTY_HIERARCHY`.
6. CLI Flags:
   - `--action {pin, unpin, swap}`, `--no-auto-swap`.
- **Kiểm chứng độc lập**: Đạt 37/37 test PASS trong `test_pin_top_videos.py`.

---

## 4. Kỷ Luật Phối Hợp & Quy Tắc Bất Biến Mới
1. **Phân vai rõ ràng**: Khi gặp lỗi hệ thống hoặc cần thiết kế kiến trúc:
   - **Claude CLI (Sonnet 5.5)**: Chỉ đóng vai trò Planner/Reviewer ra bản vẽ blueprint (`claude_worker.py --role planner`).
   - **Coordinator / Haiku CLI**: Trực tiếp thi công code theo blueprint qua `dispatch_worker.py`. CẤM để Claude Sonnet tự ý sửa code vụn vặt gây hao hụt quota.
2. **Quy tắc Send-Gate trước khi gửi `MEDIA:`**:
   - Trước khi đính kèm thẻ `MEDIA:<path>`, bắt buộc phải chạy `verify_media_target(image_path, target_handle)`.
   - Nếu `ok == False` ➔ DỪNG LẠI NGAY LẬP TỨC, cấm gửi ảnh, kiểm tra lại hiện trường thiết bị.
