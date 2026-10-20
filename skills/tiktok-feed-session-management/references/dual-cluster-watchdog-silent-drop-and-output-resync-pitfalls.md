# Dual-Cluster Watchdog Silent Drop & Output Workbook Resync Pitfalls

## 1. Sự Cố Nuốt Cụm Trực Tuyến Trong Watchdog (Silent Cluster Elimination)
- **Bối cảnh:** Hệ thống quản lý Dual-Cluster (`kibe` M1-80 và `admin` M201-280). Khi một phiên nuôi feed/follow hoàn tất, `feed_session_watchdog.py` duyệt qua danh sách `CLUSTERS` để tổng hợp block báo cáo cho từng cụm.
- **Cơ chế lỗi:**
  * Khi cụm Admin không có lượt chạy nào trong phiên (do bị runner skip vì workbook rỗng hoặc chưa đến ca), khối của Admin được sinh ra với định dạng:
    ```text
    🏢 【FARM ADMIN - MÁY 201-280】
    • Trạng thái: Không có lượt chạy nào trong phiên (Chưa chạy / Bị skip)
    ```
  * Trong các hàm bóc tách phân luồng chuyên biệt như `format_follow_report_from_blocks()` (nhóm `-5127276494`), logic chỉ bốc các dòng thuộc `• Follow chéo`:
    ```python
    fl_s = sec("Follow chéo")
    if fl_s:
        fl_p.append("\n".join(hdr + fl_s))
    ```
  * **Hậu quả:** Khối Admin không chứa dòng `• Follow chéo`, nhánh `if fl_s` bị bỏ qua và **hoàn toàn thiếu nhánh fallback**. Toàn bộ khối Admin bị loại bỏ im lặng khỏi bản tin Telegram. Người vận hành chỉ thấy báo cáo cụm Kibe và cho rằng Farm Admin bị sập hoặc watchdog bỏ quên.
- **Quy tắc bắt buộc:**
  * Mọi hàm bóc tách block báo cáo chuyên sâu (Follow, Upload, Tim/Comment) BẮT BUỘC phải có nhánh `else` giữ lại thông tin trạng thái để không nuốt im lặng bất kỳ cụm nào:
    ```python
    fl_s = sec("Follow chéo")
    if fl_s:
        fl_p.append("\n".join(hdr + fl_s))
    else:
        st_lines = [l for l in lines if l.startswith("• Trạng thái")]
        if st_lines:
            fl_p.append("\n".join(hdr + st_lines))
    ```

---

## 2. Invariant Kiểm Tra Tồn Tại File Đích Trong Cron Đồng Bộ Dữ Liệu
- **Bối cảnh:** `hermes_taikhoan_sync_cron.py` định kỳ 5 phút quét nguồn `taikhoan_dat_v2_updated .xlsx` và các file `Tik1..8.xlsx` để build sổ cái an toàn `taikhoan_run_safe.xlsx`.
- **Cơ chế lỗi:**
  * Script tối ưu silent cron bằng cách lưu chữ ký file nguồn (`source_sig`, `tik_sigs`). Nếu chữ ký không đổi thì thoát sớm `return 0` để không spam console.
  * Tuy nhiên, nếu file đích `taikhoan_run_safe.xlsx` bị mất trên đĩa (do lỗi xung đột đồng bộ OneDrive, thao tác dọn dẹp hoặc lỗi rename), script kiểm tra `source_sig == current[0]` thấy file nguồn không đổi nên tiếp tục thoát im lặng `return 0`.
  * Hậu quả: File safe bị mất vô thời hạn; các cron runner (`tiktok_runner.py`) đọc vào thấy 0 account hợp lệ và tự động skip toàn bộ các ca chạy của cụm đó.
- **Quy tắc bắt buộc:**
  * Kiểm tra chữ ký file nguồn để thoát sớm CHỈ ĐƯỢC PHÉP khi toàn bộ file đích hợp lệ vẫn đang hiện diện trên đĩa:
    ```python
    outputs_exist = all(out.exists() for out in outputs if out.parent.exists())
    if (state.get("source_sig") == current[0]
            and state.get("tik_sigs") in (current[1], persisted_tik_sigs)
            and not state.get("last_error")
            and outputs_exist):
        return 0  # Chỉ silent khi file nguồn không đổi VÀ toàn bộ file đích còn nguyên vẹn
    ```

---

## 3. Cạm Bẫy Khóa File OneDrive Khi Atomic Update (Dot-files Lock)
- **Hiện tượng:** Trong `automation_core.workbook.single_writer_workbook_update()`, file tạm được tạo dưới dạng dot-file `.{stem}.{rand}.xlsx` trong cùng thư mục với file đích (nằm trong thư mục OneDrive `D:\OneDrive\TaadaaData\admin`).
- **Nguyên nhân:** OneDrive client trên Windows liên tục giám sát thư mục bằng FileSystemWatcher. Khi file tạm vừa được ghi xong, OneDrive có thể lập tức chụp file lock để đồng bộ cloud, dẫn tới lệnh `os.replace` bị `PermissionError` hoặc bị ngắt quãng giữa chừng, để lại các file mồ côi `.taikhoan_run_safe.<hash>.xlsx` và làm mất file chính thức.
- **Quy tắc vận hành:** Khi phát hiện runner báo 0 account và thư mục OneDrive xuất hiện các file `.taikhoan_run_safe.*.xlsx` mồ côi, Coordinator phải nhận diện ngay đây là sự cố kẹt atomic rename của OneDrive, lập tức chạy sync thủ công O(1) khôi phục file chính và kiểm tra tính toàn vẹn qua `excel_preflight_validator.py`.
