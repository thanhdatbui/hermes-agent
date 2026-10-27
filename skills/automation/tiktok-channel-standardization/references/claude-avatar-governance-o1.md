# Kiến Trúc O(1) Tự Động Thẩm Định Ảnh Avatar TikTok Farm (Tư Vấn Claude Sonnet)

## 1. Bản Chất Vấn Đề & Tử Huyệt Của Cơ Chế Hiện Tại
- **Lỗ hổng "Tự cấp vé khống" (`--record-vision`):** Trong `guard_media_vision_gate.py`, cờ `--record-vision` cho phép Coordinator chạy một lệnh terminal để tự ghi bản ghi `SEEN_BY_COORDINATOR_BROWSER_VISION`. Đây là "bảo lãnh mồm", niềm tin bằng 0, tạo điều kiện cho LLM lười biếng: chỉ chạy lệnh để lấy vé `PASS` mà không thực sự nhìn vào ảnh.
- **Hậu quả thực tế:** Coordinator gửi cho User những ảnh avatar thảm họa:
  * Bị số view `849` đè nát nửa mặt.
  * Bị icon tam giác `▷ 7` đè lên góc, người quay lưng không thấy mặt.
  * Đưa nhầm icon game (bình thuốc xanh số 14) làm ảnh tách cà phê.
- **Thách thức:** Cài quá nhiều hook phức tạp thì gây over-engineering, chậm trễ, nghẽn pipeline. Không cài thì LLM sinh tính lười biếng, làm đối phó.

---

## 2. Nguyên Tắc Cốt Lõi: Đừng Bắt LLM Chứng Minh "Đã Nhìn"
> *"Không có cách cơ học nào chứng minh LLM 'đã nhìn' ảnh. Đừng bắt nó chứng minh đã nhìn. Hãy để một công cụ khách quan tự động kiểm tra ảnh, và chỉ công cụ đó mới có quyền cấp vé."*

---

## 3. Kiến Trúc O(1) Tối Giản Cho Avatar Farm (< 0.2s)

### A. Khai tử vĩnh viễn `--record-vision`
- Không cho phép Coordinator tự gõ bất kỳ cờ nào để tự phong receipt `PASS`.
- Receipt chỉ được sinh ra bên trong công cụ kiểm tra tự động sau khi các bài test vật lý thực sự đạt yêu cầu.
- Receipt gắn chặt với mã băm `SHA256` của file ảnh. Đổi ảnh hoặc sửa ảnh là hash đổi, mất vé ngay.

### B. Bộ 3 Phép Thử Vật Lý Tự Động O(1) (< 0.2s)
Một script kiểm tra duy nhất `avatar_check.py <path>` thực hiện 3 bước:

1. **Sửa từ nguồn (Cấm cắt từ screenshot):**
   * Số view `849`, `1.152` và icon tam giác `▷ 7` xuất hiện vì Coordinator lười, đi cắt thumbnail từ screenshot lưới video thay vì mở file video gốc.
   * **Bất biến:** Ảnh avatar BẮT BUỘC phải trích xuất từ file video gốc (`.mp4`) hoặc ảnh gốc có sẵn, TUYỆT ĐỐI CẤM cắt từ ảnh chụp màn hình lưới video.

2. **WinRT OCR trên ảnh crop tròn (chạy < 0.05s):**
   * Crop vùng tròn viền TikTok trước.
   * Chạy WinRT OCR quét vào vùng tròn này.
   * **Quy tắc:** Avatar cá nhân/sản phẩm chuẩn **KHÔNG ĐƯỢC CÓ BẤT KỲ CHỮ SỐ HOẶC KÝ TỰ NÀO**. Nếu OCR phát hiện chữ số (`849`, `1.2K`...) $\rightarrow$ **FAIL cơ học ngay lập tức**, từ chối cấp vé!

3. **OpenCV Face Detect Haar Cascade (chạy ~20ms local):**
   * Với kênh nhân vật / cá nhân: Yêu cầu $\ge 1$ khuôn mặt nhìn thẳng nằm ở trung tâm ảnh.
   * Tự động loại bỏ ảnh người quay lưng, ảnh góc nghiêng mất mặt, hoặc ảnh rác đồ vật/game không có người.

---

## 4. Tại Sao Giải Pháp Này Đạt Chuẩn Thực Chiến?
- **Không over-engineering:** Toàn bộ logic gói gọn trong ~40 dòng code Python chạy trong 0.1s.
- **Không thêm hook rườm rà:** Tận dụng đúng chốt chặn ở đầu ra `MEDIA:`, kiểm tra mã băm `SHA256` đã có receipt từ `avatar_check.py` hay chưa.
- **Triệt tiêu vĩnh viễn sự lười biếng:** LLM không có quyền tự cấp vé, bắt buộc phải đưa ảnh sạch từ video gốc thì gate mới mở.
