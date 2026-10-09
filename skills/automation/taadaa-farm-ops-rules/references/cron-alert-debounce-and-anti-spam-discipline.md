# Kỷ Luật Báo Cáo Alert Farm: Debounce / Alert-Once & Chống Spam Cron Retry

## 1. Nguyên Tắc Cốt Lõi (Invariant)
- **Lỗi nhỏ hay lớn: CHỈ ĐƯỢC BÁO DUY NHẤT 1 LẦN (Alert-Once / Debounce).**
- Tuyệt đối CẤM tình trạng mỗi tick cron lặp lại (5m, 15m, 30m) lại gửi lại cùng một nội dung lỗi vào nhóm Telegram khi lỗi chưa được giải quyết hoặc đang retry.
- User phản ánh: *"Vấn đề có lỗi ít hay nhỏ cũng báo 1 lần thôi chứ báo liên tục chi v"* → Đây là quy tắc kỷ luật tối cao đối với mọi watchdog/cron runner.

## 2. Các Bẫy Spam Phổ Biến & Cách Khắc Phục

### Bẫy 1: Retry False-Positive (Tỷ lệ fail trên tập con)
- **Triệu chứng:** Script nuôi acc/dọn cache/batch quét 80 máy. Đợt 1 thành công 78 máy, còn 2 máy lỗi socket/timeout. Đợt 2 chạy retry chỉ quét 2 máy còn lại (`target_machines = 2`). Cả 2 máy tiếp tục fail → code tính `f_count / total_attempted = 2 / 2 = 100% fail` → Ngộ nhận là "Đa số máy toàn farm sập" và bắn Farm Alert P0!
- **Khắc phục:**
  - Ngưỡng kích hoạt alert diện rộng PHẢI dựa trên tổng quy mô farm (`len(all_machines)` hoặc `f_count >= 5` và `f_count > total * 0.3`), tuyệt đối không tính trên tập con retry.

### Bẫy 2: Thiếu State Dedup / Debounce giữa các chu kỳ Cron
- **Triệu chứng:** Cron chạy mỗi 15 phút, gặp lỗi là lập tức gọi hàm bắn alert, không ghi nhớ trạng thái đã báo trước đó.
- **Khắc phục:** Bắt buộc lưu `last_alert_msg` và `last_alert_date` vào file state của cron task:
```python
# Kiểm tra dedup trong state file để chỉ báo 1 lần / ngày
already_reported = False
if STATE_FILE.is_file():
    try:
        st = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        if st.get("last_alert_date") == today_str and st.get("last_alert_msg") == alert_msg:
            already_reported = True
    except Exception:
        pass

if not already_reported:
    _send_clear_cache_alert(alert_msg)
    try:
        st = {}
        if STATE_FILE.is_file():
            st = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        st["last_alert_date"] = today_str
        st["last_alert_msg"] = alert_msg
        STATE_FILE.write_text(json.dumps(st, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
```

## 3. Quy Tắc Tự Động Phục Hồi ADB Trước Khi Timeout
- Khi thiết bị bị đơ socket ADB (`adbd` không phản hồi `shell` nhưng vẫn hiện `device` trong `adb devices`):
  - Phải có quick probe `adb -s <serial> shell echo 1` (timeout 5s).
  - Nếu timeout → chạy ngay `adb -s <serial> reconnect` trước khi timeout cả tác vụ chính (240s) và gây cascade fail.
