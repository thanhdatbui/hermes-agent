# Quy Hoạch Phân Tầng Lưu Trữ Media 2 Chiều Google Drive & Phục Hồi Video Gốc Farm Admin

## 1. Nguyên Tắc Bất Di Bất Dịch: Tách Biệt Tuyệt Đối 2 Kho Lưu Trữ Trên Google Drive
Khi giải phóng dung lượng ổ đĩa `D:` trên Farm Admin (`192.168.110.119`) sang Google Drive (`G:\My Drive`), **TUYỆT ĐỐI CẤM gom chung hoặc nhầm lẫn** giữa 2 loại dữ liệu:

1. **Kho Video Gốc (Scraped Source):**
   - **Đường dẫn Cloud:** `G:\My Drive\video_goc_backup\{f_src}\`
   - **Đường dẫn Local:** `D:\video goc may 2\{f_src}\`
   - **Quy tắc dọn dẹp:** CHỈ copy lên Cloud và xóa file local khi folder thành phẩm tương ứng đã render đủ $\ge 45$ clip (`.mp4` dung lượng $> 100\text{ KB}$).
2. **Kho Video Render Thành Phẩm (Rendered Clips):**
   - **Đường dẫn Cloud:** `G:\My Drive\video_render_backup\{f_vid}\`
   - **Đường dẫn Local:** `D:\TIKTOK-videonuoinick-admin\{f_vid}\`
   - **Quy tắc phân tầng (Hybrid Tiering):**
     * **Local:** Giữ nguyên vẹn từ `1.mp4` đến `20.mp4` (đủ gối đầu cho farm nuôi nick đăng bài 20 ngày độc lập không phụ thuộc Internet).
     * **Cloud Offload:** Đẩy toàn bộ các clip số lớn từ `21.mp4` đến `45.mp4` lên `video_render_backup\{f_vid}\`. Chỉ xóa file local sau khi kiểm tra dung lượng byte-for-byte khớp 100%.
     * **Hiệu quả:** Giải phóng ngay $\sim 350\text{ GB}$ đến $400\text{ GB}$ trên ổ `D:`, duy trì dung lượng trống an toàn $> 200\text{ GB}$ cho cả quá trình cào và render.

---

## 2. Công Thức Ánh Xạ Slot & Folder Video (Admin Slot Mapping)
Farm Admin quản lý 80 máy ($M201 \rightarrow M280$), chia làm 8 slot Tik ($1 \rightarrow 8$):
- **Từ $F_{vid}$ sang $F_{src}$:**
  ```python
  slot = (f_vid - 1) % 8 + 1
  m_idx = (f_vid - 1) // 8 + 1
  f_src = (slot - 1) * 80 + m_idx
  ```
- **Từ $F_{src}$ sang $F_{vid}$:**
  ```python
  slot = (f_src - 1) // 80 + 1
  m_idx = (f_src - 1) % 80 + 1
  f_vid = (m_idx - 1) * 8 + slot
  ```

---

## 3. Quy Trình Kéo Bù Video Gốc Bị Thiếu (Restore Service)
Khi cần khôi phục video gốc cho các folder chưa hoàn thành render:
1. **Kiểm tra tổng số clip thành phẩm thực tế:**
   $$\text{Total Rendered} = \text{Count}(\text{Local } F_{vid}) + \text{Count}(\text{GDrive } F_{vid})$$
   - Nếu $\text{Total Rendered} \ge 45$: **BỎ QUA** (đã hoàn tất, không kéo thừa làm chật đĩa).
   - Nếu $\text{Total Rendered} < 45$: Tìm $F_{src}$ tương ứng trên `G:\My Drive\video_goc_backup\{f_src}`, kéo các file `.mp4` còn thiếu về `D:\video goc may 2\{f_src}`.
2. **Kỷ luật chịu lỗi mạng (Fault Tolerance per File):**
   - File Stream của Google Drive có thể gặp `[Errno 22] Invalid argument` hoặc timeout mạng bất chợt trên từng file lớn.
   - BẮT BUỘC bọc `try...except` cho từng lệnh copy file riêng lẻ (`shutil.copy2`), ghi log cảnh báo và tiếp tục copy các file tiếp theo, không được để crash cả tiến trình quét.

---

## 4. Kỷ Luật Tiến Trình Nền (Windows OpenSSH Breakaway Pattern)
Khi điều phối chạy ngầm script kéo/đẩy qua SSH:
- Dùng cờ `0x01000008` (`CREATE_BREAKAWAY_FROM_JOB | DETACHED_PROCESS`) để process không bị OpenSSH Server tự động tiêu diệt khi session SSH đóng:
  ```python
  subprocess.Popen(
      [python_exe, "-u", "-X", "utf8", script_path],
      stdout=f_log,
      stderr=subprocess.STDOUT,
      creationflags=0x01000008
  )
  ```
- Tương thích môi trường: Không phụ thuộc vào thư viện bên thứ ba (`psutil`), sử dụng fallback sang lệnh Windows native (`tasklist` hoặc PowerShell) để kiểm tra Game Guard (`war3.exe`, `w3l.exe`, `tftclient.exe`, `league of legends.exe`).
