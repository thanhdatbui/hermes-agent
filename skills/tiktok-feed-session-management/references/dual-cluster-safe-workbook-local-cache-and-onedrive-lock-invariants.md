# Dual-Cluster Safe Workbook Local Cache & OneDrive Lock Invariants

## 1. Hiện Tượng OneDrive Nuốt File Sổ Cái (Atomic Replace Lock Contention)
- **Cơ chế lỗi:** Khi `sync-safe-workbook.py` (sử dụng `automation_core.workbook.single_writer_workbook_update`) ghi đĩa:
  1. Tạo file tạm dot-file `.{stem}.{rand}.xlsx` trong cùng thư mục đích.
  2. Ghi dữ liệu và xác thực schema qua `openpyxl`.
  3. Gọi `os.replace(temp, target)` để hoán đổi nguyên tử.
- **Điểm gãy trên thư mục OneDrive Shared đa máy (`TaadaaData/admin`):**
  - Thư mục được sync bởi 2 máy (Kibe PC và Admin-PC).
  - Ngay khi file tạm dot-file vừa tạo xong, tiến trình OneDrive service trên cả 2 máy lập tức bắt file lock để upload.
  - Lệnh `os.replace` trên Windows bị dính `PermissionError / Access is denied`. File chính thức bị biến mất, để lại các file rác kẹt lại (`.taikhoan_run_safe.*.xlsx`).
- **Bài học bất biến:** CẤM TUYỆT ĐỐI runner chạy phụ thuộc duy nhất vào 1 đường dẫn nằm trên thư mục OneDrive sync. Bắt buộc phải có bản Local Runtime Cache trên ổ SSD nội bộ.

---

## 2. Kiến Trúc Dual-Storage Local Cache & Auto-Fallback Resolver
Để triệt tiêu nguy cơ mất sổ cái vận hành:
1. **Dual Outputs trong Cron Đồng Bộ (`hermes_taikhoan_sync_cron.py`):**
   - Cả cụm Kibe và cụm Admin đều phải xuất ra song song 2 nơi:
     * Bản Local Cache: `D:\Taadaa\runtime\<cluster>\taikhoan_run_safe.xlsx` (bản SSD cục bộ, không ai tranh chấp).
     * Bản OneDrive Mirror: `D:\OneDrive\TaadaaData\<cluster>\taikhoan_run_safe.xlsx` (bản dùng để xem và đối soát).
2. **Auto-Fallback Resolver trong Runner (`tiktok_runner.py`):**
   - Runner dùng hàm `_resolve_account_workbook(cluster)`:
     * Ưu tiên 1: Đọc bản OneDrive (`account_workbook`).
     * Fallback 2: Nếu bản OneDrive bị mất hoặc kẹt lock, lập tức tự động fallback sang bản Local Cache (`runtime_root / taikhoan_run_safe.xlsx`).
   - Đảm bảo runner 100% không bao giờ bị dừng cả ca chỉ vì OneDrive bị chậm hoặc sync lỗi.

---

## 3. Quy Tắc Kiểm Tra File Đích Tồn Tại (Output Missing Check Invariant)
- **Lỗ hổng cũ:** Cron đồng bộ chỉ kiểm tra hash nguồn (`source_sig`, `tik_sigs`). Nếu file nguồn không đổi, cron thoát im lặng (`return 0`). Khi file đích bị OneDrive xóa mất, cron nằm im không tự build lại.
- **Quy tắc bắt buộc:**
  ```python
  outputs_exist = all(out.exists() for out in outputs if out.parent.exists())
  if (state.get("source_sig") == current[0]
          and state.get("tik_sigs") in (current[1], persisted_tik_sigs)
          and not state.get("last_error")
          and outputs_exist):
      return 0  # Chỉ silent khi file đích thực sự đang tồn tại trên đĩa
  ```

---

## 4. Chống Nuốt Cụm Trong Báo Cáo Phân Tách (Watchdog Status Fallback Invariant)
- **Lỗ hổng cũ:** Hàm lọc báo cáo `format_follow_report_from_blocks()` trong `feed_session_watchdog.py` chỉ bốc dòng `sec("Follow chéo")`. Khi cụm Admin bị skip (0 lượt chạy), block của nó chỉ có dòng `• Trạng thái: Không có lượt chạy nào...` $\rightarrow$ bị watchdog drop hoàn toàn, khiến báo cáo mất tích cụm Admin.
- **Quy tắc bắt buộc:** Khi block không có section chức năng (`Follow chéo` hoặc `Đăng Video`), watchdog BẮT BUỘC fallback nhặt dòng `• Trạng thái:` để giữ nguyên block định danh `🏢 【FARM ADMIN - MÁY 201-280】` trong tin nhắn gửi Telegram.

---

## 5. Tại Sao CẤM Gộp 160 Máy Vào 1 File Excel Chung?
Khi được đề xuất dồn toàn bộ acc Admin vào Kibe để quản lý 1 file duy nhất (160 máy):
1. **Xung đột toán học Video:** Kibe dùng `F_src = (Slot-1)*80 + M`, Admin dùng `F_src = (Slot-1)*80 + (M-200)`. Gộp file sẽ làm gãy logic cào clip, render và mapping thư mục video trên 2 PC.
2. **Blast Radius (Vùng sát thương):** File chung bị hỏng hoặc kẹt lock sẽ làm tê liệt toàn bộ 160 máy thay vì chỉ cô lập 1 cụm.
3. **Hiệu năng `openpyxl`:** File 1.280 dòng chịu tải 25–40 worker đọc/ghi đồng thời gây tranh chấp file lock nặng nề và tràn RAM.
4. **Mất Cold Standby:** Phá vỡ tính độc lập của PC Admin khi cần chuyển giao làm Master khẩn cấp.
