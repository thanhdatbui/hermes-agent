# Case 127: Phục Hồi Focused Package Unavailable Qua UI XML & Bài Học Thực Chiến Patch Contract (06/09/2026)

## 1. Bối cảnh & Hiện tượng lỗi
- **Hiện trường:** Farm Alert `[MÁY 46]` (Serial: `ce0916092531413504`, Nick: `trieutruc0505`) dừng phiên nuôi acc / lướt feed TikTok với triệu chứng: `focused package unavailable`.
- **Quan sát thực tế trên thiết bị:** Ứng dụng TikTok vẫn đang mở và hiển thị feed bình thường.

## 2. Nguyên nhân cốt lõi (Root Cause)
1. **Lệnh dumpsys trả về rỗng trong transition:** Khi thiết bị Android chuyển cảnh giữa các video hoặc hệ thống bận, `dumpsys window` tạm thời không bắt được window focus và trả về `focused_package = None`.
2. **Khiếm khuyết dữ liệu trong `safety_check_attempt` (`python_runner/core/safety.py`):**
   - `safety_check_attempt` không truyền `raw_xml` cho `safety_check` (mặc định nhận `None`).
   - `safety_check_attempt` chỉ trích xuất `attempt.get("detected_screen")` mà bỏ qua `attempt.get("detected")`.
   - Hệ quả: Biến `is_tiktok_xml` trong `safety_check` luôn đánh giá `False`.
3. **Fail-closed quá sớm:** Khi `focus_pkg is None` và `is_tiktok_xml == False`, hàm `safety_check` lập tức trả về `SafetyCheckResult(SAFETY_FAILED, "focused package unavailable")` làm crash cả feed session, dù UI XML đã dump thành công và chứa đầy đủ marker / package của TikTok.

## 3. Giải pháp chuẩn hóa (Case Fix)
1. **Trong `safety_check_attempt`:**
   - Fallback đọc `raw_xml` từ `xml_path` (nếu `raw_xml` chưa có trong bộ nhớ `attempt`):
     ```python
     raw_xml = attempt.get("raw_xml") or attempt.get("xml_text")
     if not raw_xml and attempt.get("xml_path"):
         try:
             xml_p = Path(str(attempt["xml_path"]))
             if xml_p.is_file():
                 raw_xml = xml_p.read_text(encoding="utf-8", errors="ignore")
         except Exception:
             raw_xml = None
     ```
   - Fallback `detected = attempt.get("detected_screen") or attempt.get("detected") ...`
   - Truyền `raw_xml=raw_xml` vào `safety_check(...)`.
2. **Trong `safety_check`:**
   - Mở rộng `is_tiktok_xml` bao phủ toàn bộ `KNOWN_TIKTOK_PACKAGES` và các tabs/markers quen thuộc ("Đề xuất", "Bạn bè", "Following", "For You", resource IDs đặc trưng).
   - Kiểm tra bằng chứng XML an toàn:
     ```python
     has_xml_evidence = bool(xml_available or raw_xml)
     if (focus_pkg in SYSTEM_OVERLAY_PACKAGES or focus_pkg is None) and (
         is_known_tiktok_screen or (has_xml_evidence and is_tiktok_xml)
     ):
         focus_pkg = expected
     ```
   - Tự động phục hồi `focus_pkg = expected` khi XML chứng minh TikTok đang ở trên màn hình, triệt tiêu lỗi `focused package unavailable`.
3. **Trong `python_runner/flows/observe.py`:**
   - Bổ sung regex nhận diện các dạng Samsung window focus (`Window{...}`) và bổ sung lightweight grep fallback trên `dumpsys window`.

## 4. Bài học thực chiến: Giá trị sống còn của Patch Contract (Claude Opus Playbook)
- **Thực tế:**
  + Lần 1 & 2: Coordinator dispatch worker với goal điều tra mở ("Phân tích log và sửa...", "Patch cơ chế re-poll..."). Cả 2 worker đều rơi vào bẫy phân tích (analysis paralysis), gọi tới 35 tool calls (chạm trần cứng `max_iterations = 35`, mất 40+ phút mỗi worker) mà KHÔNG chạm vào đĩa để sửa code!
  + Lần 3: Coordinator tuân thủ nghiêm ngặt Claude Opus Playbook:
    1. Dùng `git grep` và python một dòng định vị chính xác vị trí lỗi.
    2. Xác nhận tính duy nhất: `grep -c == 1` cho cả 2 đoạn code `old_string`.
    3. Soạn **Patch Contract** hoàn chỉnh gồm `old_string` -> `new_string` + lệnh test cụ thể (`test_safety.py`).
    4. Dispatch worker với directive: *"Áp 1 patch đã soạn sẵn, KHÔNG điều tra, KHÔNG đọc thăm dò. Budget <= 5 calls"*.
  + **Kết quả:** Worker thứ 3 hoàn thành xuất sắc trong **134 giây** (11 tool calls), `py_compile` và 24/24 unit test pass 100%!
- **Quy tắc đúc rút:** Đối với mọi codebase phức tạp, Coordinator **CẤM TUYỆT ĐỐI** giao goal mở cho worker. BẮT BUỘC soạn sẵn Patch Contract với Uniqueness Check trước khi dispatch!

## 5. Xử lý Stale Fast-Fail Device Lock Trước Khi Chạy Canary
- Khi một máy farm dừng phiên do Fast-Fail, runner giữ lock 1h (`.lock.json`) để operator inspect hiện trường.
- Nếu tiến trình master runner (`run_tiktok.py --mode multi-machine-feed-session`) vẫn đang chạy nền cho các máy khác trong cùng cohort, PID ghi trong file lock vẫn sống, nhưng máy lỗi cụ thể đã dừng.
- Lệnh Canary sẽ bị từ chối nếu không giải phóng lock này.
- **Quy trình:**
  1. Kiểm tra tiến trình con của master PID: xác nhận máy cần test không còn lệnh ADB nào đang chạy.
  2. Xóa các file lock của máy:
     `rm -f C:/Users/Kibe/.codex/device-locks/machine_<N>.lock.json C:/Users/Kibe/.codex/device-locks/serial_<serial>.lock.json`
  3. Kích hoạt lệnh Canary kèm `env -u PYTHONPATH`.
