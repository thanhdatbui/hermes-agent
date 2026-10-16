# Pitfall: Bẫy Tái Tạo Script Ad-Hoc & Ngộ Nhận Tái Sử Dụng Avatar Cũ Trên Đĩa (2026-10-16)

## 1. Hiện Tượng & Hai Căn Bệnh Cốt Lõi

Trong phiên vận hành đổi avatar cho tài khoản đơn lẻ (Máy 59, `@vantieu11`, Tik 4), điều phối viên đã vấp phải hai sai lầm nghiêm trọng bị người vận hành (User) nhắc nhở trực tiếp:

1. **Bẫy gửi ảnh đối phó do tái sử dụng `avatar.jpg` cũ trên đĩa:**
   - Thay vì trích xuất frame mới từ video nuôi thực tế (`D:/TIKTOK-videonuoinick/<folder>/<video>.mp4`), điều phối viên lại bốc ngay file `avatar.jpg` có sẵn trong thư mục render để tạo preview.
   - Hậu quả: File `avatar.jpg` cũ này chính là hình ảnh rác/lỗi (ngón tay cầm sợi dây cáp) mà người vận hành đang muốn thay thế! Việc gửi lại ảnh y hệt cái đang hiển thị trên nick vi phạm nghiêm trọng quy tắc Soi mắt & Đổi mới.

2. **Bẫy Over-Engineering tạo script mới (`execute_m<N>_avatar.py`):**
   - Khi phát hiện TikTok trên máy đang mở sẵn một tài khoản khác (`@thutuan4916`), thay vì dùng công cụ chuẩn hóa có sẵn của Farm (`run_avatar_batch_3accs.py`), điều phối viên lại tự ý viết một script ad-hoc riêng (`execute_m59_avatar.py`) và dispatch subagent sửa đi sửa lại tới mức dính timeout 600s.
   - User phản hồi gay gắt: *"Ủa t nhớ có file up avatar r mà sao mày còn đi tạo cái ms? Ý tao là script m59_avatar.py là sao?"*

---

## 2. Kỷ Luật & Quy Tắc Khắc Phục (Invariants)

### 2.1. Cấm Tuyệt Đối Viết Script Ad-hoc Up Avatar (REUSE > EXTEND > NEW)
- Farm đã có sẵn launcher chuẩn hóa duy nhất để nạp avatar cho 1 máy đơn lẻ:
  ```bash
  python D:/Taadaa/tools/run_avatar_batch_3accs.py --tik <Tik> --machine <May>
  ```
- **Không tự ý viết script điều khiển ADB tay:** Bộ runner chuẩn `run_tiktok_upload_avatar.ps1` -> `run_tiktok_upload_batch.ps1` -> `state_machine.py` đã tích hợp đầy đủ:
  - Tự động chuyển nick (`WorkflowState.ACCOUNT_SWITCHER`) sang đúng tài khoản mục tiêu theo `Tik<N>.xlsx`.
  - Tự động dọn MediaStore, push ảnh, scan gallery, mở Profile và chọn ảnh.
  - Tự động phân loại layout và tap nút Lưu.
- **Quy tắc:** CẤM TUYỆT ĐỐI tạo bất kỳ file script nào có dạng `execute_m<N>_avatar.py`, `do_upload_avatar_m<N>.py` hay tự viết vòng lặp `monkey` / `tap` / `swipe` để up avatar thay thế cho launcher của Farm.

### 2.2. Kỷ Luật Trích Xuất Avatar Mới (Chống Up Lại Ảnh Cũ)
- Khi nhận task đổi avatar, file `avatar.jpg` đang có trong thư mục chính là ảnh cần phải bỏ đi.
- **Quy trình chuẩn 3 bước:**
  1. Trích xuất frame mới từ video nuôi chính chủ (`D:/TIKTOK-videonuoinick/<folder>/<N>.mp4`).
  2. Cắt crop cận cảnh chân dung 512x512, tạo preview đối sánh khung tròn `prev_creator_<id>.jpg`.
  3. Mở `browser_vision` soi mắt kiểm tra (đảm bảo là ảnh mới, người thật, bố cục tròn chuẩn), sau đó mới gửi `MEDIA:` xin ý kiến / nghiệm thu.
  4. Ghi đè file mới vào đồng thời 2 đầu:
     - `D:/TIKTOK-videonuoinick/<folder>/avatar.jpg`
     - `D:/video goc/<folder>/avatar.jpg`
  5. Gọi launcher chuẩn `run_avatar_batch_3accs.py`.
