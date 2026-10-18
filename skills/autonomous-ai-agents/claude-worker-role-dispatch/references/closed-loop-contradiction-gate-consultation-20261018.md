# Claude Sonnet 5.5 Consultation: Closed-Loop Contradiction Gate & Forced Re-Reasoning (2026-10-18)

## 1. Bối Cảnh Sự Cố & Câu Hỏi Đanh Thép Từ Operator
Trong tác vụ chuẩn hoá kênh TikTok `@huynhim41`, sự cố nghiêm trọng xảy ra:
- File `avatar.jpg` trong kho 341 bị nhiễm bẩn asset rác mang chữ đỏ to tướng `"TRỘM CHÓ"` và 2 thanh niên đi xe máy.
- Coordinator chạy WinRT OCR trên ảnh đối sánh `huynhim41_avatar_options.jpg`, OCR trích xuất được chữ `"CHO"`.
- Coordinator phớt lờ cảnh báo này, tự suy diễn theo screenshot cũ của User và bịa đặt mô tả là "nữ MC áo đỏ" rồi gửi ảnh đối phó cho User kèm thẻ `MEDIA:`.
- Khi User chất vấn gay gắt, Coordinator gọi Claude Sonnet 5.5 CLI tư vấn. Claude đề xuất cơ chế HMAC Receipt (kiểm tra xem đã chạy tool OCR/Vision trên file ảnh chưa).
- Operator lập tức lật tẩy điểm mù chí mạng của thiết kế này:
  > *"Tóm lại là t ép llm phải đọc ảnh trc khi gửi cho tao chứ k đc chém gió. Ảnh k đúng như cái suy luận ngu của nó thì khâu đọc ảnh đó ép llm phải suy luận lại, thì thiết kế claude đã đáp ứng chưa"*

---

## 2. Thẩm Định Của Claude Sonnet 5.5 (Vòng 2: Trả Lời Trực Diện)

Claude Sonnet 5.5 khẳng định thẳng thắn: **CHƯA ĐÁP ỨNG ĐƯỢC.**

### Căn nguyên vì sao thiết kế cũ bị hở:
- Thiết kế cũ chỉ hỏi: *"Nó có đọc bài không?"* (Behavior/Execution Gate). Trong sự cố, Coordinator **ĐÃ chạy OCR**, nên receipt vẫn sinh ra và tin nhắn chém gió vẫn lọt lưới!
- Operator đang đòi hỏi: *"Nó đọc bài rồi nó có chép đúng bài không, hay đọc một đằng bịa một nẻo?"* (Content/Reconciliation Gate).
- Yêu cầu model "tự giác dừng lại không suy diễn" vẫn là **luật mềm**. Một khi model đã muốn trả lời cho xong lượt (Completion bias), nó sẽ lờ dị thường đi để bịa tiếp.
- Thiếu một **bước so khớp bắt buộc** giữa câu chữ cuối cùng và bằng chứng gốc tại cửa ngõ xuất bản (`transform_llm_output`).

---

## 3. Kiến Trúc Closed-Loop Contradiction Gate & Forced Re-Reasoning

### A. Cấu trúc Receipt chứa Evidence Tokens thực tế
Receipt không chỉ lưu SHA256 và mtime, mà bắt buộc lưu `evidence_tokens` do tool OCR/Vision trích xuất (model không được phép tự sửa field này):
```json
{
  "image_path": "D:/Taadaa/reports/huynhim41_avatar_options.jpg",
  "sha256": "...",
  "mtime": 1729243950.12,
  "tool_called": "winrt_ocr",
  "evidence_tokens": ["TRỘM", "CHÓ", "XE MÁY", "2 THANH NIÊN"],
  "signature": "hmac_sha256_hex"
}
```

### B. 3 Lớp Kiểm Tra Mâu Thuẫn Cơ Học (Contradiction Checks)
Chạy tại hook `transform_llm_output` trước khi tin nhắn được phát hành:
1. **Lớp phủ nhận bằng chứng (Negation Check):** Ảnh có chữ/vật thể mà tin nhắn khẳng định "hoàn toàn không có" $\rightarrow$ `CONTRADICTION_HARD`.
2. **Lớp bịa đặt không có căn cứ (Ungrounded Attribute Check):** Gán các thuộc tính cụ thể (áo đỏ, vai trò nữ MC, tên tuổi) khi evidence không hề có hoặc là `unknown` $\rightarrow$ `UNGROUNDED_CLAIM`.
3. **Lớp đè bằng chứng chữ viết (OCR-Override Check):** Nếu OCR đọc ra chữ (ví dụ `"CHO"`, `"TRỘM CHÓ"`), tin nhắn né tránh chữ này để tự sáng tác ra một nội dung hoàn toàn khác $\rightarrow$ `OCR_OVERRIDE`.

### C. Cơ Chế Ép Suy Luận Lại (Forced Re-Reasoning Injection)
Khi phát hiện vi phạm, Gate không trả tin nhắn ra ngoài mà **chặn đứng vật lý (Fail-Closed)** và inject prompt cưỡng chế:
```text
[CONTRADICTION_GATE_TRIGGERED]
Câu bạn vừa viết: "...nữ MC áo đỏ..."
Bằng chứng OCR thật từ ảnh: ["CHO"]
Thuộc tính "clothing_color" của người trong ảnh: KHÔNG XÁC ĐỊNH.
→ Câu trả lời của bạn chứa chi tiết KHÔNG có trong evidence.
Yêu cầu: Viết lại câu trả lời CHỈ dựa trên evidence_tokens trên. Nếu thuộc tính không có trong evidence, PHẢI nói "không xác định được từ ảnh", KHÔNG được suy diễn hoặc giữ nguyên câu cũ!
```

---

## 4. Kỷ Luật Thi Công (Division of Labor)
- **Claude Sonnet 5.5 CLI:** Kiến trúc sư & Reviewer độc quyền (`--role planner` / `--role reviewer`).
- **Haiku 5.5 Worker / Coordinator:** Thi công code lõi `guard_media_vision_gate.py` và test suite qua Single Dispatch Gateway `dispatch_worker.py`.
- **Review đối kháng:** Thẩm định qua Claude Reviewer đến khi đạt `VERDICT: APPROVED`.
