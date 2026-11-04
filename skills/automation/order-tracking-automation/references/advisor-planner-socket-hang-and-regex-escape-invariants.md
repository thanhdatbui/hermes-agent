# Advisor Planner Socket Hangs and Regex Escape Fallback Invariants

## 1. Hiện tượng & Triệu chứng S1 Gate B Failure
Trong quá trình vận hành S1 Gate B của `unified_patch_pipeline.py` hoặc triệu tập Hội đồng Cố vấn (`gate_b_planner.py`), có thể xảy ra tình trạng cả 3 cố vấn cùng bị loại:
1. **Sol Worker (`gpt-web-sol` qua OmniRoute :20129) bị treo / Timeout 300s:**
   - Tiến trình Node.js của OmniRoute (`server.js` hoặc `run-next.mjs`) bị ngậm socket lâu ngày hoặc nghẽn connection pool.
   - Khi request gửi vào `/v1/chat/completions` với payload văn bản lớn, kết nối bị treo vô hạn cho đến khi chạm mốc timeout cứng 300s.
2. **Gemini Web (`gemini-web-argon-pool`) bị FAIL count=0 do nuốt dấu escape:**
   - Khi model trả về đoạn code JavaScript/Python có chứa biểu thức chính quy (Regex) như `split(/[\\/]/).pop()`.
   - Chuỗi JSON trả về bị unescape/lột bớt 1 dấu gạch chéo thành `split(/[\/]/).pop()`.
   - Hàm `validate_plan()` dùng phép đối soát byte chính xác (`file_text.count(old_str) == 1`) dẫn đến kết quả `count=0` và đánh trượt plan oan uổng dù logic đúng 100%.
3. **Claude CLI bị chặn Quota Gate (`BLOCK_PROBE_FAILED`):**
   - Bộ kiểm tra quota `claude_quota_guard.py` tự động kích hoạt chế độ bảo vệ khi chạm ngưỡng an toàn hoặc probe thất bại.

---

## 2. Giải pháp Kỹ thuật & Sửa chữa Tận gốc

### A. Cơ chế Fuzzy Regex Escape Fallback trong `validate_plan`
Trong `gate_b_planner.py`, bổ sung kiểm tra fallback khi `count == 0`:
```python
file_text = nl(p.read_text(encoding="utf-8", errors="replace"))
count = file_text.count(old_str)
if count == 0:
    candidates = []
    if "[/]" in old_str:
        candidates.append(old_str.replace("[/]", r"[\/]"))
    if r"[\/]" in old_str:
        candidates.append(old_str.replace(r"[\/]", "[/]"))
    if r"\/" in old_str:
        candidates.append(old_str.replace(r"\/", "/"))
    if "/" in old_str:
        candidates.append(old_str.replace("/", r"\/"))
    for cand in candidates:
        if file_text.count(cand) == 1:
            old_str = cand
            count = 1
            break
if count != 1:
    raise ValueError(f"old_string not unique in {rel_file}: count={count}")
```

### B. Giải phóng Socket Hangs trên OmniRoute (:20129)
Khi phát hiện Sol Worker bị hang quá 300s dù `/api/health` vẫn trả về 200:
1. Kiểm tra các PID Node.js đang chạy:
   ```python
   import psutil
   procs = [p.info for p in psutil.process_iter(['pid', 'name', 'cmdline']) if 'node.exe' in (p.info['name'] or '').lower()]
   ```
2. Kill trực tiếp các tiến trình `server.js` hoặc `run-next.mjs` bị nghẽn socket:
   ```cmd
   taskkill /F /PID <pid_server> /PID <pid_next>
   ```
3. Watchdog nền `omniroute_watchdog.ps1` sẽ tự động khởi tạo lại instance mới sạch sẽ trong 15-20s.
4. Đảm bảo cấu hình gọi Sol Worker trong `gate_b_planner.py` trỏ đúng model `"gpt-web-sol"`.
