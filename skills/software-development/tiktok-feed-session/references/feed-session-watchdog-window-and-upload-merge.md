# Feed Session Watchdog: Session Windows, Multi-Run Upload Merge & Classification Rules

## 1. Nguyên nhân lỗi Session Window lọt khe và sai lệch số liệu Upload

### Vấn đề 1: Khung giờ Session Window quá hẹp (`SESSION_WINDOWS`)
- Trước đây, `SESSION_WINDOWS` cấu hình Ca 1 Phiên 3 bắt đầu từ `09:30 - 12:00`.
- Trên thực tế, cron feed runner phân bổ lượt chạy chính Phiên 3 sớm từ khoảng `09:00 - 09:16` (ví dụ run `row-2-091645` lúc 09:16:45).
- Do `09:16 < 09:30`, run chính bị rớt khỏi Phiên 3 hoặc rơi về Phiên 2. Watchdog chỉ nhìn thấy run đợt 2 lúc `10:30`, bỏ sót toàn bộ kết quả upload của 51 máy ở run 09:16.

### Vấn đề 2: Multi-Run Idempotency & Merge Upload Result
- Khi đợt 1 chạy (09:16), 51 máy upload thành công (`status: success, exit_code: 0`).
- Khi đợt 2 chạy (10:30), hệ thống kiểm tra idempotency thấy máy đã đăng video trong shift nên trả về `reason: already_uploaded_in_shift` với `status: skipped`.
- Nếu `merge_upload_result` không giữ trạng thái `success` của run trước, hoặc run trước bị lọt ra ngoài window, watchdog chỉ thấy 70 máy bị `already_uploaded_in_shift` và báo thành "Bỏ qua" hoặc "Lỗi script", trong khi thực tế 51 máy đã đăng video thành công.

---

## 2. Quy tắc chuẩn hóa cho `feed_session_watchdog.py`

### Bất biến 1: Khung giờ `SESSION_WINDOWS` liên tục, không lọt khe
- **Ca 1 (Sáng)**:
  - Phiên 1: `06:00` - `07:30`
  - Phiên 2: `07:30` - `09:00` (trước đây `09:30`)
  - Phiên 3: `09:00` - `12:00` (trước đây `09:30 - 12:00`, bao trọn các run từ 09:00 trở đi)
- **Ca 2 (Chiều)**:
  - Phiên 1: `12:00` - `13:40`
  - Phiên 2: `13:40` - `15:15`
  - Phiên 3: `15:15` - `18:30`
- **Ca 3 (Tối)**:
  - Phiên 1: `18:30` - `20:00`
  - Phiên 2: `20:00` - `21:45`
  - Phiên 3: `21:45` - `23:59`

### Bất biến 2: Logic `merge_upload_result` bảo toàn Success
```python
def merge_upload_result(prev, new):
    if not prev:
        return new
    if not new:
        return prev
    prev_success = (str(prev.get("status") or "").lower() == "success" and int(prev.get("exit_code", 0) or 0) == 0)
    new_success = (str(new.get("status") or "").lower() == "success" and int(new.get("exit_code", 0) or 0) == 0)
    
    # Nếu run trước đã success và run sau chỉ là skipped/already_uploaded_in_shift -> giữ Success
    if prev_success and not new_success:
        return prev
    if new_success:
        return new
    return new
```

### Bất biến 3: Tối ưu I/O Single-Pass Directory Traversal
Tránh gọi `glob(recursive=True)` 3 lần riêng biệt cho từng run directory (gây timeout 900s). Duyệt thư mục `machines/machine_*` trong 1 lượt duy nhất để đọc cùng lúc:
- `summary.txt` (Feed status)
- `follow_result.json` (Follow status)
- `upload_result.json` (Upload status)

---

## 3. Điều phối Coordinator vs Subagent
- **BẮT BUỘC Turn 1**: Khi nhận task điều tra/sửa lỗi từ người dùng, Coordinator **BẮT BUỘC gọi `delegate_task`** để Subagent phân tích hiện trường và sửa mã nguồn.
- Coordinator **CẤM** tự ý chạy các vòng lặp debug/inspect dài dòng trực tiếp trên turn chính.
