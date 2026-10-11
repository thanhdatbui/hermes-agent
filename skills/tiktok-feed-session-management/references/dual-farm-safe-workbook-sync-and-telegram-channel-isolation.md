# Dual-Farm Safe Workbook Sync & Telegram Channel Isolation

## 1. OneDrive Conflict & Target Safe Workbook Liveness (Dual-Farm)

### Symptom
- Farm Admin (máy 201–280) biến mất hoàn toàn khỏi báo cáo phiên nuôi acc (`feed_session_watchdog.py`).
- Không có thư mục live run được tạo dưới `D:\Taadaa\runtime\admin\live\<YYYY-MM-DD>\`.
- Log của `tiktok_runner.py`:
  ```text
  tiktok_runner: Safe workbook khong ton tai: D:\OneDrive\TaadaaData\admin\taikhoan_run_safe.xlsx
  tiktok_runner [admin]: Row X co 0 account hop le trong D:\OneDrive\TaadaaData\admin\taikhoan_run_safe.xlsx, skipping current tick.
  ```

### Root Cause
1. **OneDrive Sync Conflict:** Cả hai máy Master Kibe (`DESKTOP-3PFPGQC`) và Remote Admin (`Admin-PC`) cùng chạy tiến trình sync ghi đè vào thư mục chia sẻ OneDrive `D:\OneDrive\TaadaaData\admin\`. OneDrive phát hiện collision và đổi tên file đích thành các bản conflict (`taikhoan_run_safe-Admin-PC-XX.xlsx` hoặc `taikhoan_run_safe-DESKTOP-3PFPGQC-XX.xlsx`), làm file gốc `taikhoan_run_safe.xlsx` biến mất.
2. **Sync Cron Silent Skip Anti-Pattern:**
   - Trong `hermes_taikhoan_sync_cron.py`: Script so sánh signature của file nguồn (`taikhoan_dat_v2_updated .xlsx` và các file `TikN.xlsx`). Nếu file nguồn không đổi mtime/size, script trả về `0` (silent) mà **không kiểm tra file đích `taikhoan_run_safe.xlsx` có còn tồn tại trên đĩa hay không**.
   - Vòng lặp sync có điều kiện chết người: `if not output.exists(): continue`. Khi file đích bị mất do OneDrive conflict, script bỏ qua không tạo mới!
   - Hậu quả: File đích vĩnh viễn không được tái tạo cho đến khi can thiệp thủ công.

### Invariant & Quy Tắc Khắc Phục
- **Target Liveness Check:** Cron sync bắt buộc kiểm tra `if not all(out.exists() for out in outputs): force_sync = True`. Dù file nguồn không đổi, nếu file đích bị mất trên đĩa thì BẮT BUỘC phải trigger sync tái tạo ngay lập tức.
- **Cấm Skip Khi File Chưa Tồn Tại:** TUYỆT ĐỐI CẤM `if not output.exists(): continue` trong vòng lặp ghi file đầu ra.
- **Tái tạo khẩn cấp (Emergency Recovery):**
  ```bash
  python "D:/Taadaa/tiktok-luot nuoi acc/scripts/sync-safe-workbook.py" \
    --source "D:/OneDrive/TaadaaData/admin/taikhoan_dat_v2_updated .xlsx" \
    --output "D:/OneDrive/TaadaaData/admin/taikhoan_run_safe.xlsx" \
    --tik-dir "D:/OneDrive/TaadaaData/admin"
  ```

---

## 2. Kỷ Luật Phân Luồng & Cô Lập Báo Cáo Telegram (Channel Isolation)

### Business Rule & User Invariant
Báo cáo phiên nuôi acc (`feed_session_watchdog.py`) phải được bóc tách TRIỆT ĐỂ 100% theo đúng nghiệp vụ và nhóm Telegram đích:
- **Nhóm `Tiktok Luot Nuoi Acc` (`-5377611430`):** ĐỘC QUYỀN LƯỚT FEED. Tuyệt đối không chứa bất kỳ dòng header hay chi tiết nào của Follow chéo hoặc Upload video.
- **Nhóm `Tiktok Follow` (`-5127276494`):** ĐỘC QUYỀN FOLLOW CHÉO (Module 1 bù, Module 2 anchor, nhả follow, cooldown IP/máy).
- **Nhóm `Tiktok video` (`-5435853713`):** ĐỘC QUYỀN ĐĂNG VIDEO & AVATAR.

### Pitfall Trong `dispatch_split_reports()`
- **Lỗi rò rỉ (Report Leak):** Khi chia nhỏ khối báo cáo, CẤM append dòng tóm tắt `fl_s[0]` (Follow chéo) hoặc `up_s[0]` (Đăng Video) vào danh sách dòng `feed_p` của Lướt Feed:
  ```python
  # SAI - Gây rò rỉ thông tin Follow/Upload vào nhóm Nuôi Acc:
  if fl_s: f_s.append(fl_s[0])
  if up_s: f_s.append(up_s[0])

  # ĐÚNG - Cô lập triệt để 100%:
  f_s = [l for l in lines if l not in fl_s and l not in up_s]
  # Không append fl_s[0] hay up_s[0] vào f_s
  ```
- **Hậu quả khi rò rỉ:** User sẽ thấy dòng `• Follow chéo (...)` xuất hiện trong nhóm Nuôi Acc và phàn nàn "sao fl chéo lại ném vào nhóm tiktok luot nuoi acc". Phải giữ nhóm Nuôi Acc sạch sẽ 100% chỉ có lướt feed.
