# Quy Chuẩn Nguồn Video & Khắc Phục Lỗi Cào/Upload (2026-10-17)

## 1. User Invariant Cốt Lõi: "Nguồn Cũ" vs "Niche Cũ"
- **Định nghĩa của User:** Khi user hỏi/yêu cầu "nguồn cũ", điều đó có nghĩa là **CHÍNH XÁC KÊNH / CREATOR GỐC** (cùng channel link, cùng tác giả/gương mặt/phong cách), **TUYỆT ĐỐI KHÔNG PHẢI chỉ là cùng niche/chủ đề**.
- **Kỷ luật 1 Folder = 1 Creator:**
  - Mỗi folder video (`D:\video goc\<ID>` hay `D:\TIKTOK-videonuoinick\<ID>`) tương ứng độc quyền với 1 kênh TikTok/YouTube gốc.
  - CẤM TUYỆT ĐỐI tải hoặc nhồi các clip của kênh khác vào trộn lẫn trong folder cũ dù cùng niche (làm loãng nhận diện kênh và gãy tệp người xem).
  - Khi kho video gốc của kênh đó thực sự cạn kiệt (kênh dừng ra video), phải dùng quy trình hoán đổi kênh chuẩn (`swap_single_folder_pipeline.py`) để thay thế trọn bộ >= 45 clip mới của 1 creator mới và cập nhật avatar đồng bộ.

## 2. Quy Tắc Proxy LAN Cho Downloader Cụm Admin (201-280)
- **Vấn đề:** Máy Admin (`192.168.110.119`) khi chạy `download_by_niche.py` qua cấu hình proxy domain ngoài `mirotik1.taadaa.click:10001..10035` bị dính lỗi `ProxyError: 502 Bad Gateway` hàng loạt do router MikroTik không hỗ trợ Hairpin NAT / loopback từ LAN ra WAN rồi quay lại LAN.
- **Giải pháp:**
  - File `proxy_pool_69.txt` trên host Admin bắt buộc phải trỏ trực tiếp về IP LAN MikroTik nội bộ: `192.168.110.2:10001..10035`.
  - Lưu ý: Downloader đọc danh sách proxy vào bộ nhớ RAM lúc khởi chạy. Sau khi sửa file proxy trên đĩa, bắt buộc phải kill tiến trình `download_by_niche.py` để service giám sát restart lại và nạp pool mới từ RAM.

## 3. Nhận Diện Header Excel Có Chú Thích Ngoặc Đơn
- **Vấn đề:** Các file Excel trên farm (`Tik1.xlsx` đến `Tik8.xlsx`) sử dụng tiêu đề cột có chú thích trong ngoặc đơn:
  - `Folder Video (Render Dich)`
  - `Video Goc (Nguon Cao)`
  Nếu code chỉ tìm chính xác `folder video` hoặc `video goc` thì sẽ bị crash `Missing required fields: Folder Video`.
- **Giải pháp:** `CANONICAL_HEADERS` trong `scripts/tiktok_workflow/account_source.py` bắt buộc phải bao gồm các alias có ngoặc đơn này (`folder video (render dich)`, `video goc (nguon cao)`).
