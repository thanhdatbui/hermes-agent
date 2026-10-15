# Chuẩn Hoá Kênh 3 Món (Ava - Hashtag - Pin) & Kỷ Luật USB Hub Debounce

## 1. Bối cảnh & Mục đích
Quy trình thực thi khi nhận chỉ thị từ User: `"chuẩn hoá kênh này"` (thường kèm ảnh chụp màn hình TikTok profile Web hoặc App).
Quy chuẩn bắt buộc phải tự động kiểm tra đủ 3 món độc lập: **Avatar**, **Hashtag/Niche**, và **Ghim Top Video (Pin)**.

---

## 2. Quy trình Định Danh Kênh O(1)
1. **Trích xuất `@username`:** Dùng WinRT OCR đọc text từ ảnh (`windows-native-ocr`).
2. **Truy vết ngược vị trí Farm:**
   - Quét cột ID trong `taikhoan_dat_v2_updated .xlsx` hoặc các file `Tik1..Tik8.xlsx` để xác định:
     * Máy $m$, Slot $s$
     * Folder video render: $F_{out} = (m - 1) \times 8 + s$ (`D:/TIKTOK-videonuoinick/<F_out>`)
     * Folder video gốc: $F_{src} = (s - 1) \times 80 + m$ (`D:/video goc/<F_src>`)

---

## 3. Tiêu Chuẩn Kiểm Tra 3 Món Chuẩn Hoá

### Món 1: Avatar (Ảnh Đại Diện)
- **Kiểm tra trạng thái TikN:** Cột `Avatar` là `OK` hay `PENDING`/`FORCE_UPLOAD`.
- **Kiểm tra cờ khóa 2 tầng (SSOT & Marker):**
  1. Registry JSON: Kiểm tra cả 2 file:
     - `D:/Taadaa/data/manual_avatar_protected_folders.json`
     - `D:/Taadaa/Tiktok-video/data/manual_avatar_protected_folders.json`
     (Cả $F_{src}$ và $F_{out}$ bắt buộc phải có trong `protected_folders` và `accounts`).
  2. Marker vật lý: Kiểm tra file `.manual_avatar_locked` tồn tại trong cả 3 thư mục:
     - `D:/TIKTOK-videonuoinick/<F_out>/.manual_avatar_locked`
     - `D:/video goc/<F_out>/.manual_avatar_locked`
     - `D:/video goc/<F_src>/.manual_avatar_locked`
- **Quy tắc:** Nếu kênh đã có avatar chân dung chuẩn, bắt buộc nạp cờ khóa kép để tool quét tái sinh avatar hàng loạt không đè lại.

### Món 2: Hashtag & Niche
- **Đối soát nội dung:** Kiểm tra các video trong kênh/folder gốc có khớp với `Keyword Video` và `Hashtag Pool` trong file Tik không.
- **Khóa bảo vệ Hashtag:** Đăng ký $F_{src}$ và $F_{out}$ vào `D:/Taadaa/data/manual_hashtag_protected_folders.json`.
- Khi có cờ này, cronjob đồng bộ định kỳ 15 phút (`sync_all_tik_keywords.py`) sẽ tự động bỏ qua, không ghi đè lại niche/hashtag cũ.

### Món 3: Pin Top Videos (Ghim Video Lên Đầu)
- **Quy chuẩn ngưỡng view của Farm:**
  - Chỉ ghim video khi có **lượt xem $\ge 1.000$ view** (theo đúng rule `pin_top_videos.py --min-views 1000`).
  - **Lý do kỹ thuật:** Ghim video lẹt đẹt (< 1.000 view) sẽ làm loãng đề xuất và phá vỡ thuật toán phân phối của TikTok đối với acc nuôi.
- **Nếu video cao nhất < 1.000 view:** Báo cáo rõ ràng: *"Chưa đạt ngưỡng ghim tiêu chuẩn của farm (cần $\ge 1.000$ view)"*, tuyệt đối không tự ý ghim bừa hoặc báo lỗi.

---

## 4. Kỷ Luật Chống Ngộ Nhận "Device Offline" do USB Hub Flapping / Debounce
- **Hiện tượng thực tế:** Trên Phone Farm 80–280 máy, hub USB thường xuyên thực hiện debounce/reset bus hoặc máy cắm lại chập chờn khi có tác vụ nặng, khiến số lượng thiết bị trong `adb devices` sụt giảm tức thời (ví dụ từ 78 máy tụt xuống 42 máy).
- **CẤM TUYỆT ĐỐI:** Kết luận máy "OFFLINE" và vội vàng đánh dấu task BLOCKED sau chỉ 1 lệnh kiểm tra đơn lẻ.
- **Kỹ thuật xác minh an toàn:**
  1. Kiểm tra tổng số thiết bị gắn kết: `adb devices | grep -c device`.
  2. Nếu tổng số thiết bị tụt dưới mức bình thường ($\ge 70$ máy): Đây là dấu hiệu USB flapping. Chờ 5–10 giây rồi query lại lần 2.
  3. Kiểm tra cụm thứ hai (Admin Remote `:5037` / `admin_ssh.py`) nếu máy thuộc cụm 200+.
  4. Chỉ khi sau 2 lần retry cách nhau 10s mà serial vẫn vắng mặt trong khi tổng số máy các cổng khác vẫn đủ thì mới ghi nhận máy offline thật sự.

---

## 5. Kỷ Luật Phản Hồi Coordinator (Chống Trốn Việc)
- **CẤM TUYỆT ĐỐI:** Đặt câu hỏi vô trách nhiệm dạng *"Anh muốn em làm gì / anh muốn em bỏ qua không"*.
- **Cấu trúc báo cáo chuẩn:** Trình bày bảng đối soát 3 món:
  `| Món | Trạng thái hiện tại | Đánh giá & Khuyến nghị |`
- Đưa ra đề xuất hành động kỹ thuật cụ thể (đã sẵn sàng thực thi O(1) theo ngân sách).
