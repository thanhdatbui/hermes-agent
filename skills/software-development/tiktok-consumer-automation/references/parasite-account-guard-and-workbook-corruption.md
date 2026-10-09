# Parasite Account Guard & Corrupt Workbook Resilience

## 1. Mục đích
Trên phone farm quy mô lớn (hàng trăm máy), nguy cơ một máy (ví dụ Máy 201) lấy nhầm account/email thuộc quyền sở hữu của máy khác (ví dụ Máy 22) để login hoặc reg ("nick ký sinh" / account hijacking) dẫn đến checkpoint hàng loạt, đá nick và sai lệch inventory workbook.

`parasite_guard.py` được tích hợp vào `tiktok_login_v1.py` và `social_reg_v1.py` để bảo đảm tính toàn vẹn máy ↔ account trước khi bất kỳ tác vụ nào bắt đầu.

## 2. Cơ chế cốt lõi (Parasite Account Guard)

### Xác định chủ sở hữu (`find_account_owner_stt`)
- Tra cứu danh sách workbook tracking farm:
  - `D:/OneDrive/TaadaaData/admin/taikhoan_dat_v2.xlsx`
  - `D:/OneDrive/TaadaaData/admin/taikhoan_run_safe.xlsx`
- Chuẩn hóa identifier: TikTok ID, login email, gmail username.
- Đối chiếu số thứ tự máy (`owner_stt`) trong sheet `Accounts` / `TikTok`.

### Chặn vi phạm (`assert_account_machine_binding`)
- So sánh `target_stt` (máy đang chạy) với `owner_stt` (máy sở hữu trong bảng).
- Nếu `owner_stt != target_stt`:
  - **Mặc định**: Ném `ParasiteAccountViolation`, ghi log `[telemetry:parasite-guard] action=block ...` và hủy flow ngay lập tức để bảo vệ farm.
  - **Override có chủ đích**: Nếu truyền `allow_override=True` kèm `operator_reason`, cho phép vượt qua và ghi log `[telemetry:parasite-guard] action=override ...`.

### Structured Telemetry & Audit Persistence
- Mỗi thao tác kiểm tra binding (`verify`, `block`, `override`) đều được:
  1. Print telemetry stdout: `[telemetry:parasite-guard] action=<action> target_stt=<stt> account=<acc> owner_stt=<owner> status=<status> reason=<reason>`.
  2. Ghi append dạng JSONL vào `runtime/audit/parasite_guard_audit.jsonl` (hoặc custom `audit_file`) có timestamp ISO UTC để phục vụ audit/truy vết tự động.

## 3. Khả năng chống chịu lỗi Workbook hỏng (Corrupt Workbook Resilience)

### Pitfall
Các file Excel tracking trên farm thường xuyên được đồng bộ qua OneDrive hoặc chia sẻ giữa nhiều tiến trình. Sự cố mạng hoặc crash đột ngột có thể để lại file rác hoặc file hỏng cấu trúc zip (`File is not a zip file` / `BadZipFile`).
Nếu script đọc workbook mà không xử lý ngoại lệ này, toàn bộ worker hoặc batch chạy trên máy sẽ bị crash unhandled exception.

### Giải pháp kỹ thuật
Trong hàm quét workbook (`find_account_owner_stt`):
- Bao bọc từng lần mở workbook trong `try...except Exception as exc`.
- Khi gặp workbook lỗi, in log cảnh báo có cấu trúc:
  `⚠ [parasite-guard:warning] Failed to inspect workbook {path}: {exc}`
- Không ném ngoại lệ lên caller; tiếp tục duyệt các workbook fallback hoặc trả về `None` an toàn.

### Pattern viết test kiểm thử
```python
def test_find_account_owner_stt_handles_corrupt_workbook(tmp_path, monkeypatch):
    corrupt_file = tmp_path / "corrupt.xlsx"
    corrupt_file.write_text("not an excel file")
    monkeypatch.setattr("parasite_guard.TRACKING_PATHS", [corrupt_file])
    import parasite_guard
    # Không ném ngoại lệ, log cảnh báo và trả về None an toàn
    assert parasite_guard.find_account_owner_stt("some_account") is None
```
