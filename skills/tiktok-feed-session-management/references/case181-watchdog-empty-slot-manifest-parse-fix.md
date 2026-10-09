# Case 181: Khắc Phục Lỗi Watchdog Bỏ Sót Máy Trống Slot Do Bỏ Qua run_manifest.json

## 1. Hiện Tượng & Báo Cáo Sai Lệch
- Người vận hành phát hiện 2 alert thông báo đối nghịch nhau:
  - Báo cáo Feed Watchdog:
    ```text
    📊 [TIKTOK NUÔI ACC] Ca 4 - Phiên 2/2 (Đêm) hoàn tất (Row 8)
    • Tổng máy xử lý: 58 máy
    • Lướt Feed:
      + Success (55): 1, 7, 8...
      + Fail (3): M38, M75, M77
      + Trống slot/chưa có nick (0): Không có
    ```
  - Alert Preflight Reg bù ngay bên dưới lại báo:
    `📋 [PREFLIGHT REG BÙ ROW 8] Tổng máy thiếu: 22 (Đang cần reg bù cho 22 máy)`
- Người vận hành phản ánh: *"Báo cáo láo. Ghi trống slot k có trong khi alert dưới lại báo trống slot phải reg bù"*.

---

## 2. Nguyên Nhân Cốt Lõi (Root Cause)
1. **Cơ chế Runner Safe-Skip trước khi đụng vào thiết bị:**
   - Khi chạy nuôi feed một Row (ví dụ Row 8), nếu một máy chưa có username trong file safe workbook (`account row 8 is empty (no username), skipping`), runner kích hoạt safe-skip ngay tại preflight.
   - Do bỏ qua sớm, runner **KHÔNG tạo thư mục con `machines/machine_X/`** và không sinh `summary.txt` per-machine.
   - Thay vào đó, toàn bộ danh sách 80 máy (kèm các máy bị safe-skip) chỉ được ghi nhận trong mảng `multi_machine_summary` của file root `run_manifest.json` và file root `summary.txt`.
2. **Watchdog bị mù file `run_manifest.json`:**
   - Trong `feed_session_watchdog.py`, hàm `parse_run_all(run_dir)` sử dụng `os.walk` chỉ tìm kiếm `summary.txt` nằm dưới các thư mục con `machines/machine_X/`.
   - Hàm bỏ qua hoàn toàn `run_manifest.json` ở root. Kết quả: `all_machines` chỉ gom được đúng 58 máy có session log thực tế (55 pass + 3 fail), 22 máy bị bỏ qua hoàn toàn biến mất khỏi báo cáo.
3. **Mẫu số giả định bị co cụm:**
   - Hàm `get_expected_machines_for_row(row)` lấy danh sách từ `hermes_cron_source_config.json` vốn chỉ chứa các máy *đang có nick* ở Row đó (58 máy).
   - Watchdog coi 58 máy là 100% kế hoạch của phiên, đối soát `58 - 58 = 0` máy trống slot, dẫn đến bản tin báo cáo sai lệch nghiêm trọng thực tế vận hành farm.

---

## 3. Giải Pháp Kỹ Thuật Chuẩn (Patch Contract)

### A. Đọc trực tiếp `run_manifest.json` trong `parse_run_all`:
Bổ sung kiểm tra file `run_manifest.json` ở root `run_dir` trong vòng lặp duyệt:
```python
# Parse run_manifest.json at run root to capture all machines (including skipped-empty)
if "run_manifest.json" in files and not m_str:
    m_path = os.path.join(root, "run_manifest.json")
    try:
        with open(m_path, "r", encoding="utf-8", errors="ignore") as f:
            m_data = json.load(f)
        mms = m_data.get("multi_machine_summary") if isinstance(m_data, dict) else None
        if isinstance(mms, list):
            for item in mms:
                if not isinstance(item, dict) or "machine" not in item:
                    continue
                m_num = str(item["machine"])
                exp_u = str(item.get("expected_username", "")).strip()
                s_reason = str(item.get("stop_reason", "")).strip()
                f_status = str(item.get("final_status", "")).strip().lower()
                if exp_u == "account:empty" or "is empty (no username)" in s_reason.lower() or "does not have valid row" in s_reason.lower():
                    m_st = "skipped-empty"
                elif f_status == "success":
                    m_st = "success"
                else:
                    m_st = "fail"
                payload = {
                    "status": m_st,
                    "reason": s_reason,
                    "likes": {},
                    "feed_counts": {},
                    "swipes": int(item.get("swipes_completed", 0) or 0),
                    "comment_peeks": 0,
                }
                res_m[m_num] = merge_machine_result(res_m.get(m_num), payload)
    except Exception:
        pass
```

### B. Hàm `get_all_fleet_machines()` & Đối soát toàn bộ 80 máy:
Thêm hàm lấy danh mục toàn bộ fleet 80 máy và bổ sung các máy chưa có trong `all_machines`:
```python
def get_all_fleet_machines() -> set:
    """Lấy toàn bộ danh sách 80 máy của Farm."""
    if os.path.exists(SOURCE_CONFIG):
        try:
            with open(SOURCE_CONFIG, "r", encoding="utf-8") as f:
                data = json.load(f)
            accounts = data.get("feed_source", {}).get("accounts", [])
            m_set = {str(a["machine"]) for a in accounts if "machine" in a}
            if m_set:
                max_m = max(int(x) for x in m_set if x.isdigit())
                target_cnt = max(max_m, 80)
                return set(str(i) for i in range(1, target_cnt + 1))
        except Exception:
            pass
    return set(str(i) for i in range(1, 81))
```

Trong vòng lặp tạo báo cáo phiên:
```python
# Phân loại Feed đối soát trên toàn bộ fleet (80 máy)
fleet_machines = get_all_fleet_machines()
for fm in fleet_machines:
    if fm not in all_machines:
        if fm not in expected_machines:
            all_machines[fm] = {"status": "skipped-empty", "reason": f"account row {active_row} is empty (no username)"}
        else:
            all_machines[fm] = {"status": "fail", "reason": "no-run-recorded"}
```

---

## 4. Quy Chuẩn Đồng Bộ 4 Vị Trí (Bắt Buộc Chống Drift)
Mọi thay đổi trong `feed_session_watchdog.py` bắt buộc phải cập nhật đủ cả 4 đường dẫn:
1. `D:/Taadaa/tiktok-luot nuoi acc/scripts/feed_session_watchdog.py`
2. `D:/Taadaa/tiktok-luot nuoi acc/scripts/hermes_cron/feed_session_watchdog.py`
3. `D:/Taadaa/Hermes/deploy/hermes-home/scripts/feed_session_watchdog.py`
4. `C:/Users/Kibe/AppData/Local/hermes/scripts/feed_session_watchdog.py`

## 5. Kết Quả Sau Vá
Báo cáo watchdog phản ánh trung thực toàn bộ 80 máy của Farm:
```text
📊 [TIKTOK NUÔI ACC] Ca 4 - Phiên 2/2 (Đêm) hoàn tất (Row 8)
• Tổng máy xử lý: 80 máy
• Lướt Feed:
  + Success (55): 1, 7, 8, 9...
  + Fail (3): M38, M75, M77
  + Trống slot/chưa có nick (22): 2, 3, 4, 5, 6, 10, 20, 22, 30, 36, 37, 40, 44, 46, 48, 54, 55, 61, 62, 64, 66, 76
```
Đồng nhất 100% với alert của preflight reg bù.
