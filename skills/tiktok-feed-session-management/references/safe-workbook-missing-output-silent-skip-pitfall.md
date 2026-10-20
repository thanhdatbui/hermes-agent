# Safe Workbook Missing Output Silent-Skip Pitfall & Dual-Cluster Starvation

## 1. Bản chất Sự cố (2026-10-20 Incident)
- **Hiện tượng:** Cụm Farm Admin (Máy 201-280) bị bỏ qua hoàn toàn (Skip 100%) suốt từ 10:51 sáng đến 22:30 đêm trong tất cả các Ca nuôi (Ca 2 Row 4, Ca 3 Row 6), Watchdog ghi nhận:
  `🏢 【FARM ADMIN - MÁY 201-280】: Không có lượt chạy nào trong phiên (Chưa chạy / Bị skip)`
- **Hậu quả ngầm:** Runner không báo lỗi, không gửi alert lỗi vì đối với runner, đây là hành vi skip hợp lệ khi số tài khoản hợp lệ trả về bằng 0 (`_count_valid_accounts_for_row == 0`).

---

## 2. Nguyên nhân gốc rễ (Root Cause)

### A. Cơ chế mất file `taikhoan_run_safe.xlsx`
Khi một tiến trình cập nhật Excel (ví dụ `atomic_workbook_update`) bị lỗi verify hoặc gián đoạn giữa chừng, nhánh exception rollback kích hoạt:
```python
elif target.exists():
    target.unlink()
```
Lệnh này xóa sạch file `taikhoan_run_safe.xlsx` chính thức và chỉ để lại file tạm dot-file (như `.taikhoan_run_safe.rpqriyjb.xlsx`).

### B. Dòng code "tự hủy" trong Cron Sync Wrapper (`hermes_taikhoan_sync_cron.py`)
Trong vòng lặp đồng bộ từ file gốc `taikhoan_dat_v2_updated .xlsx` sang các file an toàn:
```python
# CODE CŨ (NGUY HIỂM):
for output in outputs:
    if not output.exists():
        continue  # <- NẾU FILE ĐÍCH CHƯA TỒN TẠI HOẶC BỊ XÓA -> BỎ QUA LUÔN!
    results.append(_run_sync(source, output, tik_dir, cluster_name=...))
```
- Khi `output.exists()` trả về `False`, script âm thầm bỏ qua file đó.
- Script vẫn cập nhật `state["source_sig"]` và `state["tik_sigs"]` rồi kết thúc với mã thành công (`exit code 0`).
- Các tick chạy tiếp theo (mỗi 5 phút) thấy signature không đổi nên tiếp tục **IM LẶNG (no_agent cron silent)**.
- Kết quả: File `taikhoan_run_safe.xlsx` của Admin vĩnh viễn không bao giờ được tạo lại, khiến toàn bộ cụm Admin chết đứng cả ngày.

---

## 3. Quy tắc khắc phục & Bất biến (Invariant)

1. **Kiểm tra thư mục cha thay vì kiểm tra file:**
   ```python
   # CODE CHUẨN:
   for output in outputs:
       if not output.parent.exists():
           continue  # Chỉ bỏ qua khi mất cả ổ đĩa / thư mục cha (ví dụ chưa mount OneDrive)
       results.append(_run_sync(source, output, tik_dir, cluster_name=...))
   ```
   Nếu thư mục cha còn tồn tại nhưng file chưa có, `_run_sync()` bắt buộc phải chạy để tạo mới và xuất bản file `taikhoan_run_safe.xlsx`.

2. **Preflight Health Gate:**
   - Trong các cron watchdog giám sát nuôi acc, nếu phát hiện `valid_accounts == 0` trên một cluster mà trước đó cluster đó có máy online, phải phát sinh cảnh báo cấu hình (`config-error: safe workbook missing or 0 accounts`) thay vì im lặng ghi nhận `Bị skip`.
