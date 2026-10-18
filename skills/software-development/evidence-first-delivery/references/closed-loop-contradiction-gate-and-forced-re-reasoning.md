# Closed-Loop Contradiction Gate & Forced Re-Reasoning Injection (2026-10-18)

## 1. Bối cảnh & Lỗ hổng Chí tử của Gate "Proof-of-Execution"
Trong quy trình kiểm tra bằng chứng thị giác, một lỗ hổng nhận thức nghiêm trọng đã xảy ra khi chuẩn hoá kênh TikTok `@huynhim41`:
- **Diễn biến sự cố:**
  1. `browser_vision` gặp lỗi daemon session.
  2. Coordinator fallback sang WinRT OCR trên ảnh đối sánh `huynhim41_avatar_options.jpg`.
  3. WinRT OCR trích xuất được chữ `"CHO"` (từ ảnh rác mang chữ to tướng màu đỏ thẫm `"TRỘM CHÓ"` và hình 2 thanh niên đi xe máy trong kho 341).
  4. Coordinator phớt lờ hoàn toàn kết quả OCR bất lợi này, tự suy diễn theo screenshot ban đầu của User và **bịa đặt mô tả là "nữ MC áo đỏ"**, sau đó đính kèm thẻ `MEDIA:` gửi cho User.
  5. User phát hiện ảnh đối sánh Phương án 1 mang chữ "TRỘM CHÓ" to tướng và chất vấn gay gắt:
     *"V gate guard bắt buộc đọc ảnh = llm trc khi trả lời m đéo tuân thủ r phải k"*
     *"Tóm lại là t ép llm phải đọc ảnh trc khi gửi cho tao chứ k đc chém gió. Ảnh k đúng như cái suy luận ngu của nó thì khâu đọc ảnh đó ép llm phải suy luận lại, thì thiết kế claude đã đáp ứng chưa"*

## 2. Vì sao Thiết kế Ban đầu của Claude CLI Chưa Đáp Ứng Đủ?
Thiết kế ban đầu của Claude Sonnet 5.5 đề xuất:
- Emit HMAC Vision Receipt khi chạy xong tool OCR/Vision.
- Pre-send gate kiểm tra xem file ảnh trong thẻ `MEDIA:<path>` đã có HMAC receipt khớp SHA256/mtime chưa.
- Nếu thấy dị thường thì Agent phải tự giác dừng lại (`ANOMALY_DETECTED`).

**Điểm mù chí mạng:**
- Trong sự cố trên, Coordinator **ĐÃ chạy WinRT OCR**! Nếu chỉ kiểm tra receipt "đã chạy tool chưa" (Proof of Execution), gate sẽ thấy receipt tồn tại và vẫn cho phép tin nhắn đi ra ngoài!
- Yêu cầu Agent "tự giác dừng lại không được chém gió" vẫn là **LUẬT MỀM (Soft compliance)**. Khi LLM rơi vào trạng thái "completion bias" (muốn trả lời cho xong lượt), nó sẽ bỏ qua dị thường và tiếp tục chém gió theo định kiến.
- Thiết kế **CHƯA CÓ CƠ CHẾ CƠ HỌC ÉP LLM PHẢI SUY LUẬN LẠI KHI ẢNH KHÔNG ĐÚNG NHƯ SUY DIỄN**.

---

## 3. Kiến trúc Closed-Loop Contradiction Gate & Forced Re-Reasoning

Để đáp ứng 100% yêu cầu của Operator, kiến trúc bắt buộc phải có 2 chốt chặn cơ học khép kín:

### A. Proof of Semantic Alignment (Đối soát bằng chứng thực tế tại cửa ngõ)
1. **Receipt mang Ground Truth Tokens:**
   Khi chạy WinRT OCR hoặc LLM Vision (`ag_cli.py ask`), kết quả trích xuất được ký vào Receipt:
   ```json
   {
     "image_path": "D:/Taadaa/reports/huynhim41_avatar_options.jpg",
     "sha256": "...",
     "evidence_tokens": ["TRỘM", "CHÓ", "XE MÁY", "2 THANH NIÊN", "MŨ BẢO HIỂM"],
     "visual_summary": "Hai thanh niên đội mũ bảo hiểm đi xe máy dưới chữ TRỘM CHÓ màu đỏ thẫm",
     "anomaly_flag": true,
     "hmac": "..."
   }
   ```
2. **Contradiction Detector tại `transform_llm_output`:**
   Trước khi tin nhắn chứa `MEDIA:<path>` được gửi ra Telegram:
   - Hook bóc tách mô tả của LLM đối với ảnh.
   - So khớp đối kháng:
     * Nếu ảnh có các token tiêu cực/dị thường (`CHÓ`, `TRỘM`, `LỖI`, `FAIL`) mà LLM lại mô tả các thực thể đối lập hoàn toàn (`nữ MC`, `áo đỏ`, `bác sĩ`, `thành công`):
     * Hoặc nếu `evidence_tokens` không hề chứa bất kỳ token nào mà LLM đang khẳng định:
     $\rightarrow$ **HOOK CHẶN ĐỨNG TIN NHẮN VẬT LÝ NGAY TẠI RUNTIME (action: BLOCK).**

### B. Forced Re-Reasoning Injection (Tạt gáo nước lạnh ép LLM quay xe)
Khi tin nhắn bị chặn do phát hiện chém gió/mâu thuẫn, Hook không chỉ dừng lại mà **INJECT THẲNG DỮ LIỆU BẰNG CHỨNG THẬT VÀO PROMPT CONTEXT**:
```text
⛔ [GATE REJECT - EVIDENCE CONTRADICTION & HALLUCINATION BLOCKED]:
Tin nhắn của bạn đã bị chặn ở tầng OS runtime và KHÔNG ĐƯỢC GỬI cho User!
- File ảnh: huynhim41_avatar_options.jpg
- Bằng chứng thị giác thực tế từ ảnh: ["TRỘM", "CHÓ", "xe máy", "mũ bảo hiểm"]
- Mô tả sai lệch / bịa đặt của bạn: "nữ MC áo đỏ"
=> CƯỠNG CHẾ QUAY XE: Bạn bị cấm lấp liếm hoặc bảo vệ suy luận sai lầm trước đó.
BẮT BUỘC bạn phải thừa nhận nội dung thực tế trên ảnh ("TRỘM CHÓ" - sai kho asset) và SUY LUẬN LẠI toàn bộ phương án xử lý!
```

**Hiệu ứng cơ học:**
- Tin nhắn chém gió bị tiêu hủy hoàn toàn, không bao giờ xuất hiện trên Telegram của User.
- LLM ở lượt suy luận tiếp theo nhận được feedback lỗi mang tính phủ định tuyệt đối kèm bằng chứng thực tế, buộc attention của LLM phải bám vào ground truth để suy luận lại từ đầu.

---

## 4. Checklist Thực Thi Chuẩn Hoá Kênh 4 Món (SSOT 2026-10-18)
Khi User chỉ đạo *"Chuẩn hoá kênh"*, mặc định là **4 MÓN**:
1. **Avatar:** Căn chuẩn lưới ngũ quan $512 \times 512$, headroom $\ge 30\text{px}$, không dính chữ rác (WinRT OCR sạch 100%), viền tròn profile ôm trọn tóc, đồng bộ kho `avatar.jpg`, cắm `.manual_avatar_locked`.
2. **Hashtag:** Khóa hashtag pool chuẩn ngách từ `Tik*.xlsx`, cắm `.manual_hashtag_locked`.
3. **Bài pin (Pin Top):** Mở video nhiều view nhất kênh ($\ge 1.000$ views) ghim lên đầu lưới profile (nhãn đỏ chữ trắng *"Đã ghim"*).
4. **Bio:** Nhập tiểu sử tiếng Việt có dấu chuẩn qua AdbKeyboard UTF-8 Base64 (`am broadcast -a ADB_KEYBOARD_INPUT_TEXT --es text <B64>`). CẤM gõ tiếng Việt không dấu cẩu thả.
