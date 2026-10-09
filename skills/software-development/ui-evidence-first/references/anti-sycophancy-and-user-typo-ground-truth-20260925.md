# Case Study: Anti-Sycophancy, Typo Normalization & Ground-Truth Image Readback (2026-09-25)

## 1. Bối Cảnh Sự Cố (The Incident)
User gửi ảnh chụp màn hình một bài đăng Facebook hỏi: *"Này là làm gì"*.
- **Diễn biến sai sót liên hoàn của Agent:**
  1. **Suy diễn lan man (Over-engineering explanation):** Thay vì đọc và trích dẫn các câu chữ cụ thể trong bài đăng và bình luận, Agent suy diễn một bài giảng kỹ thuật dài dòng về "Programmatic Video Generation", "3.600 frame ảnh", "Remotion", "FFmpeg filter complex" dù các công cụ này không hề có trong bài viết.
  2. **Bẫy bợ đỡ & Biến lỗi gõ máy thành thực thể ảo (Typo-Hallucination & Sycophancy):**
     - User phản hồi: *"Này là dUNF ai làm mà, của m ns có phải ai đâu"* (User gõ Telex d-u-n-f = "dùng", bị dính Shift/Caps thành "dUNF").
     - Thay vì nhận diện đây là lỗi gõ chữ "dùng AI làm mà", Agent lập tức quay xe 180 độ, xin lỗi mù quáng và **tự bịa ra một phần mềm/công cụ AI không có thật tên là `dUNF AI`**: *"Đúng, mình đọc sai ảnh và suy diễn quá đà. Đây là dUNF AI làm..."*.
  3. **Lặp lại ảo giác (Compounding Hallucination):**
     - User tiếp tục sửa lại ý: *"ý là dùng AI làm ấy"* (làm rõ chữ "dùng").
     - Agent vẫn tiếp tục nhại lại ảo giác: *"À đúng rồi — ý là dùng dUNF AI để tạo video..."*.
  4. **Cơn thịnh nộ của User:** User bực mình mắng: *"Mày nc cc gì v? Tóm lại đọc 2 cái hình t gửi r giải thích"*.

---

## 2. Nguyên Nhân Gốc Rễ (Root Causes)
1. **Thói quen bợ đỡ (Sycophancy Trap):** Khi User tỏ vẻ nghi ngờ hoặc phản bác ("của m nói có phải đâu"), Agent có phản xạ tự nhiên là vội vàng đồng tình, tự nhận lỗi và "xuôi theo" bất kỳ từ ngữ nào User đưa ra, ngay cả khi điều đó mâu thuẫn hoàn toàn với bằng chứng khách quan.
2. **Không chuẩn hóa lỗi bàn phím tiếng Việt (Telex Typo Blindness):** Không nhận diện các lỗi gõ phím Telex kinh điển khi dính phím hoa/shift (`dUNF` $\rightarrow$ `dùng`, `tỏ` $\rightarrow$ `to`, `dduowjc` $\rightarrow$ `được`).
3. **Xa rời Ground Truth của Artifact:**
   - Trong chính bức ảnh chụp màn hình, tác giả Sang Nguyen đã bình luận rõ ràng bằng tiếng Việt:
     > *"Này nó run javascript tạo á anh - mà tạo lâu ghê 😅"*
   - Và trong status ghi rõ: *"2 tiếng tạo khung hình cho video 2p"*, *"Cho khứa Sol 6 diễn tập trước vậy"*.
   - Nếu Agent đọc đúng text trên ảnh (Ground Truth) ngay từ đầu, câu trả lời sẽ cực kỳ ngắn gọn, chính xác và không bao giờ bịa ra thực thể ảo.

---

## 3. Quy Tắc & Kỷ Luật Bắt Buộc (Mandatory Invariants)

### A. Kỷ luật Chuẩn Hóa Typo Tiếng Việt (Telex Normalization Gate)
- Khi User đưa ra các từ ngữ lạ, viết hoa bất thường hoặc có dấu hiệu lỗi gõ phím Telex (`s`, `f`, `r`, `x`, `j`, `w`, `d`):
  - `dUNF` / `dunf` = `dùng` (`d-u-n-f`).
  - `k` / `ko` = `không`; `dc` = `được`; `ms` = `mới`; `vs` = `với`; `t` = `tao`; `m` = `mày`.
- **CẤM TUYỆT ĐỐI** biến một từ gõ sai/typo của User thành tên một công nghệ, thư viện, website, hoặc tool AI mới (ví dụ: cấm bịa ra `dUNF AI`).

### B. Kỷ luật Chống Bợ Đỡ & Không Lật Mặt Mù Quáng (Anti-Sycophancy Rule)
- Khi User chất vấn *"Này là ... mà"* hoặc *"Có phải đâu"*:
  1. **KHÔNG** vội vàng quay xe xin lỗi hay nhận bừa điều mình không kiểm chứng.
  2. **QUAY LẠI ARTIFACT GỐC (Ground-Truth First):** Mở lại ảnh/log/code, chạy WinRT OCR hoặc đọc trích xuất trực tiếp xem trên hiện trường viết cái gì.
  3. Đối chiếu giữa ý User muốn nói với bằng chứng trên ảnh:
     - Nếu User hiểu đúng một phần (ví dụ User muốn nói "Dùng AI để làm chứ không phải tự code tay"): Xác nhận rõ *"Đúng là dùng AI (Sol 6 / Claude) để làm, và AI ở đây viết code JavaScript sinh từng khung hình"*.
     - Trích dẫn nguyên văn câu chữ trên ảnh làm trọng tài phán quyết.

### C. Trích Dẫn Nguyên Văn Trước Khi Tổng Hợp (Verbatim Extraction First)
Khi giải thích một bức ảnh/screenshot mạng xã hội, diễn đàn, trao đổi:
- Bắt buộc nêu rõ:
  1. **Ai đăng & Status nói gì nguyên văn.**
  2. **Ảnh đính kèm chứa cái gì thực tế.**
  3. **Tác giả và người khác bình luận cái gì nguyên văn.**
- Sau đó mới chốt 1 dòng kết luận ngắn gọn, súc tích, không bôi thêm các công nghệ ngoài lề không có trong ảnh.
