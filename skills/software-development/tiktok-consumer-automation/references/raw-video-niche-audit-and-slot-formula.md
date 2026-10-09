# Bóc Tách Niche Kho Video Gốc & Quy Tắc Mapping Slot Video (Raw Video Niche Audit & Slot Formula)

## 1. Bản Chất Ánh Xạ: `video gốc` vs `Folder Video`
Trong các workbook quản lý `Tik1.xlsx` đến `Tik8.xlsx` trên cả 2 cụm (Kibe & Admin):
* **`video gốc` (Input Kho Gốc `D:/video goc/<video gốc>/`)**:
  - Công thức chuẩn: $\text{video\_goc} = (Slot - 1) \times 80 + M$ (với $Slot \in [1..8]$, Máy $M \in [1..80]$).
  - **ĐÂY LÀ KHÓA CHÍNH trong `state.db` (`folders.folder_num`)**: Quyết định trực tiếp chủ đề (`niche`), `Keyword Video` và `Hashtag Pool` của kênh!
* **`Folder Video` (Output Render `D:/TIKTOK-videonuoinick/<Folder Video>/`)**:
  - Công thức chuẩn: $\text{Folder\_Video} = (M - 1) \times 8 + Slot$.
  - Đây chỉ là thư mục chứa các clip `.mp4` đã render thành phẩm của nick đó trên máy.
* **Bẫy va chạm số hiệu (Ví dụ Máy 57 - Tik 2)**:
  - `Folder Video` = $(57 - 1) \times 8 + 2 = 450$.
  - `video gốc` = $(2 - 1) \times 80 + 57 = 137$.
  - Clip render tại folder 450 thực chất được render từ video gốc **137**. Niche của kênh do folder nguồn 137 quyết định, hoàn toàn KHÔNG PHẢI folder 450!

---

## 2. Bẫy 272 Folder Đời Đầu Không Có Uploader Metadata
* **Nguyên nhân lọt lưới**: Các script đối soát tự động trước đây chỉ rà soát những folder có thông tin `uploader` YouTube trong bảng `videos` hoặc `source_channel`.
* **Kẽ hở**: Có **272 / 640 folder nguồn đời đầu** (tải trực tiếp từ TikTok/Douyin cũ) hoàn toàn không có metadata trong bảng `videos`. Khi khởi tạo farm, hệ thống đã gán tuần tự theo danh sách 80 niche mẫu (`niches_pool.txt`) từ trên xuống dưới mà không đối chiếu nội dung clip thực tế.

---

## 3. Pipeline Kiểm Toán Bằng Chứng Hiện Trường Thật (Audio Speech + WinRT OCR)
Khi đối soát các folder không có metadata uploader, tuyệt đối CẤM đoán mò theo tên hay số folder. Bắt buộc dùng pipeline bóc tách hiện trường:

1. **Trích xuất hình ảnh (Visual OCR)**:
   - Dùng `ffmpeg -ss 00:00:02 -i <video.mp4> -vframes 1` trích xuất frame tại giây thứ 2.
   - Chạy WinRT OCR (`python D:/Taadaa/tools/ocr.py <frame.jpg>`) đọc tiêu đề, phụ đề, text overlay trên clip.
2. **Trích xuất âm thanh (Speech-to-Text)**:
   - Dùng `ffmpeg -ss 00:00:00 -t 12 -i <video.mp4> -vn -acodec pcm_s16le -ar 16000 -ac 1 <audio.wav>` cắt 12 giây âm thanh đầu.
   - Dùng thư viện `speech_recognition` (Google Speech API với ngôn ngữ `vi-VN`) nhận diện lời thoại nhân vật trong video.
3. **Phân loại theo cụm từ khóa ngữ nghĩa trọng tâm**:
   - **Thú cưng (`thucung`)**: `mèo`, `chó`, `cún`, `thú cưng`, `poodle`, `chó con`, `mèo con`.
   - **Ẩm thực (`amthuc`)**: `nấu ăn`, `công thức`, `món ngon`, `vào bếp`, `gia vị`, `bữa cơm`, `mukbang`.
   - **Tin tức / Câu chuyện (`cauchuyen`)**: `công an`, `thời sự`, `tin tức`, `vụ việc`, `tin 3 phút`.
   - **Làm đẹp (`lamdep`)**: `skincare`, `chăm sóc da`, `mỹ phẩm`, `trang điểm`, `son môi`.
   - **Yoga (`yoga`)**: `yoga`, `tập yoga`, `thiền định`, `uốn dẻo`.
   - **Ô tô (`oto`)**: `ô tô`, `xe hơi`, `vô lăng`, `lái xe`, `bằng lái`.
4. **Lọc nhiễu & Chống False Positives**:
   - Từ ngữ đơn lẻ xuất hiện ngoài ngữ cảnh (ví dụ: chữ "tạ" trong "cảm tạ" hoặc "phát" trong "phát triển") không được coi là Gym.
   - Chỉ kết luận mismatch khi phát hiện các từ khóa chủ đề đặc trưng và nội dung khác biệt hoàn toàn với `niche` hiện tại.

---

## 4. Quy Trình Cập Nhật Đồng Bộ An Toàn
1. **Sao lưu trước khi ghi**:
   - `state.db` $\rightarrow$ `state.db.bak_<label>`.
   - File Excel $\rightarrow$ `<TikX>.xlsx.bak_<label>`.
2. **Ghi CSDL `state.db`**:
   - Cập nhật `UPDATE folders SET niche = ? WHERE folder_num = ?`.
3. **Ghi Excel nguyên tử (`atomic_workbook_update`)**:
   - Cập nhật đồng bộ cả sheet `TaiKhoan` (cột `Keyword Video` và `Hashtag Pool`) và sheet `Hashtag theo Folder` (cột `Keyword/Niche` và `Hashtag Pool`).
   - Thực hiện trên cả 16 file Excel của 2 cụm (`kibe` và `admin`).
4. **Chạy Test Suite Parity Verification**:
   - `pytest tests/test_farm_hashtag_parity.py`: Đảm bảo 100% 640 tài khoản có đầy đủ tag, không ô trống.
   - `pytest tests/test_hashtag_selector.py`: Đảm bảo 100% khi bốc tag đạt $3 \le \text{tags} \le 5$, $\ge 2$ tag viral chung, $\le 1$ tag ngách đúng chủ đề.
