# Immediate Channel Standardization Protocol (Chuẩn Hóa Kênh Tức Thì: Ava, Hashtag, Pin)

## 1. Bối Cảnh & Nguyên Tắc Chống Thụ Động (Anti-Passivity Invariant)
- **Trigger**: Khi User gửi ảnh profile kênh kèm lệnh: *"chuẩn hoá kênh này"*, *"chuẩn hoá ava hashtag pin"*, hoặc *"đổi ava nick này"*.
- **Kỷ luật tối cao**: Tuyệt đối **CẤM** dừng lại ở việc đọc log, đối soát rồi đưa ra bảng báo cáo phân tích và hỏi User *"Anh có muốn làm không?"* hay *"Có bỏ qua không?"*.
- Lệnh chuẩn hóa là **lệnh thi công trực tiếp**. Coordinator phải chủ động đưa task về **DONE** kèm đầy đủ bằng chứng thực tế thị giác (`MEDIA:`).

---

## 2. Quy Trình Chuẩn Hóa 3 Món (Avatar - Hashtag - Pin)

### Món 1: Avatar (Thay đổi & Khóa chống ghi đè)
1. **Xác định Folder**:
   - $F_{src} = (Slot - 1) \times 80 + Machine$ (`D:/video goc/<F_src>`)
   - $F_{out} = Folder\ Video$ trong file `Tik<N>.xlsx` (`D:/TIKTOK-videonuoinick/<F_out>`)
2. **Kiểm tra ảnh chuẩn**:
   - Đảm bảo `avatar.jpg` tồn tại ở cả 2 thư mục và là ảnh vuông 512x512, tỷ lệ khuôn mặt cân đối (headroom 15–20%).
3. **Kích hoạt Runner tải lên**:
   - Dù cột `Avatar` trong `Tik<N>.xlsx` đang là `OK`, cập nhật tạm thành `PENDING` trong file Excel hoặc truyền cờ force.
   - Chạy runner chuyên biệt avatar độc lập:
     ```bash
     python D:/Taadaa/tools/run_avatar_batch_3accs.py --tik <N> --machine <M>
     ```
   - Nghiệm thu exit code 0 và report JSON: `status: "AVATAR_SMOKE_SUCCESS"`, `avatar_status: "FORCED_REPLACED_VERIFIED"`.
4. **Khóa bảo vệ vĩnh viễn (Lock)**:
   - Thả marker vật lý `.manual_avatar_locked` tại 3 đầu thư mục:
     * `D:/TIKTOK-videonuoinick/<F_out>/.manual_avatar_locked`
     * `D:/video goc/<F_src>/.manual_avatar_locked`
     * `D:/video goc/<F_out>/.manual_avatar_locked`
   - Đăng ký folder vào `manual_avatar_protected_folders.json`.

---

### Món 2: Hashtag & Niche
1. **Đối soát ngách**:
   - Soi nội dung video trên kênh để xác định đúng niche (Cười, Gia đình, Gái xinh, Công việc...).
2. **Cập nhật Workbook**:
   - Ghi đúng Keyword Video và Hashtag Pool tương ứng vào dòng của máy trong `Tik<N>.xlsx`.
3. **Khóa chống Cron 15 phút ghi đè**:
   - Đăng ký $F_{src}$ và $F_{out}$ vào `D:/Taadaa/data/manual_hashtag_protected_folders.json`.

---

### Món 3: Pin Top Video
1. **Quy chuẩn View ghim**:
   - **Ngưỡng kích hoạt ghim**: View $\ge \mathbf{1.000}$ view.
   - Nếu video cao nhất chưa đạt 1.000 view: Báo cáo rõ ràng chưa đủ điều kiện view để ghim (tránh ghim rác làm loãng đề xuất kênh).
2. **Nếu đủ điều kiện ghim ($\ge 1.000$ view)**:
   - Chạy tool ghim tự động:
     ```bash
     python D:/Taadaa/tools/pin_top_videos.py --account <username> --min-views 1000
     ```

---

## 3. Cạm Bẫy Nghi Ngờ "Offline" Khi Mount USB
- **Hiện tượng**: `inspect_machine.py <M>` trả về `device not found` do cổng USB của máy vừa cắm lại hoặc hub USB đang re-enumerate (chỉ thấy 40-50/78 máy trong `adb devices`).
- **Quy tắc xử lý**:
  - **CẤM** vội vã báo User "máy offline xin phép dừng".
  - Chờ 5–10s và chạy `adb devices`. Nếu máy xuất hiện lại, tiếp tục ngay lập tức quy trình thực thi.

---

## 4. Nghiệm Thu Thị Giác (Gate 6 & Soi Mắt Đọc Ảnh)
- Thu thập ảnh chụp màn hình từ runner:
  * `avatar-save-surface-guard.png` (màn hình crop/lưu avatar).
  * `avatar-uploaded-confirmed.png` (màn hình sửa hồ sơ với thumbnail mới).
- Gọi `browser_vision` soi mắt kiểm tra đúng thumbnail, đúng profile trước khi gửi kèm thẻ `MEDIA:<path>`.
