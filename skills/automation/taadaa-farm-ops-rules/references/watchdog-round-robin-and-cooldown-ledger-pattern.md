# Watchdog Round-Robin & Cooldown Ledger Pattern (Chống kẹt vòng lặp đơn Tik)

## 1. Vấn đề: Starvation Loop (Kẹt Tik đầu tiên)
Trong các watchdog chạy theo lịch cron (như `post_evening_avatar_watchdog.py`), nếu code duyệt tài nguyên/Tik theo thứ tự cố định:
```python
# CODE CŨ DỄ KẸT
for tik in ctx["target_tiks"]:
    missing = all_unuploaded.get(tik, [])
    if missing:
        trigger_batch(tik, missing)
        return 0
```
Nếu Tik đầu tiên (ví dụ `Tik 5`) có máy lỗi, máy chưa thể upload xong hoặc thất bại liên tục, mỗi nhịp cron watchdog sẽ luôn chọn `Tik 5`, bỏ đói toàn bộ các Tik phía sau (`Tik 6, 7, 8, 3, 4`).

## 2. Giải pháp chuẩn hóa: Round-Robin Cursor + Cooldown Ledger

### A. Cơ chế Round-Robin Cursor
Lưu lại cursor vị trí Tik đã chạy gần nhất trong file `state.json`:
```python
target_tiks = ctx["target_tiks"]
cursor = int(state.get("avatar_rr_cursor", 0)) % len(target_tiks)
ordered = target_tiks[cursor:] + target_tiks[:cursor]
```

### B. Ledger chống kích hoạt dồn dập (Cooldown Ledger)
Lưu lịch sử kích hoạt trong `state["avatar_launch_history"]`:
```python
# Trong trigger_avatar_batch:
now_ts = time.time()
launch_entry = {
    "tik": tik,
    "machines": machines,
    "timestamp": now_ts,
    "pid": proc.pid,
}
history = state.get("avatar_launch_history", [])
# Giữ lại trong vòng 24h hoặc tối đa 50 bản ghi
history = [h for h in history if now_ts - h.get("timestamp", 0) < 86400][-49:]
history.append(launch_entry)
state["avatar_launch_history"] = history
```

### C. Gate Cooldown khi duyệt
Khi lặp qua `ordered`:
```python
for offset, tik in enumerate(ordered):
    missing_machines = all_unuploaded.get(tik, [])
    if missing_machines:
        recent_launches = state.get("avatar_launch_history", [])
        last_for_tik = next((l for l in reversed(recent_launches) if l.get("tik") == tik), None)
        # Cooldown 30 phút (1800s) cho mỗi Tik
        if last_for_tik and (time.time() - last_for_tik.get("timestamp", 0) < 1800):
            continue
        trigger_avatar_batch(tik, missing_machines, state, host_context=ctx)
        state["avatar_rr_cursor"] = (cursor + offset + 1) % len(target_tiks)
        save_state(state, state_file=ctx["state_file"])
        return 0
```

## 3. Session Delta Report
Trong báo cáo cuối phiên (`format_report_html` / `report_final_summary`):
- Không chỉ in snapshot tĩnh (tổng số máy còn thiếu hiện tại).
- Cần bổ sung **Session Delta**: dựa vào `avatar_launch_history` của session hôm nay để báo cáo:
  - Tổng số batch đã trigger trong ca.
  - Các Tik đã được xử lý luân phiên.
  - Số máy thành công mới / số máy lỗi cần can thiệp.
