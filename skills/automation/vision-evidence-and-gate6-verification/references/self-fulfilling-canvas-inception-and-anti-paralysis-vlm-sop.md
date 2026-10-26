# Bẫy Self-Fulfilling Inception Trên Proposal Canvas & Kiến Trúc Anti-Paralysis VLM Gate

## 1. Bản Chất Sự Cố & Lỗ Hổng Bị Bypass (The Inception Vulnerability)
- **Cơ chế sự cố:** Khi Coordinator tạo ảnh Proposal Canvas (ghép 4 ô avatar), Agent đã dùng `cv2.putText` hoặc `PIL.ImageDraw` in đè các chuỗi văn bản mô tả (ví dụ: *"Vườn ươm cây giống"*, *"Khuôn viên nhà vườn"*, *"Lối đi cây cảnh"*) lên chính bức ảnh canvas tổng hợp. Sau đó:
  1. Agent chạy `run_winrt_ocr.py` trên file canvas vừa tạo.
  2. OCR engine đọc được chính xác các từ ngữ vừa in trên ảnh và lưu vào receipt.
  3. Gate `guard_media_vision_gate.py` chỉ kiểm tra `Claims trong Message ⊆ Tokens trong OCR`.
  4. Hậu quả: Tin nhắn tự do khẳng định các visual claim sai sự thật (biến ảnh vi khuẩn/kính hiển vi thành "vườn cây"), Gate bị bypass 100% vì thấy chữ trong tin nhắn khớp với chữ OCR trên ảnh!
- **Token Grounding Gap:** OCR chỉ đọc được ký tự văn bản, hoàn toàn mù màu và mù ngữ nghĩa thị giác (pixel content). Agent tự in chữ lên ảnh rồi dùng OCR đọc lại là tạo ra **vòng tròn tự bảo lãnh (self-fulfilling inception)**, triệt tiêu tính độc lập của bằng chứng.

---

## 2. Kiến Trúc Khắc Phục Cơ Học (The Mechanical Fix)

### 2.1 Phân Loại Provenance & Trừ Khử Overlay Tokens
- **Định danh nguồn gốc ảnh (Provenance Class):**
  * `RAW_CAPTURE`: Screencap thiết bị hoặc frame trích xuất nguyên bản từ video gốc.
  * `DERIVED_CROP`: Crop/resize thuần túy từ ảnh RAW mà không vẽ thêm chữ/đồ họa.
  * `SYNTHETIC`: Ảnh có pixel do script tự vẽ, gồm text overlay hoặc ghép canvas.
- **Quy tắc trừ khử chữ tự in (Overlay Exclusion Invariant):**
  * Khi tạo Canvas bằng tool (`make_proposal_canvas.py`), tool bắt buộc ghi nhận danh sách `overlay_tokens[]` (các chữ được in lên canvas) vào metadata sidecar.
  * Gate cơ học bắt buộc loại bỏ toàn bộ `overlay_tokens` khỏi evidence grounding:
    $$\text{evidence\_tokens} = \text{OCR\_tokens} - \text{overlay\_tokens}$$
  * Mọi chữ do script tự in lên ảnh có **giá trị bảo chứng bằng 0**.

### 2.2 Phân Tầng Thẩm Định (Claim Router T0 / T1)
- **Tier 0 (Text Claim / Raw Capture):** Screencap UI thiết bị thật, claim chỉ chứa text/số/tên UI $\rightarrow$ Tiếp tục dùng WinRT OCR (nhanh, rẻ, giữ nguyên).
- **Tier 1 (Visual-Semantic Claim / Avatar Proposals):** Khi tin nhắn chứa mô tả thị giác (chủ thể, bối cảnh, "thiên nhiên", "chân dung", "vi sinh", "cây cối") $\rightarrow$ **Bắt buộc VLM độc lập (Sol Web Vision `:20129` hoặc Claude CLI)**:
  1. **Blind Describe:** VLM độc lập đọc ảnh không kèm prompt mớm lời của Agent, trả về JSON `{subjects[], scene}`.
  2. **Decoy Check:** Chèn 1 claim bẫy sai. Nếu VLM gật bừa $\rightarrow$ Huỷ kết quả.
  3. **Delivery Check:** Đối soát kích thước / màu sắc chủ đạo local để chống trường hợp VLM trả lời mù không thấy ảnh.

---

## 3. Kỷ Luật Chống Khóc Lóc & Bại Liệt (Zero-Whining & Anti-Paralysis FSM)

**Nguyên tắc tối cao: Gate kiểm soát Claim, tuyệt đối KHÔNG bao giờ chặn đứng luồng gửi làm kẹt phiên.**

1. **Thông báo chặn kèm đúng 1 lệnh thực thi duy nhất (Action-Forcing Guidance):**
   * Khi VLM bác bỏ claim của Agent, Gate cấm trả về lỗi mơ hồ khiến Agent xin lỗi hay phân trần.
   * Gate trả về trực tiếp ground-truth:
     ```text
     ẢNH THỰC CHỨA: 4 tiêu bản vi sinh vật / tế bào dưới kính hiển vi.
     LỆNH: Gửi lại tin nhắn dựa trên mô tả này. CẤM xin lỗi, CẤM giải thích.
     ```
2. **Trần cứng 2 vòng (Cap 2 turns) $\rightarrow$ `ALLOW_WITH_CLAIM_STRIP`:**
   * Nếu sau 2 lượt gửi mà visual claim vẫn không khớp, Gate **tự động hạ cấp sang chế độ Strip**: Cho phép gửi thẻ `MEDIA:`, tự động thay caption bằng template trung tính:
     `[UNVERIFIED-VISUAL] Gửi ảnh theo yêu cầu, chỉ xác nhận thông số kích thước & OCR text.`
   * Triệt tiêu hoàn toàn nguy cơ Agent bị đóng băng, khóc lóc, hoặc đùn đẩy việc lại cho User.
3. **Fallback VLM Nhanh (Timeout 25s):**
   * Nếu VLM ngoại vi (Sol/Claude) gặp lỗi mạng, 503 hoặc timeout > 25s $\rightarrow$ Chuyển thẳng sang `ALLOW_WITH_CLAIM_STRIP`, tuyệt đối không treo phiên chờ vô hạn.
