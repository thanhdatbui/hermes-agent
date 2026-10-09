# Watchdog Natural Follow Released/Dropped Deduction Contract

## 1. Bối Cảnh & Mục Đích (Feed Session Watchdog)
Khi các nick trong phiên gặp sự cố nhả/drop follow (`FOLLOW_FAILED` / `follow_failed = True` / nằm trong `fl_released`), cần phân định theo chỉ đạo Người Dùng (2026-10-03):
- **Nếu lượt đầu follow chéo = 0 (`cnt == 0`)**: Nick bị nhả/drop ngay từ đầu phiên -> Bỏ hết cả follow tự nhiên (`calculate_session_natural_follows` tự trừ khỏi tổng phiên) và chéo (`reported = 0`).
- **Nếu lượt đầu follow chéo thành công (`cnt > 0`)**: Nick đã ăn follow tự nhiên và ăn các lượt chéo trước khi bị nhả -> Giữ nguyên 100% follow tự nhiên (KHÔNG trừ), đồng thời đếm các lượt chéo thành công cho tới khi bị nhả (`reported = cnt + natural_cnt`).

## 2. Hàm Chuẩn: `calculate_session_natural_follows`
Đặt ngay trước `classify_machine_follow_result` trong `scripts/feed_session_watchdog.py`:

```python
def calculate_session_natural_follows(
    all_machines: dict[str, Any],
    all_follows: dict[str, Any],
    fl_released: list[Any] | None = None,
) -> tuple[int, int, int, int, int]:
    """Tính toán số lượt follow tự nhiên hợp lệ sau khi trừ các nick bị nhả/drop ngay từ lượt đầu (cnt == 0).
    
    Trả về: (valid_tot, valid_fy, valid_fl, valid_fr, dropped_tot)
    """
    fl_released = fl_released or []
    # Chỉ bỏ follow tự nhiên của các máy mà lượt đầu follow chéo = 0 (cnt == 0).
    # Nếu lượt đầu follow chéo đã thành công (cnt > 0) thì tính hết follow tự nhiên.
    released_machine_set = set()
    for m in fl_released:
        f_data = all_follows.get(m) or all_follows.get(str(m)) or (all_follows.get(int(m)) if str(m).isdigit() else {})
        cnt = len(f_data.get("followed", [])) if isinstance(f_data, dict) else 0
        if cnt == 0:
            released_machine_set.add(str(m))

    for m_k, f_data in all_follows.items():
        if isinstance(f_data, dict) and (
            f_data.get("follow_failed") is True
            or str(f_data.get("status") or "").upper() == "FOLLOW_FAILED"
        ):
            cnt = len(f_data.get("followed", []))
            if cnt == 0:
                released_machine_set.add(str(m_k))

    tot_fy = 0
    tot_fl = 0
    tot_fr = 0
    dropped_fy = 0
    dropped_fl = 0
    dropped_fr = 0

    for m, d in all_machines.items():
        if not isinstance(d, dict) or d.get("status") != "success":
            continue
        nf = d.get("natural_follows") or {}
        fy = int(nf.get("for-you", 0) or 0)
        fl = int(nf.get("following", 0) or 0)
        fr = int(nf.get("friends", 0) or 0)
        tot_fy += fy
        tot_fl += fl
        tot_fr += fr
        if str(m) in released_machine_set:
            dropped_fy += fy
            dropped_fl += fl
            dropped_fr += fr

    dropped_tot = dropped_fy + dropped_fl + dropped_fr
    valid_fy = max(0, tot_fy - dropped_fy)
    valid_fl = max(0, tot_fl - dropped_fl)
    valid_fr = max(0, tot_fr - dropped_fr)
    valid_tot = max(0, (tot_fy + tot_fl + tot_fr) - dropped_tot)

    return valid_tot, valid_fy, valid_fl, valid_fr, dropped_tot
```

## 3. Quy Chuẩn Tích Hợp Trong `main()`
1. **Loại bỏ tính sớm**: Không cộng dồn `tot_nat_follows` trước vòng lặp duyệt follow vì lúc đó chưa xác định được danh sách `fl_released`.
2. **Khấu trừ sau phân loại follow**:
   ```python
   valid_tot_nat, valid_fy_nat, valid_fl_nat, valid_fr_nat, dropped_tot_nat = calculate_session_natural_follows(
       all_machines, all_follows, fl_released
   )
   valid_nat_rate = (valid_tot_nat / tot_swipes * 100.0) if tot_swipes > 0 else 0.0
   if dropped_tot_nat > 0:
       nat_follow_line = f"  + Follow tự nhiên: {valid_tot_nat} lượt / {tot_swipes} video ({valid_nat_rate:.1f}%) [Đề xuất: {valid_fy_nat} | Bạn bè: {valid_fr_nat}] (Đã tự trừ {dropped_tot_nat} lượt do nick bị nhả/drop)"
   else:
       nat_follow_line = f"  + Follow tự nhiên: {valid_tot_nat} lượt / {tot_swipes} video ({valid_nat_rate:.1f}%) [Đề xuất: {valid_fy_nat} | Bạn bè: {valid_fr_nat}]"
   ```
3. **Database Tracker**: Lưu `natural_fl=valid_tot_nat` vào `save_session_action_stats(...)` để thống kê đúng với thực tế tài khoản.

## 4. Focused Unit Test Contract
Trong `python_runner/tests/test_feed_session_watchdog.py`:
- Test case `test_calculate_session_natural_follows_deducts_released_machines`:
  - M1 (thành công) giữ nguyên 3 natural follows.
  - M2 (`follow_failed = True` trong `all_follows`) bị trừ 2.
  - M3 (nằm trong `fl_released`) bị trừ 1.
  - M4 (`status != success`) bị bỏ qua khỏi mẫu số.
  - Assertions: `valid_tot == 3`, `dropped_tot == 3`.
- Verify: `python -m unittest python_runner/tests/test_feed_session_watchdog.py`.
