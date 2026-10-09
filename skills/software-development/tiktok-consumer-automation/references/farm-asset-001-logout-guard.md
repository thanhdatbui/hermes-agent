# FARM-ASSET-001: Logout Guard Architecture & Telemetry Specs

`logout_guard.py` bảo vệ tài sản tài khoản TikTok trên toàn bộ Taadaa Phone Farm theo nguyên tắc **Fail-Closed**.

## 1. Fail-Closed Decisions
Mọi hành vi logout đều bị CHẶN TUYỆT ĐỐI (`allowed=False`, ném `LogoutForbidden`) trừ DUY NHẤT một trường hợp:
- **PARASITE** (`allowed=True`): Nick ký sinh (Nick hợp lệ có trong Excel, chính chủ thuộc `owner_stt != current_stt`, đã OCR readback xác nhận).
- **OWN_ACCOUNT** (`allowed=False`): Nick chính chủ của `current_stt` (`owner_stt == current_stt`) -> CẤM LOGOUT.
- **UNRECORDED** (`allowed=False`): Nick không có trong Excel -> Sự cố Data Desync -> CẤM LOGOUT, giữ hiện trường.
- **DUPLICATE** (`allowed=False`): Nick xuất hiện ở nhiều máy khác nhau trong Excel -> CẤM LOGOUT.
- **UNVERIFIED** (`allowed=False`): Chưa OCR readback hoặc username rỗng -> CẤM LOGOUT.
- **REGISTRY_ERROR** (`allowed=False`): File Excel không tồn tại hoặc hỏng -> CẤM LOGOUT.

## 2. Dynamic Column Header Detection
Bảng tính tracking có thể thay đổi thứ tự hoặc tên cột giữa các đợt cập nhật. `find_column_indices(headers)` tự động quét dòng header đầu tiên (`min_row=1`):
- **STT / Máy**: Header chứa `"stt"`, `"máy"`, `"may"` (Fallback: cột 0).
- **TikTok ID**: Header chứa `"id"`, `"tiktok"`, `"tik tok"`, `"username"` (Fallback: cột 2).
- **Gmail**: Header chứa `"gmail"`, `"email"`, `"mail"` nhưng **loại trừ** các cột mật khẩu như `"pass"`, `"pass mail"` (Fallback: cột 5).

## 3. Data Parsing & Fail-soft Row Validation
- `parse_stt(val)`: Chuyển đổi an toàn từ int, float, string (`"5"`, `" Máy 03 "`, `"M14"`), trả về `int` hoặc `None`.
- Vòng lặp đọc hàng `ws.iter_rows(min_row=2)` bọc try-except từng hàng: bỏ qua các dòng lỗi / hỏng mà không làm sập guard.
- Workbook luôn được đóng an toàn trong khối `finally`.

## 4. Telemetry & Incident Logging Schema
Hàm `assert_logout_allowed` ghi structured JSONL với đầy đủ 8 trường schema bắt buộc:
```python
record = {
    "timestamp": "YYYY-MM-DD HH:MM:SS",
    "code": decision.code,
    "target": decision.target,
    "current_stt": decision.current_stt,
    "owner_stt": decision.owner_stt,
    "allowed": decision.allowed,
    "detail": decision.detail,
    "evidence": evidence or {},
}
```
- **Audit Log** (`audit_log_path`, mặc định `D:/Taadaa/runtime/audit/logout_guard_audit.jsonl`): Ghi tất cả các quyết định (`allowed=True` và `allowed=False`).
- **Incident Log** (`incident_log_path`, mặc định `D:/Taadaa/runtime/audit/unrecorded_assets_incident.jsonl`): Chỉ ghi khi có vi phạm (`allowed=False`).
- Cho phép truyền custom paths vào `assert_logout_allowed(..., audit_log_path=..., incident_log_path=...)` để phục vụ unit test độc lập không làm ô nhiễm production logs.
