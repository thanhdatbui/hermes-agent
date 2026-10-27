# Báo Cáo & Quy Trình Đại Phẫu Cắt Tỉa Hệ Thống Gate / Guard Over-Engineered (2026-10-27)

## 1. Bối Cảnh & Vấn Đề Gốc
Trong quá trình vận hành Taadaa Phone Farm (hơn 80 máy Android nuôi nick TikTok), hệ thống chốt chặn đã tích lũy hơn 90 file kiểm soát. Hậu quả:
- **Tê liệt phiên vận hành:** Một tác vụ đơn giản trên điện thoại (đổi bio, pin clip) không sửa bất kỳ dòng code nào nhưng khi chốt phiên ("Done"), hệ thống lại tự động đọc các commit Git cũ của repo tools, chấm REJECTED rồi kích hoạt Sol Repair điên cuồng đi sửa code ma.
- **Security Theater & Blockchain giả cầy:** Tự cài đặt thuật toán kiểm tra DACL process memory Windows (`win32security`), HMAC tự ký tự duyệt, và băm chuỗi SHA-256 (`prev_chain_hash` + `self_hash`) vào từng dòng log `gate_audit.jsonl`. Khi có một bản ghi thiếu `self_hash`, hàm `_read_last_chain_hash` quăng `RuntimeError` làm tê liệt toàn bộ cổng Closeout.
- **Trói chân lệnh Git Push:** `safe_push.py` bọc ngoài git push và quét ngược log `gate_audit.jsonl` đòi phải có bản ghi APPROVED trong 30 phút, tạo vòng lặp phụ thuộc chết người.

## 2. Các Hành Động Đại Phẫu Đã Thực Hiện

### A. Đưa 5 Siêu Gate Dead-Code / Over-Engineered vào `_retired/`
Đã sao lưu an toàn và chuyển vào `D:/Taadaa/tools/_retired/`:
1. `plan_exec_gate.py` (1.787 dòng, 66 KB): DACL memory Windows và Git ref ảo `refs/gates/<id>/a`.
2. `evidence_gate_verifier.py` (741 dòng, 32 KB): Tự parse từng byte nhị phân ảnh (`\x89PNG`, `\xff\xd8`) và kiểm tra PID ctypes. Code mồ côi (0 callers).
3. `gate_pipeline.py` (518 dòng, 13 KB): Pipeline Gate A -> B -> C tự động hóa phức tạp.
4. `review_gate.py` & `run_plan_review_gate.py`: Tàn dư gọi 9Router review diff bằng curl HTTP.

### B. Triệt Tiêu Lỗi Crash Chuỗi Hash Trong `closeout_gate.py`
- **Nguyên nhân crash:** `_read_last_chain_hash` đọc dòng cuối của `gate_audit.jsonl`, nếu không có `self_hash` lập tức raise `ValueError` -> `RuntimeError`.
- **Vá cơ học O(1):** Quét ngược log tìm dòng hợp lệ gần nhất; nếu không có hoặc có lỗi thì fallback mềm về `"GENESIS"` an toàn tuyệt đối, không bao giờ làm sập gate.

### C. Dọn Dẹp Chốt Chặn Giấy Tờ Trong `safe_push.py`
- Cắt bỏ hoàn toàn 3 hàm kiểm tra ngược log JSONL cũ: `_verify_closeout_gate_approval`, `_verify_guardgate_invariants`, `_verify_canary_receipt`.
- Trả lệnh push về trạng thái kỹ thuật trực tiếp: git push với các cờ an toàn, loại bỏ cơ chế đòi giấy phép thông hành JSONL.

### D. Mở Khóa Tra Cứu Quota Trong `guard_claude_cli_lock.py`
- Thêm `--check-quota` vào `SAFE_FLAGS` để các lệnh kiểm tra hạn mức `claude_worker.py --check-quota` chạy ngay lập tức mà không bị cướp quyền hay chặn nhầm.

## 3. Ranh Giới Bất Biến Giữa "Gate Cản Trở" vs "Watchdog Bảo Vệ Farm"
- **Gate Cản Trở (Phải Cắt / Tinh Gọn):**
  - AI Reviewer chấm điểm văn học 85/100.
  - Vòng lặp Sol Repair tự sửa code khi không có failing test cụ thể.
  - DACL memory, HMAC tự ký trên cùng quyền OS User.
  - Blockchain hash chain trong file log JSONL.
- **Watchdog Quan Sát & Bảo Vệ Thiết Bị Thật (BẮT BUỘC GIỮ 100%):**
  - `gate_compliance_watchdog.py`: Báo cáo định kỳ 6h đo lường vi phạm (gọi worker sai, quét root, timeout) để Operator nắm kỷ luật Agent.
  - `with_device_lock.py`: JIT lock từng máy theo serial ADB, chống xung đột điều khiển 80 máy.
  - `guard_android_proxy.py` & `farm_network_gate.py`: Chống rớt proxy lộ IP farm làm chết nick TikTok.
  - `ui_policy_check.py`: Cấm spam `uiautomator dump` làm treo ADB trên Samsung Galaxy S7.
  - `guard_cronjob_safety.py`: Ép cronjob chạy ẩn (`CREATE_NO_WINDOW`), chống nhảy cửa sổ đen sì màn hình.
  - `claude_quota_guard.py` & `guard_scan`: Chống cháy hạn mức token (<85%) và cấm quét đĩa diện rộng trên ổ D:/.
