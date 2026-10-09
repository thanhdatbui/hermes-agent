# Watchdog Module 1/2 Counts Passthrough (contract 2026-09-13)

Session: WATCHDOG MODULE 2/1 REPORT — contract mới hẹp, khác prompt timeout cũ.
Quy tắc: chỉ 2 edit, ≤3 iterations không xong thì ABORT, cấm đốt budget, không commit.

## Anchors (feed_session_watchdog.py, ~941 lines)
- A1 ~L473-479 (`parse_run_all`, follow_result.json block): anchor `"failed": raw_failed,` trong `f_item`.
- A2 ~L863 (report loop): anchor `msg_lines.extend(format_released_follows(fl_released, all_follows))`.

## Edit 1 — f_item passthrough (backward-compatible)
```python
f_item = {
    "status": raw_status,
    "followed": flist,
    "follow_failed": is_clean_ff,
    "failed": raw_failed,
    # Module1/2 passthrough (backward-compat: thiếu details -> 0)
    "mode1_count": int((d.get("details") or {}).get("mode1_followed_count") or 0),
    "mode2_count": int((d.get("details") or {}).get("mode2_followed_count") or 0),
    "reason": str(d.get("reason") or ""),
}
```

## Edit 2 — dòng tổng Module trong báo cáo Follow chéo (ngay sau A2)
```python
msg_lines.extend(format_released_follows(fl_released, all_follows))
tot_m2 = sum(int((v or {}).get("mode2_count", 0) or 0) for v in all_follows.values())
tot_m1 = sum(int((v or {}).get("mode1_count", 0) or 0) for v in all_follows.values())
msg_lines.append(f"  + Module 2 (following-list nội bộ): {tot_m2} lượt | Module 1 (search bù): {tot_m1} lượt")
```

## Vì sao an toàn
- `merge_follow_result(prev, new)`: mọi nhánh đều `res = dict(new|prev)` + `res["followed"] = combined_flist`
  → passthrough 2 key mới tự giữ nguyên, không cần sửa merge.
- `format_released_follows / format_success_follows` chỉ đọc list `followed`, không chạm mode counts.
- Data cũ thiếu `details` → totals `0|0` = PASS (chứng minh line render, không phải bug).

## Focused check <30s
```bash
python -c "
import sys; sys.path.insert(0,'C:/Users/Kibe/AppData/Local/hermes/scripts')
import feed_session_watchdog as fsw
_, all_follows, _ = fsw.parse_run_all('D:/Taadaa/runtime/kibe/live/2026-09-13/row-3-120032')
tot_m2=sum(int((v or {}).get('mode2_count',0) or 0) for v in all_follows.values())
tot_m1=sum(int((v or {}).get('mode1_count',0) or 0) for v in all_follows.values())
print(f'  + Module 2 (following-list nội bộ): {tot_m2} lượt | Module 1 (search bù): {tot_m1} lượt')
"
```
Baseline đã verify pre-patch: `parse_run_all` OK (`res_m=80, res_f=74, res_u=74`), kỳ vọng post-patch in `0|0` trên data cũ.

## Pitfalls học được
1. `search_files` với absolute Windows path có thể lỗi `rg: IO error ... cannot find the path` do MSYS `/c/...` mapping — fallback sang `read_file` theo offset đã biết hoặc `terminal` + `python inspect.getsource`.
2. Glob `machines/*/*follow_result*` trả `[]` dù `parse_run_all` vẫn parse được 74 follows → layout dir nested sâu hơn (`run-HHMMSS/machine_X/`); đừng kết luận "không có file", hãy tin `parse_run_all` counts.
3. Nếu merge 2 lần chạy cùng máy cần cộng dồn counts thì phải thêm `max()/+` vào `merge_follow_result` — nhưng contract hẹp hiện tại chỉ yêu cầu passthrough nên giữ đơn giản.
