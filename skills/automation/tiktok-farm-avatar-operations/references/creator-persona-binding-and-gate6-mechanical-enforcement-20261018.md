# Creator Persona Binding & Gate 6 Mechanical Enforcement (2026-10-18)

## 1. Sự cố Lệch Creator Persona (Incident: "Ava kiểu gì v?")
- **Hiện trường:** Chuẩn hoá kênh `@huynhdiem0806` (Máy 23, Tik 3). Kênh thuộc ngách đời sống/ẩm thực, nội dung video từ Folder `179`.
- **Lỗi nhận diện:** Sổ cái `Tik3.xlsx` từng bị lệch `Folder Video = 179` nhưng `Video Goc = 183`. Coordinator máy móc bốc file `avatar.jpg` từ `D:/video goc/183/` (chân dung cô gái trẻ phong cách khác) thay vì trích xuất từ video của Folder `179`.
- **Hậu quả:** Avatar không khớp với khuôn mặt người thật xuất hiện trong các video của kênh, làm gãy creator persona và nhận diện kênh. User lập tức chất vấn gay gắt: *"Ava kiểu gì v?"*.
- **Quy tắc bất biến (Creator Persona Invariant):**
  1. Avatar của mọi tài khoản BẮT BUỘC phải trích xuất từ chính `representative_frames` của **Folder Video hiện tại** (`D:/TIKTOK-videonuoinick/<folder>/.avatar_work/representative_frames/`).
  2. Tuyệt đối CẤM lấy ảnh từ folder khác, folder cũ, hoặc ảnh mạng/ảnh kho chung khi chưa đối soát chéo với các frame video đang nuôi.
  3. Khuôn mặt creator phải chiếm 45%–60% khung hình, nhìn thẳng hoặc góc 3/4 tự nhiên, căn đúng tâm tròn 512x512 và WinRT OCR quét sạch 100% không dính text, watermark hay sticker.

---

## 2. Bẫy Vi Phạm Gate 6 & Chế Tài Cơ Học (Incident: "Sao lại vi phạm gate k gửi hình cho t")
- **Hiện tượng:** Sau khi chạy runner đổi tên thành `Huỳnh Diễm` và nạp Bio thành công, Coordinator gửi tin nhắn báo cáo kết quả bằng text nhưng **QUÊN đính kèm thẻ `MEDIA:<path>`**.
- **User bắt bài:** *"Là sao có thấy tấm hình mẹ nào đâu? Sso lại vi phạm k gửi hình cho t"*.
- **Nguyên nhân gốc rễ (Claude Sonnet 5.5 Audit):**
  1. **Bẫy phân loại sai tác vụ:** Coordinator ngộ nhận tin nhắn tổng kết là "báo cáo hành chính", quên rằng đổi tên/bio/avatar là **tác vụ có side-effect trực tiếp trên UI thiết bị thật**, bắt buộc phải có visual evidence.
  2. **Thiên kiến tối ưu hóa sai mục tiêu (Budget Panic):** Khi gần chạm trần lượt gọi, Coordinator có xu hướng "chốt câu trả lời bằng text" để kết thúc turn nhanh, cắt xén bước chụp ảnh và gắn thẻ `MEDIA:`.
- **Khóa cứng cơ học (Mechanical Enforcement trong `guard_media_vision_gate.py`):**
  - Đã tích hợp hàm `transform_llm_output_check()` kiểm duyệt kép:
    $$\text{Action Completion} \cap \text{UI Subject} \implies \text{BẮT BUỘC PHẢI CÓ THẺ } MEDIA:$$
  - Nếu tin nhắn có các từ: `da doi`, `doi thanh`, `thanh cong`, `hoan tat`, `renamed`, `da sua`, `da nap`... đi kèm đối tượng: `ten`, `biet danh`, `avatar`, `ava`, `tieu su`, `bio`, `profile`, `ho so`... mà KHÔNG CÓ THẺ `MEDIA:` HỢP LỆ $\rightarrow$ **Gate chặn đứng tin nhắn ngay tại runtime (Verdict: `MISSING_MEDIA_EVIDENCE`)**, buộc LLM phải chụp ảnh và gửi kèm bằng chứng thực tế.

---

## 3. Quy Chuẩn Launcher Avatar Đa Tik / Đa Máy
- Launcher canonical `D:/Taadaa/run_avatar_m1.py` được chuẩn hoá để nhận tham số linh hoạt:
  ```bash
  python D:/Taadaa/run_avatar_m1.py <Machine> <Tik>
  # Ví dụ: Máy 23, Sheet Tik 3
  python D:/Taadaa/run_avatar_m1.py 23 3
  ```
- Tự động gọi engine PowerShell `run_tiktok_upload_avatar.ps1` với `-Tik <Tik>` và `-ForceAvatarMachineList <Machine>`, tự động bóc tách đúng thư mục video từ `Tik<N>.xlsx`, chuyển đúng tài khoản mục tiêu và lưu artifact xác nhận `avatar-uploaded-confirmed.png`.
