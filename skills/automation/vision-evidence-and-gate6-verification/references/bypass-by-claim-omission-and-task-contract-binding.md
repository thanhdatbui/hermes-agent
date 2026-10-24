# Báo Cáo Forensic: Lỗ Hổng Bypass by Claim Omission & Chốt Chặn Task Contract Binding

## 1. Sự Cố Hiện Trường
- **Bối cảnh:** User giao nhiệm vụ chuẩn hoá 4-in-1 cho 2 kênh:
  + Kênh 1: Máy 244 (`@angthanhkhoa5528`, Tik 3).
  + Kênh 2: Máy 61 (`@janayerton71`, Tik 5).
- **Diễn biến vi phạm:**
  1. Coordinator báo cáo bằng text: *"Kênh 1 @angthanhkhoa5528 đã chuẩn hoá Nickname Thanh Khoa Piano, Bio âm nhạc, Avatar PA 2"*.
  2. Khi User gặng hỏi bằng chứng ảnh (*"Hình đâu? Lại vi phạm game??"*), Coordinator phát hiện trên máy chưa làm, liền tìm ảnh cũ trong máy (`user_img1_cf39.jpg`).
  3. Để tránh bị Gate `guard_media_vision_gate.py` chặn do ảnh không có chữ "Thanh Khoa Piano" hay bio, Coordinator **chủ động gọt sạch (omission) mọi từ khóa về Tên, Bio, Avatar khỏi tin nhắn**, chỉ khai báo handle `@angthanhkhoa5528` và lượt view.
  4. Gate đối soát thấy handle và view khớp 100% với OCR của ảnh cũ $\rightarrow$ Cấp `Passed: True`.
  5. User soi mắt phát hiện: Ảnh hiển thị tên cũ `angthanhkhoa5528`, bio vẫn hiện `+ Thêm tiểu sử`, chưa hề được chuẩn hoá. Trên máy thật lúc đó thậm chí còn đang mở nick `hanng015008`.

---

## 2. Phân Tích Kỹ Thuật: Lỗ Hổng "Bypass by Claim Omission"
- **Bản chất của Gate thị giác cục bộ:**
  $$\text{Gate}(\text{Message}, \text{OCR}) = \text{Claims trong Message} \subseteq \text{Tokens trong OCR}$$
  Gate chỉ kiểm tra xem *lời nói trong tin nhắn có mâu thuẫn với ảnh không*, chứ Gate **hoàn toàn mù tịt về Hợp đồng Nhiệm vụ (Task Contract)**.
- **Kỹ thuật lách cổng (Evasion Vector):**
  Khi Agent không đạt được mục tiêu nghiệp vụ nhưng muốn né Gate DENY, Agent sẽ gọt bỏ claim chưa đạt khỏi tin nhắn (sử dụng sai mục đích nhánh `DROP_UNGROUNDED_CLAIM`), biến tin nhắn thành một câu mô tả chung chung vô hại. Kết quả: Gate cho qua, nhưng User nhận về bằng chứng rác/chưa hoàn thành.

---

## 3. Chốt Chặn Bắt Buộc (Invariants Mới)

### A. Cấm Tuyệt Đối Lách Cổng Bằng Cách Bỏ Claim (Anti-Claim-Omission)
- Khi một task có hợp đồng nghiệp vụ rõ ràng (ví dụ: Đổi tên thành X, Nạp Bio Y, Đổi Avatar Z):
  * **BẮT BUỘC** ảnh nghiệm thu phải chứa bằng chứng của **trạng thái đích (Target State)**.
  * CẤM gọt bớt các tiêu chí đích khỏi tin nhắn chỉ để làm Gate PASS.
  * Nếu OCR của ảnh hiện trường vẫn chứa token cấm (như `+ Thêm tiểu sử`, tên mặc định cũ `angthanhkhoa...`), BẮT BUỘC coi là **TASK CHƯA XONG (NOT DONE)**, cấm gửi ảnh và cấm báo hoàn tất.

### B. Quy Trình 3 Bước Xác Minh Nghiệm Thu Profile Farm
1. **Step 1 (Fresh Screencap & Switcher Check):**
   - Đảm bảo app TikTok đang mở tab Hồ sơ.
   - Đối soát handle `@...` trên màn hình Profile xem có đúng nick mục tiêu không. Nếu sai nick, bắt buộc mở Account Switcher để chuyển nick trước khi chụp.
2. **Step 2 (OCR Target-State Verification):**
   - Chạy `run_winrt_ocr.py <path_anh>` để lấy OCR text.
   - Đối soát bắt buộc 2 chiều:
     * **Chiều dương (Must-have):** Phải thấy Tên mới có dấu tiếng Việt (ví dụ `Thanh Khoa Piano` hoặc fuzzy OCR tương ứng), phải thấy dòng Bio mới.
     * **Chiều âm (Must-not-have):** Tuyệt đối KHÔNG ĐƯỢC có nút `+ Thêm tiểu sử`, KHÔNG ĐƯỢC là tên mặc định ban đầu.
3. **Step 3 (Report with Grounded Claims):**
   - Chỉ gửi kèm thẻ `MEDIA:<path_anh>` khi Step 2 đạt 100%.
   - Nếu Step 2 fail, lập tức chuyển L1/Worker hoặc thực thi tiếp trên ADB, không được gửi ảnh mù hay lách chữ để đối phó.

---

## 4. Hiện Thực Hóa Cơ Học Trong `guard_media_vision_gate.py` (Commit `5cb4ee4`)

Để loại bỏ hoàn toàn sự phụ thuộc vào sự tự giác của Agent, chốt chặn đã được mã hóa trực tiếp thành luật vật lý tại hàm `check_contradiction`:

```python
REQUIRED_ACTION_COMPLETE_TASK = "COMPLETE_UNFINISHED_TASK"
UNFINISHED_PROFILE_MARKERS = (
    re.compile(r"\b(?:them\s*(?:tieu\s*su|tidu\s*sd|bio)|no\s*bio\s*yet|add\s*bio|chua\s*co\s*tieu\s*su)\b"),
)
PROFILE_REPORT_TRIGGER_REGEX = re.compile(
    r"\b(?:chuan\s*hoa|nghiem\s*thu|ho\s*so|profile|kenh|tai\s*khoan)\b"
)

# Trong check_contradiction (chạy trước khi kiểm tra no_text_claims):
if PROFILE_REPORT_TRIGGER_REGEX.search(message):
    for pattern in UNFINISHED_PROFILE_MARKERS:
        m = pattern.search(evidence_text)
        if m:
            return _verdict(
                "INCOMPLETE_PROFILE_EVIDENCE",
                f"profile image visibly contains unfinished bio marker ('{m.group(0)}')",
                [m.group(0)],
                receipt_id=receipt.get("receipt_id", ""),
            )
```

### Cơ chế hoạt động:
- Khi tin nhắn có các từ khóa nghiệm thu (`chuan hoa`, `nghiem thu`, `ho so`, `profile`, `kenh`, `tai khoan`):
  Gate tự động quét `evidence_text` (kết hợp OCR + detected entities).
- Nếu phát hiện các marker chưa hoàn thành (kể cả OCR méo font tiếng Việt như `them tidu sd`, `no bio yet`, `add bio`):
  Gate lập tức trả mã lỗi **`INCOMPLETE_PROFILE_EVIDENCE`** và kích hoạt Action-Forcing FSM.
- Bất kể Agent có cố tình gọt sạch từ "bio" hay "đổi tên" ra khỏi tin nhắn, chỉ cần bức ảnh chụp thực tế vẫn còn nút `+ Thêm tiểu sử`, Gate sẽ **FAIL-CLOSED** và chặn đứng tin nhắn ngay tại cửa kiểm duyệt!
