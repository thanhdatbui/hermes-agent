# Kỹ Thuật Phòng Chống Nghẽn Bus ADB & Bẫy Timeout Trong Preflight Nuôi Nick

> Ref: Khắc phục sự cố rụng hàng loạt 33 máy Kibe + 28 máy Admin trong Ca 2 (2026-10-14).

## 1. Hiện Tượng Sự Cố (Symptom & Root Cause)
- **Triệu chứng:** Hàng loạt máy bị văng ngay tại bước xuất phát với trạng thái `blocked-proxy-vpn` hoặc `prepare-tiktok failed to focus TikTok after launch`, báo lỗi giả `device is offline or ADB/USB disconnected`.
- **Nguyên nhân 1 (Timeout ngặt nghèo không retry):**
  Lệnh `adb shell settings get global http_proxy` đặt timeout cứng `3.0s` không có vòng lặp retry. Khi 25–30 worker chạy song song (đặc biệt qua socket mạng LAN sang máy Admin `192.168.110.119:5037`), lệnh ADB bị xếp hàng trễ quá 3s. Ngoại lệ `TimeoutExpired` bị bắt và quy chụp thành `ConsumerPreflightError: device is offline`.
- **Nguyên nhân 2 (Nghẽn daemon ADB do lệnh Dump thô hàng MB):**
  Hàm `get_focused_activity()` gọi liên tiếp `dumpsys window` (3MB unbuffered) và `dumpsys activity activities` (2MB unbuffered) khi ATX không trả kết quả. Hàng chục máy cùng dump hàng trăm MB text thô qua USB làm tê liệt tiến trình `adb.exe`, gây nghẽn hàng đợi (Máy 18 bị nghẽn tới 8 phút cho một lượt prepare).

## 2. Quy Tắc & Giải Pháp Chuẩn Hóa (Standard Pattern)

### A. Đọc Cài Đặt ADB với Retry & Timeout An Toàn:
- Mọi lệnh đọc trạng thái môi trường (`http_proxy`, `settings`, `dumpsys battery`) trên farm đa luồng BẮT BUỘC:
  1. Timeout tối thiểu `>= 8.0s`.
  2. Bọc vòng lặp `for _attempt in range(2)`: Nếu lần 1 gặp timeout hoặc connection lost tạm thời, bắt buộc `time.sleep(1.0)` và thử lại lần 2 trước khi quyết định fail-closed.

```python
device_proxy = None
p_res = None
p_err = ""
for _attempt in range(2):
    try:
        p_res = adb.shell(["settings", "get", "global", "http_proxy"], timeout=8.0, check=False)
        p_err = f"{getattr(p_res, 'stderr', '')}\n{getattr(p_res, 'stdout', '')}".strip()
        val = str(getattr(p_res, "stdout", "") or "").strip()
        if val and val not in ("null", ":0", "none"):
            device_proxy = val
        break
    except Exception as exc:
        p_err = str(exc)
        if _attempt == 0 and ("timed out" in p_err.lower() or is_connection_lost(p_err)):
            time.sleep(1.0)
            continue
        break
```

### B. Tối Ưu Hóa Focus Detection (Grep Trên Thiết Bị Trước Khi Dump Thô):
- TUYỆT ĐỐI KHÔNG gọi `dumpsys window` hoặc `dumpsys activity activities` thô trên đường fast-path của 80 máy.
- BẮT BUỘC ưu tiên lọc ngay trong shell Android bằng grep:
  `["sh", "-c", "dumpsys window | grep -E 'mCurrentFocus|mFocusedApp|mFocusedWindow|mTopFullscreenOpaque'"]`
  -> Chỉ trả về 1-2 dòng text qua cáp USB, triệt tiêu 99.9% lưu lượng bus ADB.
- Chỉ giữ `["dumpsys", "window"]` làm fallback cuối cùng trong danh sách candidates để bảo toàn tương thích cho các dòng ROM OEM đặc thù.

### C. Quy Ước Đặt Tên Test Cho Closeout Gate:
- `closeout_gate.py` tự động ánh xạ file source `python_runner/core/<module>.py` sang `python_runner/tests/test_<module>.py`.
- Nếu viết test nhưng đặt tên lệch (ví dụ `test_vpn_preflight_router.py` thay vì `test_vpn_preflight.py`), Closeout Gate sẽ không quét thấy test suite cho module đó và Sol High Reviewer sẽ từ chối nghiệm thu vì thiếu bằng chứng test trực tiếp.
