# Safe Workbook Sync Deadlock & Watchdog Taxonomy Refinement (2026-10-20)

## 1. Safe Workbook Sync Deadlock Pitfall (`output.exists()` trap)

### Triệu chứng & Sự cố thực tế
Cụm Farm Admin (80 máy: M201-M280) bị skip toàn bộ 100% các tick nuôi acc trong suốt cả ca chiều và tối mà không có bất kỳ thông báo lỗi nào trên Telegram:
```text
🏢 【FARM ADMIN - MÁY 201-280】
• Trạng thái: Không có lượt chạy nào trong phiên (Chưa chạy / Bị skip)
```

### Nguyên nhân cốt lõi
1. **Dòng code sai trong `scripts/hermes_taikhoan_sync_cron.py`:**
   ```python
   # LỖI TAI HẠI:
   for output in outputs:
       if not output.exists():
           continue  # <- Nếu file chưa có thì BỎ QUA LUÔN, không bao giờ tạo mới!
   ```
2. **Cơ chế mất file:** Khi quá trình verify trong `single_writer_workbook_update` / `atomic_workbook_update` gặp lỗi, nhánh exception kích hoạt `elif target.exists(): target.unlink()` xóa file `taikhoan_run_safe.xlsx` trên cụm Admin và để lại file tạm dạng dot-file (ví dụ `.taikhoan_run_safe.rpqriyjb.xlsx`).
3. **Vòng lặp kẹt vĩnh viễn (Silent Deadlock):**
   - File `taikhoan_run_safe.xlsx` biến mất.
   - Mỗi 5 phút cron đồng bộ thức dậy, kiểm tra `if not output.exists(): continue` nên bỏ qua, đồng thời cập nhật `last_sync` như thể đã thành công!
   - `tiktok_runner.py` đọc vào thấy file không tồn tại -> `valid_count == 0` -> tự động skip Admin mãi mãi.

### Giải pháp bắt buộc (Invariant)
1. Trong script sync, **CHỈ KIỂM TRA THƯ MỤC CHA TỒN TẠI**, tuyệt đối không kiểm tra file đích tồn tại:
   ```python
   for output in outputs:
       if not output.parent.exists():
           continue  # Chỉ skip khi mất ổ đĩa / thư mục cha; file đích thiếu BẮT BUỘC phải tạo mới!
   ```
2. Khi tái tạo, chạy trực tiếp:
   ```bash
   python "D:/Taadaa/tiktok-luot nuoi acc/scripts/sync-safe-workbook.py" --source "<dat_path>" --output "<safe_path>" --tik-dir "<tik_dir>"
   ```

---

## 2. Phân loại Watchdog Feed Failure ("Lỗi App TikTok/Script" False Crash Wave)

### Vấn đề
18 máy bị watchdog Telegram gán nhãn `Lỗi App TikTok/Script` khiến người vận hành tưởng code Python runner bị crash, nhưng thực tế khi trích xuất `run_manifest.json`:
- 15 máy bị quá thời gian phiên (`hard outer watchdog deadline expired` hoặc `run plan max_duration_seconds exceeded`).
- 2 máy bị văng focus TikTok do Low Memory Killer (`TikTok focus lost`).
- 1 máy bị kẹt drawer switcher (`account-switcher-not-open`).

### Cập nhật bổ sung vào `classify_feed_failure` trong `scripts/watchdog/formatters.py`:
- Thêm `"tiktok focus lost"` vào nhóm `Lỗi mở/focus App TikTok`.
- Thêm kiểm tra `"hard outer watchdog deadline expired"`, `"max_duration_seconds exceeded"`, `"deadline expired"` -> trả về `Hết thời gian phiên (Timeout)`.
- Thêm kiểm tra `"account-switcher-not-open"`, `"account switcher"` -> trả về `Kẹt Account Switcher`.
Sau khi cập nhật, nhãn ảo "Lỗi App TikTok/Script" giảm về 0 máy, phản ánh chính xác tình trạng thực tế của farm.

---

## 3. Lý do Bỏ qua Reboot 17:20 & Tích tụ Nghẽn USB Bus

### Kiểm tra bằng chứng thực tế
Khi farm có vẻ không reboot ở các mốc định kỳ (05:20, 11:20, 17:20), kiểm tra ngay file log hệ thống `C:\Taadaa_Service\daily_reset.log`:
- Nếu log ghi `[SKIP] Dang co tien trinh nuoi acc giu active device lock. Bo qua reboot de khong cat ngang ca chay`: Task đã tự động bỏ qua để bảo vệ phiên chạy của thiết bị.
- **Hệ quả phần cứng:** Việc bỏ qua reboot đồng nghĩa Host Controller và các bộ Hub USB không được reset chu kỳ. Sau 9+ tiếng chạy liên tục, các thiết bị dễ bị nghẽn socket ADB hoặc sụt kết nối USB hàng loạt (40 máy rớt khỏi bus USB Host).
