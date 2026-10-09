# Tra Cứu Log .ai-runs & Chẩn Đoán Lỗi Lease Release / Handoff

## 1. Tra Cứu Log Máy Cụ Thể Trong `.ai-runs` Không Đệ Quy

### Pitfall Nghiêm Trọng
- Thư mục `D:/Taadaa/tiktok-luot nuoi acc/.ai-runs` chứa hàng trăm phiên chạy với hàng chục nghìn file ảnh màn hình (`.png`) và hierarchy (`.xml`).
- **CẤM TUYỆT ĐỐI**: Dùng `grep -rn`, `find .`, `glob.glob('**/*', recursive=True)` trên `.ai-runs`. Các lệnh này sẽ duyệt toàn bộ cây đĩa và bị **TIMEOUT 900s**.

### Cách Tra Cứu Chuẩn Xác & Tức Thì (< 1 giây)
1. **Tìm các run gần nhất của máy `<N>`:**
   ```bash
   ls -td "D:/Taadaa/tiktok-luot nuoi acc/.ai-runs"/*/machines/machine_<N> 2>/dev/null | head -n 5
   ```
2. **Đọc trực tiếp summary và log của máy con:**
   - Summary: `D:/Taadaa/tiktok-luot nuoi acc/.ai-runs/<RUN_ID>/machines/machine_<N>/<RUN_ID>/summary.txt`
   - JSONL Log: `D:/Taadaa/tiktok-luot nuoi acc/.ai-runs/<RUN_ID>/machines/machine_<N>/<RUN_ID>/log.jsonl`
   - Run Manifest: `D:/Taadaa/tiktok-luot nuoi acc/.ai-runs/<RUN_ID>/machines/machine_<N>/<RUN_ID>/run_manifest.json`

---

## 2. Cơ Chế Lỗi `lease release or handoff failed` (`lease-finish-failed`)

### Vị Trí Trong Codebase
- File: `D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/multi_machine_feed_session.py`
- Khu vực: Các dòng xung quanh `4930` – `5070` trong `_run_child()`.

### Dấu Hiệu Nhận Biết
- `final_status`: `"failed"`
- `blocker_type`: `"lease-finish-failed"`
- `stop_reason`: `"lease release or handoff failed"`

### Nguyên Nhân Gốc & Cơ Chế Kích Hoạt
1. Phiên lướt của máy con thực tế đã chạy xong (`initial_goal_completed = goal_completed = True`).
2. Trong giai đoạn teardown giải phóng lease (`lock_holder.get("lease")`):
   - Runner kiểm tra đồng bộ xuất bản dưới `publication_lock` và `state_lock`.
   - Hàm nội bộ `_release_under_lock()` được gọi:
     - Kiểm tra `_watchdog_deadline_expired(timing)`.
     - Gọi `_claim_success_release(timing)` để kiểm tra quyền xuất bản của worker so với watchdog.
   - **Lỗi xảy ra khi:**
     - Deadline bị quá hạn trước khi giải phóng lease kịp hoàn tất.
     - Watchdog đã chiếm quyền xuất bản (`publication_owner != "worker"` hoặc `terminalized=True`).
     - Ngoại lệ trong khi ghi `_write_recovery_handoff_evidence(...)` hoặc `lease.finish(succeeded=True)`.
3. Khi gặp các trường hợp trên:
   - Runner đổi cờ `goal_completed = False` và `lease_release_failed = True`.
   - Khối lệnh bảo vệ `if lease_release_failed or (initial_goal_completed and not goal_completed):` sẽ ghi đè kết quả thành công ban đầu bằng `_child_flow_result(ExitStatus.FAIL, "lease release or handoff failed")`.
