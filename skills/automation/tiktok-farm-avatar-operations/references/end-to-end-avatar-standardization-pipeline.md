# Quy Trình Chuẩn Hoá 3 Món Khép Kín & Kỷ Luật "Đổi Ava Tự Làm Cấm Hỏi" (2026-10-16)

## 1. Nguyên Tắc Cốt Lõi: "Đổi Ava Tự Làm Cấm Hỏi" (Anti-Halfway Yield)
- **Tình huống sự cố:** Khi User gửi ảnh 2 kênh và ra lệnh "Chuẩn hoá 2 kênh này", Coordinator thực hiện trích xuất frame, crop avatar 512x512, soi mắt kiểm tra, cập nhật Excel và tạo marker khóa vật lý. Tuy nhiên, sau đó Coordinator dừng lại, gửi ảnh preview vòng tròn xanh báo cáo như thể đã xong, để User phải hỏi *"Xong chưa"* rồi bức xúc: *"Là sao đéo tự làm mà t phải nhắn nữa"*.
- **Kỷ luật vận hành bắt buộc:**
  * Lệnh "Chuẩn hoá kênh" / "Đổi avatar" là một **chuỗi thực thi khép kín trọn gói (End-to-End Pipeline)**.
  * CẤM TUYỆT ĐỐI dừng lại ở bước tạo preview avatar rồi ngồi chờ User duyệt hoặc hỏi tiến độ.
  * Deliverable cuối cùng để nghiệm thu nhiệm vụ KHÔNG PHẢI là file ảnh preview cục bộ, mà là **ảnh chụp màn hình thực tế trên thiết bị thật (live profile screen)** sau khi avatar mới đã được cập nhật thành công trên app TikTok.

## 2. Chuỗi 5 Bước Thực Thi Khép Kín Bắt Buộc

### Bước 1: Trích Xuất & Crop Chuẩn Headroom (Offline / Vision Inspection)
1. Xác định chính xác $F_{src} = (Slot - 1) \times 80 + M$ và $F_{out}$.
2. Quét video nguồn trong `D:/video goc/<F_{src}>/` (ưu tiên `representative_frames` hoặc frame 2–5s các video có nhân vật chính diện).
3. Crop chuẩn 512x512 (hoặc 1080x1080), căn giữa ngũ quan, tính toán Headroom (khoảng đệm đỉnh đầu và cằm an toàn trong mask tròn bán kính $R = 256$, viền xanh lá).
4. Soi mắt thẩm định qua `browser_vision` / `ag_cli`: Xác nhận không mất chỏm tóc, không cụt cằm, không dính chữ phụ đề, watermark hay emoji.

### Bước 2: Đồng Bộ Kho & Khóa Bảo Vệ Vật Lý (SSOT Hard-Lock)
1. Ghi đè file `avatar.jpg` vào cả hai đầu:
   - `D:/video goc/<F_{src}>/avatar.jpg`
   - `D:/TIKTOK-videonuoinick/<F_{out}>/avatar.jpg` (và `D:/video goc/<F_{out}>/avatar.jpg` nếu có).
2. Tạo marker khóa vật lý chống script tự động quét đè:
   - `touch D:/TIKTOK-videonuoinick/<F_{out}>/.manual_avatar_locked`
   - `touch D:/video goc/<F_{src}>/.manual_avatar_locked`
3. Cập nhật `protected_folders` trong cả hai file registry:
   - `D:/Taadaa/data/manual_avatar_protected_folders.json`
   - `D:/Taadaa/Tiktok-video/data/manual_avatar_protected_folders.json`

### Bước 3: Đồng Bộ Bảng Quản Lý (Workbook & SQLite)
1. Cập nhật `Tik<Slot>.xlsx`:
   - Gán `Keyword Video` và `Hashtag Pool` chuẩn ngách.
   - Đặt cột `Avatar = FORCE_UPLOAD` (hoặc `OK` nếu nạp thủ công thành công).
2. Kiểm tra điều kiện Ghim (Pin): Video cao nhất phải đạt $\ge 1.000$ view mới ghim (tối đa 3 video). Nếu $< 1.000$ view thì bỏ qua pin an toàn.

### Bước 4: Tự Động Kích Hoạt Nạp Lên Máy Thật Ngay Lập Tức (Execute On Device)
1. Kiểm tra máy rảnh: `python D:/Taadaa/tools/inspect_machine.py <M>`.
2. Chạy lệnh nạp avatar đơn máy trong background:
   ```bash
   python D:/Taadaa/tools/run_avatar_batch_3accs.py --tik <Slot> --machine <M>
   ```
   (hoặc gọi launcher `run_tiktok_upload_avatar.ps1 -Tik <Slot> -ForceAvatarMachineList "<M>"`).
3. Tuyệt đối không chờ User nhắc mới bấm chạy. Kích hoạt xong thì báo trạng thái đang nạp nền và monitor.

### Bước 5: Chụp Ảnh Nghiệm Thu Profile & Báo Cáo Thực Tế (Visual Proof Gate)
1. Sau khi runner báo thành công, kéo màn hình profile thực tế từ máy thật về:
   - Screencap profile TikTok trên máy `<M>` lưu ra `D:/Taadaa/runtime/kibe/m<M>_avatar_verified.png`.
2. Soi mắt kiểm tra avatar trên profile qua `browser_vision`.
3. Trả về kết quả hoàn tất với thẻ `MEDIA:<path_anh_profile_may_that>` chứng minh hoàn thành 100%.
