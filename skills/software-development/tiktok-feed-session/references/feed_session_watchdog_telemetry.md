# Telemetry & Đồng bộ Watchdog Báo Cáo Nuôi Feed (`feed_session_watchdog.py`)

## 1. Đường dẫn chuẩn (2 nơi BẮT BUỘC đồng bộ)
- **Repo source:** `D:\Taadaa\tiktok-luot nuoi acc\scripts\feed_session_watchdog.py`
  *(Lưu ý: folder có khoảng trắng `"tiktok-luot nuoi acc"`, khi chạy terminal/tool cần bọc ngoặc kép hoặc dùng path Windows).*
- **Hermes runtime scripts:** `C:\Users\Kibe\AppData\Local\hermes\scripts\feed_session_watchdog.py`
- **Quy tắc:** Mọi thay đổi tại repo source BẮT BUỘC phải sao chép sang thư mục Hermes scripts và kiểm tra cú pháp bằng `python -m py_compile` tại cả 2 vị trí.

## 2. Quy trình thêm Telemetry / Metric mới vào Watchdog Báo Cáo Ca
Khi bổ sung một metric hành vi nuôi mới (như Follow tự nhiên, Thả tim theo tab, Đọc comment, v.v.):

1. **`merge_machine_result(prev, new)`**:
   - Merge telemetry dictionary tích luỹ qua các lần retry/run kế tiếp:
   ```python
   p_nf = prev.get("natural_follows") or {}
   n_nf = new.get("natural_follows") or {}
   all_nf_keys = set(p_nf.keys()) | set(n_nf.keys())
   if all_nf_keys:
       merged_nf = {}
       for k in all_nf_keys:
           merged_nf[k] = max(p_nf.get(k, 0), n_nf.get(k, 0))
       res["natural_follows"] = merged_nf
   ```

2. **`parse_run_all(run_dir)` (hoặc per-machine summary reader)**:
   - Trích xuất telemetry từ `summary.txt` hoặc dict kết quả của máy qua regex:
   ```python
   # Ví dụ: follow_counts: {"for-you": X, "friends": Y}
   idx_nf = c.find('"follow_counts":')
   if idx_nf != -1:
       chunk_nf = c[idx_nf:idx_nf + 150]
       for ft in ("for-you", "following", "friends"):
           m_ft = re.search(rf'["\']?{ft}["\']?:\s*(\d+)', chunk_nf)
           if m_ft:
               natural_follows_map[ft] = int(m_ft.group(1))
   ```
   - Thêm vào payload per-machine (`m_payload`).

3. **Tính toán tổng hợp ca (`tot_*`)**:
   - Tính tổng các lượt từ máy thành công (`status == "success"`):
   ```python
   tot_fy_nat_follows = sum(d.get("natural_follows", {}).get("for-you", 0) for m, d in all_machines.items() if d.get("status") == "success")
   tot_fr_nat_follows = sum(d.get("natural_follows", {}).get("friends", 0) for m, d in all_machines.items() if d.get("status") == "success")
   tot_nat_follows = tot_fy_nat_follows + tot_fr_nat_follows
   tot_nat_follow_rate = (tot_nat_follows / tot_swipes * 100.0) if tot_swipes > 0 else 0.0
   ```

4. **Format hiển thị (`block_lines`)**:
   - Thêm dòng telemetry trực quan ngay dưới phần thả tim / lướt feed:
   ```python
   f"  + Follow tự nhiên: {tot_nat_follows} lượt / {tot_swipes} video ({tot_nat_follow_rate:.1f}%) [Đề xuất: {tot_fy_nat_follows} | Bạn bè: {tot_fr_nat_follows}]",
   ```
