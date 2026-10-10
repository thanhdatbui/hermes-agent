# Hotmail Lifecycle State Reconciliation & Dual-OAuth Guard

Patterns for diagnosing and reconciling Hotmail/GPM lifecycle state between independent trackers and batch supervisor runners.

## 1. Nguyên nhân gây lệch State (State Drift)
- **Tool chạy độc lập ngoài Supervisor**: Khi chạy script lẻ (ví dụ `gpm_change_hotmail_security.py` can thiệp thủ công hoặc qua watchdog khác), kết quả thành công được ghi vào `hotmail_changed_tracker.json`, nhưng file state tổng của supervisor (`batch_gpm_5profiles_supervisor_state.json`) không tự biết, dẫn đến tài khoản vẫn mang trạng thái cũ (`CHANGE_INFO` / `BLOCKED`).
- **Lỗi kết nối hạ tầng tạm thời (Transient GPM Downtime)**: Khi GPM tắt máy (`WinError 10061: Connection refused`), các profile đang lookup/create bị đánh dấu `BLOCKED`. Khi GPM API online trở lại, các tài khoản này cần được unblock về `PENDING` và xóa `last_result` cũ để không bị báo cáo là lỗi vĩnh viễn.
- **Tài khoản chuyển Stage trước khi đủ điều kiện**: Trước khi có Dual-OAuth Gate (2026-10-08), các tài khoản ngâm đủ 7 ngày tự động nhảy lên `CHANGE_INFO`. Nếu chưa có Codex OAuth trên cả 2 server (:20129 và :20128), chúng bị chặn đổi pass hoặc fail. Cần trả về `WAIT_7D` (`WAITING`).

## 2. Quy trình Reconcile chuẩn (Standard Reconciliation Flow)
1. **Đối soát Tracker với State tổng**:
   - Quét `hotmail_changed_tracker.json` lấy danh sách `changed_emails`.
   - Nếu email đã đổi pass thành công trong tracker nhưng supervisor state != `DONE` / `COMPLETED`: Cập nhật ngay `stage = "DONE"`, `status = "COMPLETED"`.
2. **Kiểm tra Dual-OAuth Gate cho Stage `CHANGE_INFO`**:
   - Query SQLite của OmniRoute (`provider_connections`, provider='codex') và 9Router (`providerConnections`, provider='codex').
   - Tài khoản ở `CHANGE_INFO` mà thiếu 1 trong 2 server: Lập tức hạ về `WAIT_7D` (status `WAITING`), gán detail rõ ràng `Waiting for Dual-OAuth (omni=..., 9router=...)`.
3. **Phục hồi tài khoản kẹt hạ tầng**:
   - Kiểm tra `GPMClient.check_health()` hoặc endpoint `http://127.0.0.1:19995/api/v3/profiles`.
   - Nếu GPM đã 200 OK: Chuyển các tài khoản bị `BLOCKED` do `NewConnectionError` về `PENDING`, dọn `last_result = None`.

## 3. Tự động hóa chống hồi quy (In-Code Auto-Reconciliation)
Trong hàm `load_state()` của `batch_gpm_5profiles_supervisor.py`, luôn nhúng đoạn auto-reconcile:
```python
ch_tracker_path = STATE_PATH.parent / "hotmail_changed_tracker.json"
if ch_tracker_path.is_file():
    try:
        ch_map = json.loads(ch_tracker_path.read_text(encoding="utf-8")).get("changed_emails", {})
        ch_set = {c.strip().lower() for c in ch_map}
        for info in profiles.values():
            if (info.get("email") or "").strip().lower() in ch_set:
                info["stage"] = "DONE"
                info["status"] = "COMPLETED"
    except Exception:
        pass
```

## 4. Kiểm chứng hình ảnh lỗi Hotmail Login (Gate 6 OCR)
- Khi Hotmail login báo fail: Không đoán mò lỗi proxy hay code.
- Dùng WinRT OCR đọc ảnh `outputs/screenshots/post_login_*.png`.
- Nếu có dòng `"Mật khẩu đó không đúng với tài khoản Microsoft của bạn"`: Xác nhận lỗi SAI MẬT KHẨU từ nguồn bán, duy trì cooldown 48h để bảo vệ dải IP, không retry mù.
