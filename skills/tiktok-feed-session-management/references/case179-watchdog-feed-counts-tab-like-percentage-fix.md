# Case 179: Fix Missing feed_counts Parse & Tab Like Percentage Fallback to 0.0%

## 1. Hiện tượng & Vấn đề (The Problem)
Trong báo cáo watchdog nuôi acc TikTok (`feed_session_watchdog.py`), thống kê thả tim hiển thị:
```text
+ Thả tim: 146 tim / 1217 video (12.0%) [Đề xuất: 128 (0.0%) | Bạn bè: 14 (0.0%) | Following: 4 (0.0%)]
```
Người vận hành phát hiện sự vô lý:
- Tab Bạn bè thả được **14 tim**, Đề xuất thả **128 tim**, Following thả **4 tim**.
- Nhưng tỷ lệ phần trăm hiển thị trong ngoặc của cả 3 tab đều bị gán cứng thành **`0.0%`**.

## 2. Nguyên nhân cốt lõi (Root Cause)
1. **Thiếu parse trường `feed_counts`:**
   - Trong `feed_session_watchdog.py`, khối đọc `summary.txt` của từng máy chỉ parse `total_swipes_completed`, `like_counts` và `comment_peeks`.
   - Dict `feed_counts` (số video lướt theo từng tab: `for-you`, `friends`, `following`) hoàn toàn bị bỏ sót, không được đọc vào `m_payload`.
2. **Thiếu merge trường `feed_counts` trong `merge_machine_result`:**
   - Hàm `merge_machine_result` chỉ merge `likes` và `swipes`, không gộp `feed_counts` tích lũy qua các lượt chạy của cùng một ca/phiên.
3. **Mẫu số bằng 0 fallback về chuỗi `0.0%`:**
   - `tot_fy_swipes`, `tot_fr_swipes`, `tot_fl_swipes` luôn bằng `0`.
   - Phép tính `(tot_fr_likes / tot_fr_swipes * 100.0) if tot_fr_swipes > 0 else "0.0%"` kích hoạt nhánh fallback và xuất ra `(0.0%)`.

## 3. Patch Contract & Giải pháp chuẩn
### Anchor 1: Merge `feed_counts` trong `merge_machine_result`
```python
    p_fc = prev.get("feed_counts") or {}
    n_fc = new.get("feed_counts") or {}
    all_fc_keys = set(p_fc.keys()) | set(n_fc.keys())
    if all_fc_keys:
        merged_fc = {}
        for k in all_fc_keys:
            merged_fc[k] = max(p_fc.get(k, 0), n_fc.get(k, 0))
        res["feed_counts"] = merged_fc
```

### Anchor 2: Trích xuất `feed_counts` từ `summary.txt`
```python
    idx_fc = c.find('"feed_counts":')
    if idx_fc != -1:
        chunk_fc = c[idx_fc:idx_fc + 150]
        for ft in ("for-you", "following", "friends"):
            m_ft = re.search(rf'["\']?{ft}["\']?:\s*(\d+)', chunk_fc)
            if m_ft:
                feed_counts_map[ft] = int(m_ft.group(1))
```
Và truyền `feed_counts_map` vào `m_payload = {..., "feed_counts": feed_counts_map, ...}`.

## 4. Pitfall & Đồng bộ nhiều vị trí
- Script watchdog tồn tại ở cả 2 nơi: `C:/Users/Kibe/AppData/Local/hermes/scripts/feed_session_watchdog.py` và `D:/Taadaa/tiktok-luot nuoi acc/scripts/feed_session_watchdog.py`. Phải patch đồng thời cả 2 bản để tránh drift.
- Chạy unit test `pytest C:/Users/Kibe/AppData/Local/hermes/scripts/test_feed_session_watchdog.py` để verify logic merge và parse.
