# Bẫy UNVERIFIED_BY_VISION Do Dính Từ Khóa Visual Claim Khi Chỉ Dùng OCR Thô

## 1. Triệu Chứng & Hiện Tượng Thực Tế
Trong phiên điều tra Farm Alert (máy M261), Coordinator đã dùng WinRT OCR đọc ảnh Switcher `screen.png` để chứng minh có đủ 7 tài khoản đang đăng nhập và đính kèm thẻ `MEDIA:<path>` trong câu trả lời.

Tuy nhiên, User trên Telegram nhận được tin nhắn rác kỹ thuật:
```text
Trạng thái: DEGRADED | Mã: UNVERIFIED_BY_VISION | Thiết bị:  | Bằng chứng cuối: rec_5723828f_adc5f375 | Việc tiếp theo: nh D:Taadaaruntimeadminlive2026-10-28row-0-06004920261028-060245
```
User lập tức bức xúc và phản hồi:
```text
[Replying to: "Trạng thái: DEGRADED | Mã: UNVERIFIED_BY_VISION ..."]
Cái l gì thế
```

## 2. Nguyên Nhân Gốc (Root Cause)
Cổng cơ học `guard_media_vision_gate.py` (hàm `check_contradiction` dòng 434-448) định nghĩa:
```python
norm_msg = _normalize_text(message_text)
is_visual_claim = any(k in norm_msg for k in ("thien nhien", "cay", "hoa", "canh", "chan dung", "de xuat", "phuong an", "khuon vien", "vuon", "vi sinh", "vi khuan"))

if (is_visual_image or is_visual_claim) and tool_called not in ("browser_vision", "ag_cli_vision"):
    return _verdict(
        "UNVERIFIED_BY_VISION",
        f"Ảnh '{image_path}' mới chỉ chạy OCR thô ({tool_called}). Coordinator BẮT BUỘC phải gọi browser_vision mở file ra soi mắt trước khi gửi!",
        [str(image_path)],
        receipt_id=receipt.get("receipt_id", ""),
    )
```

1. Trong bài báo cáo, Coordinator dùng từ `"phương án"` (ví dụ: *Phương Án Xử Lý & Mở Lại Batch*).
2. Từ `"phương án"` làm biến `is_visual_claim` bật lên `True`.
3. Receipt hiện có của ảnh `screen.png` lúc đó được sinh từ `run_winrt_ocr.py` nên có `tool_called = "run_winrt_ocr"`.
4. Gate nhận định: Đây là thông điệp chứa Visual Claim (đề xuất/phương án) nhưng lại chỉ có vé OCR thô bảo lãnh. Gate từ chối và kích hoạt mã lỗi `UNVERIFIED_BY_VISION`.
5. Tầng Hook `transform_llm_output_check` quật ngã toàn bộ bài viết và đè lên bằng chuỗi mẫu degraded `build_forced_re_reasoning_prompt()`, khiến User nhận phải văn bản lỗi kỹ thuật khó hiểu.

## 3. Quy Chuẩn Khắc Phục Bắt Buộc (SOP)
1. **Quy tắc Same-Turn Browser Vision:**
   Khi muốn đính kèm thẻ `MEDIA:<path_anh>`, Coordinator **BẮT BUỘC** phải gọi:
   ```python
   browser_navigate(url="file:///<path_anh>")
   browser_vision(question="Soi mắt kiểm tra nội dung ảnh...")
   ```
   ngay trong **CÙNG MỘT TURN** (hoặc turn ngay trước đó trong vòng 300s).
   Hàm `_extract_seen_images_from_tool_calls(tool_calls)` của Gate sẽ tự động nhận diện URL `file:///` và cấp vé kiểm định:
   ```json
   {
     "tool_called": "browser_vision",
     "ocr_raw_text": "SEEN_BY_COORDINATOR_BROWSER_VISION",
     "reason_code": "SEEN_BY_NATIVE_VISION"
   }
   ```
   Vé này có `tool_called == "browser_vision"` hợp lệ, vượt qua mọi kiểm tra `is_visual_claim`.

2. **Cảnh báo TTL 300 giây:**
   Receipt trong `vision_receipts.jsonl` chỉ có hiệu lực trong vòng **300 giây (5 phút)** (`DEFAULT_TTL_SECONDS = 300`). Nếu Coordinator gọi tool soi ảnh nhưng loay hoay quá 5 phút mới gửi tin nhắn có thẻ `MEDIA:`, vé cũ sẽ bị Gate coi là hết hạn (`NO_RECEIPT`) và tiếp tục bị chặn.

3. **Kỷ luật từ ngữ khi chỉ có vé OCR thô:**
   Nếu chưa kịp gọi `browser_vision` mà chỉ có vé từ `run_winrt_ocr.py`, tuyệt đối tránh dùng các từ khóa nhạy cảm kích hoạt `is_visual_claim`:
   `"phương án"`, `"đề xuất"`, `"chân dung"`, `"thiên nhiên"`, `"khuôn viên"`, `"vườn"`, `"cảnh"`.
