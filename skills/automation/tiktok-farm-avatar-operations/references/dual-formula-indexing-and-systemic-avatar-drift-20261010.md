# Dual Formula Indexing & Systemic Video Gốc vs Folder Video Avatar Drift (2026-10-10)

## 1. Bản chất sự cố "Cứ lệch hoài" trên toàn bộ Farm (637/640 tài khoản)
Khi Operator thắc mắc: *"Nick này thấy video gái mà sao để ava nam v... là sao cứ lệch hoài thế"*:
Qua kiểm tra toàn bộ 640 dòng trên cả 8 workbook (`Tik1.xlsx` đến `Tik8.xlsx`), phát hiện **637 / 640 tài khoản (99.5%)** có giá trị `Folder Video` khác hoàn toàn `video gốc`.

### Nguyên nhân gốc rễ kiến trúc:
Hệ thống ban đầu được đánh số theo 2 công thức toán học phân rã khác nhau:
1. **`Folder Video` (Thư mục render để bot đăng clip):**
   * Công thức: `(Máy - 1) * 8 + Tik` (Đánh số lũy tiến theo từng máy vật lý).
   * Ví dụ: Máy 62 Tik 3 $\rightarrow$ `(62 - 1) * 8 + 3 = 488 + 3 = 491`.
2. **`video gốc` (Thư mục video thô ban đầu):**
   * Công thức: `(Tik - 1) * 80 + Máy` (Đánh số chia theo từng ca Tik).
   * Ví dụ: Máy 62 Tik 3 $\rightarrow$ `(3 - 1) * 80 + 62 = 160 + 62 = 222`.

---

## 2. Bẫy phân mảnh công cụ (Dual Path Tooling Clash)
* **Luồng đăng video (`tiktok_workflow`):** Bốc video theo cột `Folder Video` (`D:\TIKTOK-videonuoinick\491\*.mp4`). Tại đây, toàn bộ clip là một bạn nữ đeo kính cận, mặc áo thể thao Nike đỏ (khớp với 2 clip hiển thị trên lưới Profile `@tyrusbwiqiw` - "Dương Chi").
* **Luồng sinh & sync avatar (`_make_avatar.py` / batch avatar dedup):** Trong các đợt chạy hàng loạt trước đây, tool lại bốc frame hoặc resolve theo cột `video gốc` (`D:\video goc\222`).
* Thư mục `222` là ngách thể thao nam / gym (`222/2.mp4` là thanh niên đeo kính râm gồng cơ bắp bicep). Tool tự động cắt trúng thanh niên này làm `D:\video goc\222\avatar.jpg`, sau đó runner đẩy ảnh này lên tài khoản TikTok Máy 62.

---

## 3. Quy tắc khóa cứng phòng ngừa (Anti-Drift Invariant)
1. **CẤM TUYỆT ĐỐI dùng `video gốc` để trích xuất avatar:**
   Mọi script trích xuất hoặc thay thế avatar BẮT BUỘC chỉ đọc theo **`Folder Video`** (thư mục video render thực tế đang đăng trên kênh).
2. **Đồng bộ 2 đầu kho theo `Folder Video`:**
   Khi sinh avatar mới, BẮT BUỘC copy file ảnh đồng thời vào cả 2 đầu kho của `Folder Video`:
   * `D:\video goc\<Folder Video>\avatar.jpg`
   * `D:\TIKTOK-videonuoinick\<Folder Video>\avatar.jpg`
   TUYỆT ĐỐI KHÔNG copy sang `<video gốc>` (sẽ làm hỏng nguồn của tài khoản khác có Folder Video mang số đó).
3. **Chống cắt avatar mù (Blind Auto-Crop Guard):**
   Trong các folder có nhiều nhân vật (sitcom, tiểu phẩm, thể thao), thuật toán cắt tự động không biết giới tính hay tên hiển thị ("Dương Chi"). Trước khi up lên máy thật, BẮT BUỘC đối chiếu frame trích xuất với thumbnail video thực tế trên profile qua Vision API (xác nhận đúng người, đúng giới tính, đúng trang phục).
