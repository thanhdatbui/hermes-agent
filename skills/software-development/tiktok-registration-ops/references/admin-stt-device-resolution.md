# Phân giải Device cho dải STT Máy Admin (201+) trong Tiktok_Reg

## Bối cảnh & Vấn đề
- Repo: `D:/Taadaa/Tiktok_Reg/social_reg_v1.py`
- Máy Kibe (máy A): dải STT 1–80, danh sách `ACCOUNTS` được hardcode sẵn.
- Máy Admin (máy B): dải STT 201–280. Ban đầu không có trong `ACCOUNTS`, dẫn đến lỗi khi gọi `social_reg_v1.py 201`:
  `Không có STT 201` và thoát ngay lập tức (`sys.exit(1)`).

## Cơ chế Phân giải Động (`resolve_account_for_stt`)
Hàm `resolve_account_for_stt(stt, target_device=None, preferred_email=None, inventory_workbook=None)` thực hiện thứ tự ưu tiên:
1. **Tra cứu trong `ACCOUNTS`**: Nếu STT thuộc 1..80, lấy thông tin tài khoản mẫu. Nếu CLI truyền `target_device`, đè serial theo CLI.
2. **Ưu tiên CLI `target_device`**: Khi chạy dạng `python social_reg_v1.py <device_serial> <stt>` (từ `_run_all_targets.py`), nếu không có trong `ACCOUNTS` thì dùng ngay `target_device`.
3. **Fallback qua `TARGET_INVENTORY_WORKBOOK`**:
   - Kiểm tra biến môi trường `TIKTOK_REG_TARGET_INVENTORY_WORKBOOK` (được cấu hình qua `taadaa_host.py` hoặc host config của Admin, trỏ về `taikhoan_run_safe.xlsx`).
   - Gọi `scripts.target_inventory.resolve_machine_device(stt, inventory_workbook)`.
   - Tạo account dict tổng hợp: `{"stt": stt, "device": resolved_device, "email": preferred_email or "", "pass": ""}`.
4. **Báo lỗi đóng kín (Fail-Closed)**:
   - Chỉ khi cả 3 nguồn trên đều không tìm thấy device mới báo lỗi:
     `Không tìm thấy device cho STT {stt} trong ACCOUNTS lẫn inventory workbook` và thoát mã `1`.

## Điểm mấu chốt tránh Concurrency Block
- Trong `_process_mentions_known_target(cmd)`: Nếu process khác đang chạy trên dải 201+ (vd `python social_reg_v1.py 202`), hàm cũng tra cứu `TARGET_INVENTORY_WORKBOOK` thay vì chỉ duyệt `ACCOUNTS`.
- Điều này ngăn `preflight_concurrency_gate` phân loại nhầm process thành `TRACKING_WRITER_UNKNOWN` và block oan máy đang chạy.

## Lệnh kiểm thử
Test tập trung:
```bash
D:/Taadaa/python-envs/automation/Scripts/python.exe -m pytest tests/test_admin_stt_resolution.py
```
Gồm 7 test case kiểm tra: absence khỏi `ACCOUNTS`, inventory fallback, preferred email, CLI override, missing STT, env var override và CLI error string.
