# Register Gmail: Merge Writer Identity & Credential Backfill Pattern

**Ngày chốt:** 2026-10-04  
**Nguyên tắc vận hành & Concurrency Guard:**

## 1. Cơ Chế Độc Quyền Ghi Excel (Single Writer Identity) & Lỗi Merge Ca Reg
- **Bối cảnh kiến trúc:**
  - Khi chạy reg Gmail song song trên nhiều máy Samsung S7 (`run_parallel.ps1`), các worker Android không ghi trực tiếp vào file Excel (`gmail_clean_v2.xlsx` / `master_gmail_manager.xlsx`) để tránh xung đột file lock (`PermissionError: [Errno 13]`).
  - Mỗi máy kết thúc ca chỉ ghi file artifact `results/machine_$Machine.success.json`.
  - Cuối ca, một tiến trình merge duy nhất (`scripts/merge_success_results.py`) đọc tất cả các file JSON này và ghi gộp vào workbook qua hàm `single_writer_workbook_update` của `automation_core.workbook`.
- **Cơ chế Writer Identity Guard:**
  - `single_writer_workbook_update` bắt buộc phải có `declared_writer_id` và `expected_writer_id`.
  - **Sự cố đứt gãy:** Trước đây, `merge_success_results.py` lấy `os.environ.get("GMAIL_EXPECTED_WRITER_ID", "")`. Nếu biến môi trường này không được export sẵn (khi chạy từ launcher, PowerShell độc lập hoặc manual), giá trị bị rỗng `""`.
  - `automation_core` lập tức kích hoạt guard: `WorkbookError: BLOCKED_EXPECTED_WRITER_ID_MISSING:gmail_clean_v2` và exit code 2.
  - Toàn bộ bước merge bị chặn đứng, không một tài khoản nào trong ca được ghi vào Excel!
- **Hậu quả dây chuyền (Missing Password Cascade):**
  - Tài khoản Gmail đã tạo thành công và profile GPMLogin đã được khởi tạo trên PC.
  - Tuy nhiên trong `master_gmail_manager.xlsx` (Sheet `Kibe_Farm_S7`) và `gmail_clean_v2.xlsx`, cột Password bị để trống (`None`).
  - Khi downstream runner (`cron_gpm_oauth_full_pool.py`) quét Excel để bốc tài khoản đi làm OAuth Antigravity / Google Session, gặp chốt an toàn `if not creds.get("password"): continue` nên bỏ qua toàn bộ, làm tắc nghẽn pool.

## 2. Chuẩn Hóa Fallback Writer ID
Trong `D:/Taadaa/register gmail/scripts/merge_success_results.py`, luôn áp dụng fallback Writer ID mặc định đồng bộ chuẩn với `gmail_reg_v10.py`:
```python
writer_id = os.environ.get("GMAIL_WRITER_ID") or "taadaa-writer-3c47f89f35e44795a79267e09fbcc72d"
expected_writer_id = os.environ.get("GMAIL_EXPECTED_WRITER_ID") or writer_id
single_writer_workbook_update(
    Path(args.workbook),
    update_workbook,
    expected_writer_id=expected_writer_id,
    declared_writer_id=writer_id,
    logical_workbook_id="gmail_clean_v2",
    backup_path=backup_path,
    verify=verify_workbook,
)
```

## 3. Quy Trình Truy Vết & Điền Bù Mật Khẩu (Credential Backfill)
Khi phát hiện tài khoản trên GPM có session nhưng trong Excel bị thiếu pass:
1. **Truy vết nguồn gốc:**
   - Tra cứu trong kịch bản batch gần nhất (`run_batch_turn2_gmails.py`, `select_turn2_candidates.py` trong `D:/Taadaa/GPM auto/scripts/`) hoặc git commit history của các repo liên quan.
   - Kiểm tra log tổng `C:/Users/Kibe/AppData/Local/register-gmail/reg_log.txt` hoặc file JSON artifact trong `D:/Taadaa/register gmail/results/`.
2. **Cập nhật đồng thời cả 2 nguồn Excel:**
   - `D:/OneDrive/TaadaaData/kibe/master_gmail_manager.xlsx` (các sheet `Kibe_Farm_S7`, `Master_All`).
   - `D:/OneDrive/TaadaaData/kibe/gmail_clean_v2.xlsx` (sheet `Gmail Accounts`).
3. **Assert Readback Verification:**
   - Luôn reload lại workbook với `data_only=True` và kiểm tra giá trị cell thực tế để đảm bảo không bị lỗi uncommitted cache hoặc lock ngầm.
4. **Xử lý tài khoản trong danh sách Cooldown:**
   - Phân biệt tài khoản sẵn sàng OAuth vs tài khoản đang dính cooldown bảo vệ (Google reCAPTCHA challenge, SMS challenge trong `oauth_pipeline_status.json` mục `cooldown_72h`).
   - Tuyệt đối giữ nguyên cooldown hẹn ngày cho tài khoản nhạy cảm, chỉ kích hoạt feeder cho các tài khoản sạch.
