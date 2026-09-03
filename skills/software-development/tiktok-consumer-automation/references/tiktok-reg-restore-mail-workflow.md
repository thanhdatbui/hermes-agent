# Restore mail bị xóa nhầm + xóa Audit Pending sai (Tiktok_Reg, 2026-08-06)

Nguồn gốc: run recovery xóa 3 mail CÒN SỐNG khỏi `gmail_clean_v2.xlsx` (STT 54
`eulaliaphilomenaclementina7@hotmail.com`, 57 `DerekMudryk198575@hotmail.com`,
36 `vonhuong2509200436@gmail.com`) — bug cũ xóa mail khi `_outlook_inbox_visible`
False dù `check_mailbox_alive` = ALIVE. User rule cứng: *"cấm tự tiện xoá ngoài
rule xác định mail die"*. Khi xảy ra, khôi phục theo quy trình này.

## Quy trình khôi phục 1 mail

1. **Xác định backup**: `D:\Taadaa\Tiktok_Reg\.runtime\Taadaa\Tiktok_Reg\workbook-backups\gmail_clean_v2_before_captcha_delete_<mail>_<ts>.xlsx`
   (backup được tạo NGAY TRƯỚC khi xóa). Tìm row gốc chứa mail + ghi nhớ vị trí
   (máy nào, giữa row nào).
2. **Kiểm tra source hiện tại**: mail đã có chưa (SKIP nếu có).
3. **Backup source hiện tại** trước khi sửa:
   `gmail_clean_v2_before_restore_sttXX_<ts>.xlsx`.
4. **Chèn lại đúng vị trí**: tìm index row đầu tiên có `Máy > STT` → `insert_rows`
   tại đó; copy từng cell từ backup row (dùng `data_only=False` để giữ công thức/
   format). Nếu không có row lớn hơn → append cuối.
5. **Verify**: reopen workbook, mail có mặt. In `DONE`.

Pattern script hoàn chỉnh (đã có cho 36/54/57):
`D:\Taadaa\Tiktok_Reg\scripts\restore_sttXX_source.py` — giữ nguyên pattern,
chỉ đổi TARGET_EMAIL / BACKUP / TARGET_ROW.

## Xóa Audit Pending sai

Audit Pending trong `taikhoan_dat_v2_updated .xlsx` sheet `Audit Pending` có thể
ghi `MAIL_DIE_GOOGLE_RELOGIN_REQUIRED` cho mail SỐNG (sai). Xóa row đó:
backup tracking workbook trước, `delete_rows(row_idx, 1)`, save, reopen verify
mail không còn trong sheet. Pattern: `scripts/remove_audit_sttXX.py`.

## Lưu ý

- Writer guard: các script restore/remove này chạy với env automation python +
  `PYTHONPATH=D:\Taadaa\Tiktok_Reg` — KHÔNG cần `TIKTOK_REG_WRITER_ID` vì không
  đi qua `single_writer_workbook_update` (chỉ là thao tác khôi phục thủ công có
  backup). Nhưng vẫn backup TRƯỚC mọi mutation.
- Sau khi restore, **chạy lại detector** (`_detect_clean.py`) để refresh manifest
  `artifacts/pending/tiktok_reg_clean_targets.json` — runner đọc manifest, không
  đọc live workbook.
- Quét toàn bộ mail bị xóa nhầm: so sánh emails trong source hiện tại vs tập
  hợp từ tất cả backup `gmail_clean_v2_*.xlsx` hôm đó; mail trong backup nhưng
  không trong source = đã bị xóa. Loại bỏ false positive (cột pass chứa `@`).
  Chỉ giữ xóa đúng nếu có CAPTCHA evidence (`google_captcha_<stt>_*.xml`).
