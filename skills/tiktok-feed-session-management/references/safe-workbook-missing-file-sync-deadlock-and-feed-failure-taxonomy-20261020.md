# Safe Workbook Missing-File Sync Deadlock & Feed Failure Taxonomy (2026-10-20)

## 1. Safe Workbook Missing-File Sync Deadlock Trap

### Triệu chứng & Hậu quả
- Cụm FARM ADMIN (Máy 201-280) bị bỏ qua 100% các tick trong ca nuôi (Row 4, Row 6) suốt cả ngày.
- Telegram báo cáo: `🏢 【FARM ADMIN - MÁY 201-280】: Không có lượt chạy nào trong phiên (Chưa chạy / Bị skip)`.
- `runner_simple_state.json` trên Admin bị đóng băng ở mốc buổi sáng sớm (ví dụ `08:00`).

### Căn nguyên gốc rễ (Root Cause)
1. **Mất file do atomic update failure:**
   - Khi chỉnh sửa file TikN (ví dụ `Tik5.xlsx`), `sync_safe_workbook` chạy qua `atomic_workbook_update`.
   - Nếu quá trình verify gặp lỗi hoặc rollback kích hoạt, nhánh exception trong `automation_core/workbook.py` gọi `elif target.exists(): target.unlink()`.
   - File `taikhoan_run_safe.xlsx` trên cụm Admin bị xóa, để lại file tạm rác dot-file (ví dụ `.taikhoan_run_safe.rpqriyjb.xlsx`).
2. **Dòng code gây deadlock trong `hermes_taikhoan_sync_cron.py`:**
   ```python
   # LỖI TỬ HUYỆT:
   for output in outputs:
       if not output.exists():
           continue  # <- File chưa tồn tại thì SKIP LUÔN, KHÔNG TẠO MỚI!
   ```
   - Bản chất: Mục đích của cron sync là tạo và cập nhật file `taikhoan_run_safe.xlsx` từ `taikhoan_dat_v2_updated .xlsx`. Nếu check `output.exists()`, một khi file bị xóa hoặc chưa tạo, cron sẽ **vĩnh viễn bỏ qua** trên mọi tick tiếp theo, trong khi vẫn ghi `last_sync` thành công giả tạo.
   - `tiktok_runner.py` gọi `_count_valid_accounts_for_row(row, workbook_path=cluster_wb)`. Khi file không tồn tại, hàm trả về `0` tài khoản $\rightarrow$ tự động skip runner.

### Quy tắc & Bản vá Invariant
- **Kiểm tra `output.parent.exists()` thay vì `output.exists()`:**
  ```python
  # CHUẨN INVARIANT:
  for output in outputs:
      if not output.parent.exists():
          continue
      try:
          results.append(_run_sync(source, output, tik_dir, cluster_name=cluster.get("name", "")))
  ```
  Chỉ skip khi ổ đĩa/thư mục cha không tồn tại (chưa mount OneDrive). Nếu thư mục cha có sẵn, **bắt buộc phải sinh mới file safe workbook**.

---

## 2. Bóc Tách "Lỗi App TikTok/Script" (Feed Watchdog Catch-all Fix)

### Bẫy gom nhóm Catch-all trong `formatters.py`
Trong `classify_feed_failure(reason)`, nhánh trả về cuối cùng là `"Lỗi App TikTok/Script"`. Bất kỳ lỗi nào không khớp từ khóa Wi-Fi, Proxy hay ADB đều bị gom vào nhãn này, khiến người dùng hiểu nhầm script Python bị crash.

### Bổ sung Token Phân loại Granular (Đã chuẩn hóa 2026-10-20)
1. **Hết thời gian phiên (Timeout):**
   - Tokens: `"hard outer watchdog deadline expired"`, `"max_duration_seconds exceeded"`, `"deadline expired"`.
   - Bản chất: Máy Samsung S7 giật lag hoặc mạng chậm khiến lượt feed vượt ngưỡng timeout quy định.
2. **Kẹt Account Switcher:**
   - Tokens: `"account-switcher-not-open"`, `"account switcher"`.
   - Bản chất: Animation drawer mở danh sách tài khoản bị khựng/chậm.
3. **Mất focus App TikTok:**
   - Bổ sung token: `"tiktok focus lost"` vào nhóm `"Lỗi mở/focus App TikTok"` (cùng với `"failed to focus tiktok"`, `"prepare-tiktok failed to focus"`, `"focused package unavailable"`).
   - Bản chất: Low Memory Killer (LMK) kill app hoặc app bị văng về Launcher.

Sau khi cập nhật, nhãn ảo "Lỗi App TikTok/Script" giảm từ 18 máy về **0 máy**, phản ánh đúng bản chất hiện trường.

---

## 3. Khóa Cửa Sổ Reboot Blackout Cho Watchdog Cuốn Chiếu (2FA/Warmup)

### Quy tắc Blackout Window
Các watchdog chạy cuốn chiếu trong ngày (như `night-tiktok-2fa-watchdog`) tuyệt đối không được kích hoạt sát giờ reboot hệ thống (`05:20`, `11:20`, `17:20`):
- Khung đệm chuẩn: 15 phút trước và sau mỗi mốc reboot:
  - `05:05 – 05:35` (trùng ca nuôi sáng `05:05 – 09:30`)
  - `11:05 – 11:35`
  - `17:05 – 17:35`
- Nếu watchdog chạy vào `17:15`, nó sẽ chiếm active device lock trên hàng chục máy farm. Đúng `17:20`, script kiểm tra an toàn reboot (`farm_preflight_daily_reset.py`) thấy có active device lock sẽ kích hoạt `[SKIP] skipped_active_device_lock` để bảo vệ tài khoản, làm mất chu kỳ reset phần cứng USB/PC.
