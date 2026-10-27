# Báo Cáo Tư Vấn Claude Sonnet: Quay Về Thiết Kế Tối Giản O(1), Chấm Dứt Bệnh Over-Engineering Của Media Gate

## 1. Bối Cảnh Sự Cố & Vấn Đề Lặp Lại Đa Session
Trong suốt ngày làm việc, người dùng và hệ thống đã phải đối mặt với một chuỗi sự cố lặp lại khó chịu ở nhiều session khác nhau (`20261027_054909_83461a8f`, `20261027_134441_4bf2f9f2`, `20261027_055942_d8042caf`):
- **Hiện tượng:** Khi Agent trò chuyện, giải thích kỹ thuật, nhận việc hoặc thảo luận mà không kèm ảnh (hoặc chưa kịp gửi ảnh), Telegram của người dùng ngay lập tức bị xả rác bởi khối prompt kỹ thuật thô:
  ```text
  [CONTRADICTION_GATE_TRIGGERED]
  verdict: MISSING_MEDIA_EVIDENCE
  reason: message claims UI/device completion but contains no MEDIA: evidence tag
  matched: ...
  REQUIRED_NEXT_ACTION (chon dung 1, thuc hien ngay trong luot nay):
  ...
  --- RAW_MESSAGE (blocked) ---
  ```
- **Phản ứng của Người dùng:** Cực kỳ phẫn nộ trước sự quan liêu, phiền nhiễu và over-engineering của hệ thống gate:
  * *"tao fix cái hook óc chó này sáng h vài lần r đấy đụ mẹ mày... đọc log session cho tao"*
  * *"Cái đụ mẹ session kia t fix r sao vẫn cứ spam ra 1 đống v"*
  * *"Tại sao đéo tiếp tục làm mà bại liệt đi hỏi"*
  * *"Cái guard đó bị over engineer r phải k"*
  * *"Gọi claude cli tư vấn quay về đơn giản k over engineer đi. Mà có session khác cx đang fix lỗi này phải k"*

---

## 2. Bản Chất Bệnh "Over-Engineering" & "Security Theater" Theo Thẩm Định Của Claude Sonnet

Claude Sonnet 5.5 đã thừa nhận và phân tích thẳng thắn vào các triệu chứng bệnh của hệ thống gate:

### A. Triệu chứng 1: Gate kiểm chứng Proxy thay vì Sự Kiện Thật
- Mục tiêu duy nhất của Người dùng: **"Agent cấm báo cáo mồm, cấm gửi ảnh mù. Phải tự mở ảnh ra soi mắt (bằng `browser_vision` hoặc WinRT OCR) rồi mới được suy luận và gửi kèm `MEDIA:<path>`."**
- Nhưng hệ thống lại đắp thêm:
  * HMAC-SHA256, dynamic key 32-byte, file `.jsonl` receipt store.
  * Mtime tolerance, so khớp SHA256 với receipt cũ (làm ảnh mới chụp đè lên bị coi là tampered).
  * Bộ Regex hơn 40 từ khóa đoán mò câu chữ (`ACTION_COMPLETION_PATTERNS`, `SUBJECT_PATTERNS`).
- **Nghịch lý Goodhart:** Thứ gate đo được không phải là thứ cần đo! Kẻ tạo ra ảnh, kẻ ký receipt và kẻ bị kiểm soát đều là cùng 1 process của Agent. HMAC bảo vệ một tín hiệu mà chính process đó giữ key thì không chống được gian lận, mà chỉ tạo ra rào cản hành chính giả tạo ("Bureaucratic Theater").

### B. Triệu chứng 2: Egress Leak (Sai Tầng Kiến Trúc Của Hook)
- Hàm `transform_llm_output` trong plugin Gateway thực chất là **Egress Formatter** — bất kỳ chuỗi text nào nó trả về sẽ trở thành văn bản xuất bản trực tiếp lên màn hình chat Telegram.
- Nhưng gate lại dùng nó như một prompt injector để ném `build_forced_re_reasoning_prompt` vào mặt người dùng.
- Khi gặp false-positive, thay vì nuốt lại trong runtime hoặc chuyển sang degraded template gọn gàng, nó biến màn hình chat của người dùng thành bãi rác mã lỗi.

### C. Triệu chứng 3: Vá Chắp Vá Gây Xung Đột Đa Session
- Session trước cố gắng xóa bỏ `EXEMPTION_MARKERS` vì sợ fail-open, nhưng không sửa tầng regex.
- Kết quả là sang session sau, khi Agent gõ chữ giải trình kỹ thuật, regex lại bắt nhầm và xả rác tiếp. Người dùng tưởng session trước đã sửa xong, dẫn đến xung đột logic và mất lòng tin.

---

## 3. Kiến Trúc Tối Giản O(1) Chuẩn Theo Tư Vấn Của Claude Sonnet

Một gate cơ học đạt chuẩn phải tuân thủ 5 nguyên tắc O(1):
1. **Kiểm tra sự kiện quá trình (Execution Event), không kiểm tra proxy nội dung văn bản.**
2. **Bộ nhớ do Harness / Context ghi nhận, không dựa vào file receipt cồng kềnh.**
3. **Một predicate duy nhất, dưới 20 dòng code.**
4. **Không bao giờ xả prompt lỗi kỹ thuật ra Telegram (Zero Egress Leak).**
5. **Đường trung thực rẻ hơn đường lách.**

### Thiết Kế Chi Tiết O(1):

```python
# 1. PostToolUse hook trên tool thị giác (browser_vision / run_winrt_ocr):
def on_vision_executed(turn_state, image_path):
    turn_state.seen_images.add(normalize_path(image_path))

# 2. Egress Gate tại transform_llm_output:
def transform_llm_output_check(raw_message, turn_state):
    media_paths = extract_media_tags(raw_message)
    
    # TIN NHẮN THUẦN TEXT (Không có thẻ MEDIA:):
    # PASS 100%! Tuyệt đối cấm dùng Regex đoán mò ý định câu chữ của người dùng hay agent.
    if not media_paths:
        return True, raw_message
        
    # TIN NHẮN CÓ CHỨA THẺ MEDIA:<path>:
    # Kiểm tra đúng 1 điều kiện cơ học duy nhất:
    for path in media_paths:
        if not os.path.isfile(path) or os.path.getsize(path) == 0:
            return False, f"LỖI: File ảnh '{path}' không tồn tại trên đĩa."
            
        if normalize_path(path) not in turn_state.seen_images:
            # Chưa soi mắt thật -> Chặn ngay, yêu cầu mở ảnh ra xem
            return False, f"CHƯA SOI ẢNH: Hãy gọi browser_vision('{path}') mở ảnh ra xem trước khi gửi!"
            
    return True, raw_message
```

---

## 4. Lợi Ích & Sự Chấm Dứt Bại Liệt

1. **Không còn False-Positive:** Tin nhắn chat, giải trình, nhận việc, phân tích lỗi, code diff không bao giờ bị chặn hay đòi ảnh.
2. **Không còn Egress Leak:** Khung chat Telegram luôn sạch sẽ, chấm dứt hoàn toàn mã lỗi `[CONTRADICTION_GATE_TRIGGERED]`.
3. **Bảo toàn 100% Invariant Soi Mắt Thật:** Mọi ảnh gửi qua `MEDIA:` bắt buộc phải có lượt gọi `browser_vision` thật trong cùng turn; không soi mắt thì không gửi được.
4. **Không Conflict Đa Session:** Bỏ toàn bộ hệ thống file `.jsonl` receipt chia sẻ, trạng thái nằm gọn trong turn execution của Harness.
