# CronRun Context Manager Premature Exit & Watchdog Mute Trap

## 1. Bản Chất Kỹ Thuật (Root Cause)
Trong thư viện giám sát định kỳ `cron_alert_core.py`, lớp `CronRun` được thiết kế theo mô hình Context Manager (`__enter__` và `__exit__`):
- `__enter__`: Khởi tạo context, bắt đầu tính giờ `start_t`.
- `__exit__`: Đánh giá `anomalies`. Nếu rỗng và không có `force_report`, đặt `status = "NOMINAL"` và ghi `state.json`. Nếu có lỗi hoặc `force_report`, in `self.report_message` hoặc danh sách mã lỗi ra `stdout`.

### Bẫy 1: Premature Exit Pitfall (with block đóng quá sớm)
Khi viết watchdog kẹp `CronRun`, nếu lập trình viên thụt lề sai khiến khối `with run_ctx as run:` chỉ bọc các dòng precheck ban đầu (ví dụ kiểm tra script tồn tại):
```python
# ❌ LỖI NGHIÊM TRỌNG: with block kết thúc quá sớm
with run_ctx as run:
    if not Path(SCRIPT_PATH).exists():
        run.anomaly("SCRIPT_NOT_FOUND", "...")
        sys.exit(1)

# Toàn bộ logic chạy audit, scan flop, check stale nằm NGOÀI with block!
cmd = [...]
data = run_audit(...)
...
if run:
    run.check("stale_accounts", crit, lambda v: v == 0)
    run.set_report(msg)
elif crit > 0 or force:
    print(msg)
sys.exit(0)
```

### Bẫy 2: Metric Blindspot (Thêm nội dung báo cáo nhưng quên đăng ký `run.check`)
Một bẫy tinh vi khác: khi mở rộng watchdog thêm phần kiểm tra mới (ví dụ `_get_flop_section()` quét kênh flop):
Nếu chỉ nối text vào `lines.extend(flop_lines)` mà KHÔNG gọi:
`run.check("flop_accounts", f_cnt, lambda v: v == 0, severity="P1", msg=f"Có {f_cnt} kênh flop cần xoay nguồn cào!")`
Thì khi các chỉ số cũ đều đạt chuẩn (`tot > 0`, `crit == 0`, `drift == 0`), `CronRun` vẫn tính `status = "NOMINAL"`!
Hậu quả: Do không có `ANOMALY` và không có `--force`, `CronRun.__exit__` sẽ BỎ QUA `self.report_message`, không in gì ra stdout và nuốt chửng toàn bộ danh sách kênh flop!

### Hậu Quả Dây Chuyền (Silent Failure Cascade):
1. Khối `with` kết thúc ngay sau khi kiểm tra precheck (~0.03s), `run.__exit__()` kích hoạt khi `anomalies` đang rỗng ➔ ghi nhận trạng thái `NOMINAL`, không in gì ra `stdout`.
2. Toàn bộ logic sau đó vẫn chạy, `run.check(...)` đẩy lỗi vào `run.anomalies`, `run.set_report(msg)` gán nội dung báo cáo. Nhưng vì `__exit__` đã chạy xong từ trước, không có cơ chế nào gọi in `report_message` nữa.
3. Nhánh fallback `elif crit > 0: print(msg)` bị bỏ qua hoàn toàn vì biến `run` trong Python vẫn tồn tại trong scope hàm và có giá trị chân lý (`bool(run) == True`).
4. Script kết thúc với `sys.exit(0)` và `stdout` hoàn toàn RỖNG (0 bytes).
5. Cơ chế Scheduler của Hermes (`no_agent: True`): Khi `stdout` rỗng, hệ thống kích hoạt **Silent Delivery**, không gửi bất kỳ tin nhắn nào về Telegram. Báo cáo quan trọng (stale upload, flop channels) bị "câm" hoàn toàn mà không hề báo lỗi đỏ.

---

## 2. Quy Chuẩn Khắc Phục Chuẩn Xác (Remediation)
BẮT BUỘC:
1. Toàn bộ phần thân script (từ khởi chạy subprocess, parsing dữ liệu, đánh giá `run.check`, tạo format tin nhắn cho đến `run.set_report`) phải nằm TRỌN VẸN bên trong khối `with run_ctx as run:` (hoặc gọi tường minh `run.__enter__()` ở đầu và `run.__exit__()` ngay sau `run.set_report(msg)`).
2. Mọi phần mở rộng nghiệp vụ phát hiện lỗi/bất thường (như `flop_need_source_swap > 0`) BẮT BUỘC phải đăng ký `run.check(...)` để đảm bảo `CronRun` chuyển trạng thái sang `ANOMALY`.
3. Nhánh fallback khi không dùng `CronRun` hoặc khi phát hiện lỗi phải kiểm tra toàn diện: `elif crit > 0 or drift_issues or f_cnt > 0 or force: print(msg)`.

```python
# ✅ CHUẨN XÁC: Toàn bộ vòng đời tác vụ được quản lý đồng bộ
    force = "--force" in sys.argv
    run = CronRun("cron_stale_upload_watchdog", force_report=force) if CronRun else None
    if run:
        run.__enter__()
    if not Path(SCRIPT_PATH).exists():
        if run:
            run.anomaly("SCRIPT_NOT_FOUND", f"Script không tồn tại: {SCRIPT_PATH}")
            run.__exit__(None, None, None)
        else:
            print(f"❌ Script not found: {SCRIPT_PATH}")
        sys.exit(1)

    # Chạy subprocess audit
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    data = json.loads(proc.stdout)

    # Đánh giá anomalies đầy đủ cả stale lẫn flop
    if run:
        run.check("total_farm_accounts", tot, lambda v: v > 0, severity="P0")
        run.check("critical_stale_accounts", crit, lambda v: v == 0, severity="P1")
        run.check("workbook_drift", len(drift_issues), lambda v: v == 0, severity="P1")
        if f_cnt > 0:
            run.check("flop_accounts", f_cnt, lambda v: v == 0, severity="P1", msg=f"Có {f_cnt} kênh flop cần xoay nguồn!")

    # Format báo cáo
    msg = "\n".join(lines)
    save_current_snapshot(...)

    if run:
        run.set_report(msg)
        run.__exit__(None, None, None)
    elif crit > 0 or drift_issues or f_cnt > 0 or force:
        print(msg)
    sys.exit(0)
```

---

## 3. Tách Biệt Giữa Cơ Chế Quét (Scanner) & Kích Hoạt Xoay Nguồn (Execution)
Khi điều tra nghi vấn "cơ chế phát hiện kênh flop không hoạt động":
1. **Kiểm tra tầng dữ liệu (Data & Classification):**
   Chạy trực tiếp hàm core scanner (ví dụ `flop_channel_scanner.scan_farm_flop_channels`) với live database. Nếu nick đã được gắn nhãn `FLOP_NEED_SOURCE_SWAP` và sinh ra `start_seq = video_da_dang + 1`, cơ chế phân loại logic hoạt động hoàn hảo.
2. **Kiểm tra tầng phân phối cảnh báo (Reporting Delivery):**
   Kiểm tra file `cron_health/<watchdog>.json`. Nếu `duration_s < 0.1` bất thường và `status == "NOMINAL"` trong khi thực tế có lỗi, lập tức truy vết lỗi Indentation / Scope của Context Manager.
3. **Phân định rõ ranh giới tự động hóa:**
   Scanner chỉ chịu trách nhiệm **phát hiện và sinh hợp đồng O(1)** để bảo toàn an toàn kho render. Nếu chưa có pipeline auto-swap được kích hoạt, farm worker vẫn sẽ tiếp tục upload các video còn sót trong folder render cũ. Cần giải thích rõ cho User sự khác nhau giữa "phát hiện flop" và "tự động xóa/thay thế video render".
