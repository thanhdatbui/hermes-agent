# Contract Trừ Lượt Follow Tự Nhiên Khi Nick Bị Nhả/Drop (Feed Session Watchdog)

## Bối cảnh & Mục đích
Khi chạy feed session trên farm TikTok (`tiktok-luot nuoi acc`), một số máy gặp tình trạng nick bị nhả follow (follow drop / `FOLLOW_FAILED` / `follow_failed = True`).
Các lượt follow tự nhiên (`natural_follows`) mà máy đó đã thực hiện trong phiên lướt feed thực chất không có giá trị giữ chân hoặc bị hệ thống TikTok thu hồi. Vì vậy, `scripts/feed_session_watchdog.py` cần tự động khấu trừ các lượt follow tự nhiên này trước khi tổng kết và gửi báo cáo Telegram cũng như lưu database tracker.

## Hàm chuẩn: `calculate_session_natural_follows`
Hàm được đặt trước `classify_machine_follow_result` trong `scripts/feed_session_watchdog.py`:

```python
def calculate_session_natural_follows(
    all_machines: dict[str, Any],
    all_follows: dict[str, Any],
    fl_released: list[Any] | None = None,
) -> tuple[int, int, int, int, int]:
    """Tính toán số lượt follow tự nhiên hợp lệ sau khi trừ các nick bị nhả/drop.
    
    Trả về: (valid_tot, valid_fy, valid_fl, valid_fr, dropped_tot)
    """
    fl_released = fl_released or []
    released_machine_set = {str(m) for m in fl_released}
    for m_k, f_data in all_follows.items():
        if isinstance(f_data, dict) and (
            f_data.get("follow_failed") is True
            or str(f_data.get("status") or "").upper() == "FOLLOW_FAILED"
        ):
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

## Vị trí tích hợp trong `main()`
1. **Loại bỏ tính toán sớm**: Không tính `tot_nat_follows` trước vòng lặp duyệt follow, vì lúc đó chưa xác định danh sách máy `fl_released`.
2. **Tính sau khi phân loại follow**:
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
3. **Lưu database**: Truyền `natural_fl=valid_tot_nat` vào `save_session_action_stats(...)`.

## Unit Test Contract
Trong `python_runner/tests/test_feed_session_watchdog.py`:
- Test case: `test_calculate_session_natural_follows_deducts_released_machines`.
- Chạy kiểm tra: `python -m unittest python_runner/tests/test_feed_session_watchdog.py`.
