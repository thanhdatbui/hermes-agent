# Zalo Electron Scraping & TikTok Niche Forensics (2026)

## 1. Tọa Độ Cửa Sổ & Child HWND Của Zalo PC
- **Tiến trình chính:** `Zalo.exe` (thư mục `C:\Users\Kibe\AppData\Local\Programs\Zalo\...`).
- **Cửa sổ gốc:** Title `"Zalo"` (hoặc `"Zalo - <Tên>"`).
- **Cửa sổ con xử lý nội dung:**
  - Class: `Chrome_RenderWidgetHostHWND`
  - Title: `Chrome Legacy Window`
  - Toàn bộ sự kiện bàn phím và chuột ảo bắt buộc phải gửi vào HWND của con này thông qua `PostMessageW`.

## 2. Dữ Liệu Thị Giá Kênh TikTok Mua Bán (Đối Soát Nhóm Zalo Tháng 07 - 11/2026)
- **Tệp Nữ (65% - 80% Nữ):**
  - Gái Cosplay / Biến hình: **9.500.000đ** (164K follow).
  - Edit Phim kịch tính: **4.500.000đ - 7.700.000đ**.
  - Bán hàng Affiliate (Điểm Shop 180, đã ra đơn): **4.000.000đ - 5.700.000đ**.
  - Cá nhân Nữ / Lifestyle: **2.700.000đ**.
- **Phôi Công Nghiệp (Xoay vòng vốn nhanh):**
  - Fancam Idol / Diễn viên hot (Bạch Lộc, C-Drama, Kpop): **750.000đ - 1.200.000đ**.
  - Thú cưng / Mèo cute Douyin: **1.500.000đ - 2.200.000đ**.
- **Ngách Khó Bán / Bị Dìm Giá (Dưới 500k):**
  - Cá nhân Nam: **400.000đ** (rẻ bằng 1/14 lần kênh Nữ).
  - Anime đại trà: **350.000đ**.

## 3. Bẫy Ngách Chết Thương Mại Cần Tránh Trên Farm
- Cấm cào video review thông số sản phẩm tĩnh (như case sổ còng Klong B5 100gsm) vì Vision AI của TikTok gắn cờ spam thương mại và không có khán giả đại chúng.
- Bắt buộc video phải có chuyển động của người thật hoặc thú cưng trong 3 giây đầu tiên.

## 4. Kỷ Luật Đa Ngách Cấp Nguồn (Anti-Cannibalization Matrix) & Xoay Nguồn Flop
- **Cấm dồn toàn bộ dàn 112 máy (1.268 nick) vào 1-2 ngách hẹp:** Dồn một ngách sẽ gây bão hòa cụm IP, tự bóp tương tác nhau và lệch persona của máy.
- **Phân bổ 6 Bể Nguồn chuẩn:**
  1. *Pool 1: Gái Cosplay / Biến hình* (25 máy Kibe: M1–M25) – 4.000.000đ - 9.500.000đ.
  2. *Pool 2: Edit Phim / Drama kịch tính* (15 máy Kibe: M26–M40) – 4.500.000đ - 7.700.000đ.
  3. *Pool 3: Fancam Idol / Diễn viên hot* (25 máy Kibe: M41–M65) – 750.000đ - 1.200.000đ.
  4. *Pool 4: Thú cưng / Mèo cute Douyin* (20 máy Kibe: M66–M80) – 1.500.000đ - 2.200.000đ.
  5. *Pool 5: Tâm linh / Xin vía / Quote* (15 máy Admin: M201–M215) – Kéo comment bùng nổ, chi phí 0đ.
  6. *Pool 6: Đồ gia dụng thông minh* (12 máy Admin: M216–M227) – Gắn giỏ hàng Affiliate ra đơn.
- **Xoay nguồn kênh Flop (`flop_channel_scanner.py`):**
  - **Quy tắc:** KHÔNG BỎ ACC / KHÔNG DỪNG ĐĂNG. Nick flop vẫn tiếp tục chạy lịch đăng để giữ trust thiết bị.
  - **Thực thi:** Dùng `swap_single_folder_pipeline.py` đánh số video mới từ `start_seq = (video_da_dang + 1)` để không đè trùng file cũ và bảo đảm tính liên tục trong sổ cái Excel.

