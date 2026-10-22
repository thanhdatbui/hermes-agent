# Kỷ Luật Xử Lý Báo Cáo Cron & Pitfall Retry ADB Preflight (2026-10-22)

## 1. Nguyên Tắc Bất Biến: Báo Cáo Ca Chạy Là Lệnh Điều Tra Hiện Trường

### Lỗi Nguy Hiểm Của Coordinator (User Bực Mình)
Khi User gửi/forward báo cáo tổng kết ca chạy vào chat (ví dụ: `Cronjob Response: tiktok-feed-session-watchdog ... 50 máy Fail`), phản xạ sai lầm chết người của AI là:
- Đọc lại nội dung báo cáo và liệt kê lại các con số, danh sách máy.
- Viết văn giải thích lý thuyết, trấn an chung chung ("không phải do code", "để ca sau tự phục hồi").
- Đóng vai "phát thanh viên" thay vì "kỹ sư điều hành farm".

### Quy Trình Điều Phối Chuẩn Bắt Buộc
Khi nhận báo cáo ca chạy có tỷ lệ lỗi bất thường (Fail cao):
1. **Tuyệt đối cấm lặp lại nội dung đã có trong tin nhắn**: User đã đọc báo cáo trước khi ném cho bạn; việc tóm tắt lại chữ trong tin nhắn là hành vi vô dụng và gây ức chế.
2. **Truy vết hiện trường O(1) qua Run Manifest**:
   - Mở trực tiếp `D:/Taadaa/runtime/<cluster>/live/<YYYY-MM-DD>/row-<row>-<HHMMSS>/<subrun>/run_manifest.json`.
   - Đọc trường `multi_machine_summary` để lấy chính xác `stop_reason`, `final_status`, và `blocker_category` của từng máy.
3. **Đối soát trạng thái sống thực tế của thiết bị**:
   - Dùng `python D:/Taadaa/tools/inspect_machine.py <N>` hoặc danh sách `adb devices` hiện tại để so sánh.
   - Bóc tách rõ: Máy nào **mất kết nối vật lý thật** (rút dây, tắt nguồn) vs Máy nào **rớt giả trong phiên chạy** (transient socket contention lúc preflight).
4. **Tự động kích hoạt L2/Worker sửa code nếu phát hiện bug logic**:
   - Nếu lỗi do code không retry, regex sai, hoặc timeout bất hợp lý, Coordinator tự thực hiện L2 O(1) (<= 30 dòng, 1 test focused) hoặc dispatch worker sửa ngay.
   - Không chờ User phải nhắc lần 2 "fix đi".

---

## 2. Pitfall Code: `check=False` Làm Vô Hiệu Hóa Vòng Lặp Retry Trong `adb.shell`

### Hiện Tượng & Nguyên Nhân Gốc Rễ
Trong `python_runner/core/vpn_preflight.py` (và các module preflight tương tự), code kiểm tra proxy thường dùng:
```python
device_proxy = None
p_res = None
p_err = ""
for _attempt in range(2):
    try:
        p_res = adb.shell(["settings", "get", "global", "http_proxy"], timeout=15.0, check=False)
        p_err = f"{getattr(p_res, 'stderr', '')}\n{getattr(p_res, 'stdout', '')}".strip()
        val = str(getattr(p_res, "stdout", "") or "").strip()
        if val and val not in ("null", ":0", "none"):
            device_proxy = val
        break  # <- BUG NGUY HIỂM Ở ĐÂY!
    except Exception as exc:
        p_err = str(exc)
        if _attempt == 0 and ("timed out" in p_err.lower() or is_connection_lost(p_err)):
            adb.reconnect()
            time.sleep(1.0)
            continue
        break
```

### Tại Sao Lỗi?
- Khi 80 máy cùng chạy khởi động song song, daemon ADB bị nghẽn socket tạm thời. Một số lệnh `adb shell settings get ...` trả về lỗi `adb.exe: device '...' not found` với `returncode=1`.
- Vì truyền `check=False`, `adb.shell()` **KHÔNG ném Exception** mà trả về object `AdbResult(ok=False, stderr="device not found")`.
- Vì không có Exception, code rơi vào luồng bình thường và gặp ngay lệnh `break` ở `_attempt = 0`!
- Sau vòng lặp, đoạn kiểm tra `if is_connection_lost(p_err): raise ConsumerPreflightError(...)` lập tức ném lỗi, loại bỏ máy khỏi phiên chạy mà không hề cho máy cơ hội retry lần 2.
- Kết quả: Hàng loạt máy (như M41-M56) đang online khỏe mạnh bị loại oan và gắn nhãn sai là "Mất kết nối ADB/USB".

### Cách Sửa Chuẩn (Pattern Bắt Buộc)
Ngay sau khi gọi `adb.shell(..., check=False)`, phải kiểm tra `is_connection_lost` hoặc `timed out` trên kết quả trước khi `break`:
```python
if _attempt == 0 and (is_connection_lost(p_err) or "timed out" in p_err.lower()):
    try:
        if hasattr(adb, "reconnect"):
            adb.reconnect()
    except Exception:
        pass
    time.sleep(1.0)
    continue
```

---

## 3. Cải Tiến Watchdog: Đính Kèm Run ID / Thư Mục Trực Tiếp Lên Header Telegram

### Vấn Đề
Trước đây, báo cáo Telegram chỉ hiển thị:
```text
🏢 【FARM KIBE - MÁY 1-80】
• Tổng máy xử lý: 80 máy
```
Coordinator khi nhận báo cáo không biết chính xác tên thư mục run là gì (ví dụ `row-5-200018`), phải dùng script duyệt tìm thư mục live mới nhất, dễ nhầm với các subrun hoặc run cũ.

### Giải Pháp
Trong `feed_session_watchdog.py`, thêm nhãn `latest_run_label` vào header cụm:
```python
latest_run_label = sorted_run_names[-1] if sorted_run_names else ""
block_lines = [
    f"🏢 【{cluster['label']}】 (Run: {latest_run_label})",
    f"• Tổng máy xử lý: {total_machines} máy",
...
```
Giúp định vị ngay lập tức đường dẫn `D:/Taadaa/runtime/<cluster>/live/<date>/<latest_run_label>` để mở `run_manifest.json` trong 1 bước duy nhất.
