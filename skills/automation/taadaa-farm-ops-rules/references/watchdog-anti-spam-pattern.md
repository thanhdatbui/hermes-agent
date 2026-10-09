# Watchdog Anti-Spam Pattern — no_agent Cron Scripts

## Bối cảnh

Hermes cron với `no_agent: true` chuyển **toàn bộ stdout** của script thẳng vào Telegram mỗi tick.
Mọi `print(...)` vô điều kiện = spam mỗi N phút.

**Trigger phát hiện:** User phản ánh "Spam lắm thế" — cron `end-of-day-clear-tiktok-cache` bắn tin rác mỗi 15 phút vì in `s_count == 0` ra stdout.

---

## Pattern chuẩn: Silent Watchdog

```python
# ❌ SAI — in báo cáo ngay cả khi không có kết quả mới:
if s_count == 0 and f_count == 0:
    return 0
# ... nhưng vẫn in s_count == 0 case ở phía dưới → spam

# ✅ ĐÚNG — Silent khi không có gì mới:
if s_count == 0:
    sys.stderr.write(f"[CRON] s_count == 0 ({f_count} failed), silent.\n")
    return 0   # stdout rỗng = không bắn Telegram
```

---

## 3 Tầng chống spam bắt buộc cho watchdog dạng retry

### Tầng 1: `s_count == 0` → return 0 ngay
```python
if s_count == 0:
    sys.stderr.write(f"[CRON] s_count == 0, silent.\n")
    return 0
```

### Tầng 2: `reported_date` dedup
Chỉ in báo cáo dài (toàn farm) đúng 1 lần/ngày.
Các đợt retry sau: in 1 dòng vắn tắt (nếu hoàn tất) hoặc im lặng.

```python
if state_data.get("reported_date") == today_str:
    if len(cleared_today) >= len(connected):
        print(f"[DỌN CACHE TIKTOK] Đã dọn bù: {s_list}. Hoàn tất {len(cleared_today)}/{len(connected)} máy.")
    else:
        sys.stderr.write(f"[CRON] Dọn bù {s_count} máy. Đã báo cáo rồi, im lặng.\n")
    return 0

# Đợt đầu tiên trong ngày → in báo cáo dài + lưu reported_date
print("\n".join(report))
state_data["reported_date"] = today_str
save_state(state_data)
```

### Tầng 3: `machine_retries` cap
Tối đa 2 lần retry/máy/ngày để tránh hammer vô tận.

```python
target_machines = [
    (m, s) for m, s in machines
    if s in connected and m not in cleared_today
    and machine_retries.get(str(m), 0) < 2
]
# Tăng counter trước khi chạy
for m, _ in target_machines:
    machine_retries[str(m)] = machine_retries.get(str(m), 0) + 1
state_data["machine_retries"] = machine_retries
save_state(state_data)
```

---

## State file pattern chuẩn

```python
def load_state(today_str: str) -> dict:
    """Reset về ngày mới, carry-forward các fields."""
    EMPTY = {"last_date": today_str, "cleared_machines": [], "machine_retries": {}, "reported_date": None}
    if not STATE_FILE.is_file():
        return EMPTY
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        if data.get("last_date") != today_str:
            return EMPTY
        data.setdefault("machine_retries", {})
        return data
    except Exception as exc:
        sys.stderr.write(f"[WARN] Failed to read state: {exc}\n")
        return EMPTY


def save_state(state: dict) -> None:
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        state["last_run_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as exc:
        sys.stderr.write(f"[WARN] Failed to save state: {exc}\n")
```

---

## Khi debug cron spam

1. **PAUSE cronjob ngay**: `cronjob(action='pause', job_id=...)` để dừng spam tiếp theo
2. **Grep stdout logic**: Tìm mọi `print(...)` không có guard `if s_count > 0`
3. **ADB stall**: `adb -s <serial> reconnect` với máy bị timeout; `inspect_machine.py <N>` verify
4. **Ghi `reported_date` thủ công** vào state file để chặn báo cáo ngay khi script chưa được patch:
   ```json
   { "last_date": "2026-09-22", "reported_date": "2026-09-22", ... }
   ```
5. **Resume cronjob** sau khi patch xong: `cronjob(action='resume', job_id=...)`

---

## Checklist trước khi deploy watchdog mới (no_agent: true)

- [ ] Tất cả `print()` có guard điều kiện rõ ràng
- [ ] `s_count == 0` → `return 0` (stdout rỗng)
- [ ] State file có `reported_date` dedup
- [ ] Max retry cap (ví dụ `machine_retries[m] < 2`)
- [ ] Test `python -m py_compile <script.py>` trước khi deploy
- [ ] Đồng bộ script sang OneDrive Shared và deploy repo
