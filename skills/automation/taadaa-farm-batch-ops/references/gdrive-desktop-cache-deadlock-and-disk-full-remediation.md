# Google Drive Desktop Cache Deadlock & Farm Storage Recovery

## 1. Bản Chất Kỹ Thuật: Cơ Chế Đệm Của Google Drive Desktop
Trên máy trạm vận hành (Admin-PC / Kibe):
- Google Drive Desktop mount ổ ảo `G:\My Drive`.
- Cấu hình registry `ContentCachePath` (`HKLM\SOFTWARE\Google\DriveFS`) được trỏ vào ổ dữ liệu (ví dụ: `D:\GoogleDriveCache`) để chống tràn ổ hệ điều hành `C:`.
- **Cơ chế Mirror dung lượng đĩa:** Khi file được ghi vào `G:`, Google Drive bắt buộc phải ghi vào thư mục Cache đệm trước khi đồng bộ lên Cloud 5TB. Do đó, driver Google Drive **lấy dung lượng trống của ổ chứa Cache (`D:`) làm dung lượng khả dụng của ổ ảo `G:`**.

---

## 2. Vòng Lặp Nghẽn "Con Gà - Quả Trứng" (The Deadlock)
Khi ổ `D:` bị cào video hoặc render đầy 100% (`Free: 0 MB`):
1. **Ổ G: báo 0 MB Free:** Mặc dù tài khoản Cloud có 5TB trống, ổ `G:` vẫn báo `Free: 0 MB` (mirror đúng ổ `D:`).
2. **Ghi vào G: thất bại:** Mọi lệnh `copy`, `shutil.copy2` hay `robocopy` vào `G:\My Drive` đều ném lỗi ngay:
   `OSError: [Errno 28] No space left on device`
3. **Cleaner (`sync_and_clean_gdrive.py`) bị tê liệt:** 
   Script dọn đĩa tuân thủ nguyên tắc an toàn: **CHỈ XÓA LOCAL KHI BẢN COPY TRÊN G: ĐÃ TỒN TẠI VÀ KHỚP SIZE 100%**. Vì không ghi được vào `G:`, cleaner không bao giờ xóa file trên `D:`.
4. **Downloader sập:** `download_by_niche.py` khởi chạy, không thể tạo file/cache tạm trên `D:` nên crash liên tục với `exit code 1` và tự dừng.

---

## 3. Quy Trình Cứu Hộ Hiện Trường (Bootstrap & Remediation)
Khi phát hiện Downloader Admin dừng cào video kèm triệu chứng ổ D: đầy:
1. **Kiểm tra dung lượng đĩa O(1):**
   ```python
   import shutil
   print("D:", shutil.disk_usage("D:"))
   print("G:", shutil.disk_usage("G:"))
   ```
2. **Tuyệt đối không ép chạy script sync khi Free = 0 MB:**
   Mọi nỗ lực gọi `sync_and_clean_gdrive.py` lúc này đều vô hiệu và tốn thời gian timeout.
3. **Tìm và dọn các mục rác ngoài pipeline (CẤM XÓA GAME):**
   - **VÙNG BẢO VỆ GAME**: CẤM TUYỆT ĐỐI xóa bất kỳ thư mục game nào (Riot Games, League of Legends, TFT, PBE hay `D:\x`). User chơi game thật cả Live và PBE trên cả 2 máy Kibe và Admin.
   - Các mục rác an toàn để dọn đĩa: File `.log` phình to trong `D:\CodexRuntime\tiktok-video-machine2\*.log` (như `download_admin_p10.log` > 100MB), thư mục tạm `C:\Users\Admin\AppData\Local\Temp`, các bản cache/staging cũ ngoài luồng.
   - Kiểm tra an toàn tiến trình trước khi xóa: Dùng `psutil` xác nhận không có tiến trình nào đang chạy bên trong thư mục mục tiêu.
4. **Giải phóng mồi (Prime Space):**
   - Xóa thư mục rác để tạo ra tối thiểu **20 – 50 GB trống** trên `D:`.
5. **Xác nhận giải tỏa Deadlock:**
   - Kiểm tra lại `shutil.disk_usage("G:")` — ổ `G:` sẽ lập tức nhận diện dung lượng đệm mới.
   - Downloader service (`run_admin_downloader_service.py`) sẽ tự động hồi sinh `download_by_niche.py` trong tick tiếp theo mà không cần can thiệp thủ công.

---

## 4. Ngưỡng Dọn Video Gốc Bắt Buộc Đạt Chuẩn >= 45 Clip (User Invariant)
- **Bẫy xóa raw quá sớm:** Trong `sync_and_clean_gdrive.py`, điều kiện kiểm tra thư mục thành phẩm `RENDER_ROOT` bắt buộc phải là `len(rendered) >= 45`.
- **Hậu quả nếu để ngưỡng cũ 30 clip:** Khi kênh mới render được 30 clip, script tưởng đã xong nên tự động robocopy rồi xóa mất video gốc trên Admin. Kênh sẽ bị cụt nguồn và không thể render bù lên 45 clip.
- **Quy tắc bất biến:** Tuyệt đối cấm xóa raw khi `len(rendered) < 45`. Chỉ dọn và giải phóng đĩa khi kênh đã đạt trọn vẹn $\ge 45$ clip thành phẩm.
