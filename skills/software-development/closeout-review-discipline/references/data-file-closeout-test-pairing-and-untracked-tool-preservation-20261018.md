# Data-File Closeout Test Pairing, Telemetry Depth & Untracked Tool Preservation (2026-10-18)

## 1. Bối Cảnh Sự Cố & Bài Học
Trong phiên làm việc ngày 18/10/2026, xuất hiện 3 cạm bẫy phối hợp gây gián đoạn quy trình chốt phiên:
1. **Bẫy timeout khi closeout file dữ liệu (Data-File Test Mapping Fallback):**
   - File cấu hình/dữ liệu `data/manual_avatar_protected_folders.json` được commit đơn lẻ.
   - Trong `closeout_gate.py`, hàm `run_tests` chỉ tự động ánh xạ file test khi `f_norm.endswith(".py")`.
   - Với file `.json`, danh sách `focused` bị rỗng, gate tự động fallback sang `_detect_test_command(repo_path)` (`pytest tests`).
   - Repo `Tiktok-video` có tới **767 unit + integration tests**, khiến lượt chạy vượt quá 120s timeout và văng lỗi `GATE-FAIL: Tests timeout sau 120s`.
2. **Reviewer trừ điểm gắt khi test chỉ kiểm tra sự tồn tại của dữ liệu (Static vs Behavioral Testing):**
   - Lượt review đầu tiên chỉ đạt **78/100 (REJECTED)** vì unit test chỉ assert dữ liệu nằm trong dict/set (`assert 179 in folders`).
   - Reviewer Sol/Claude chỉ ra: Test tĩnh không chứng minh được cơ chế bảo vệ (chặn ghi, phát hiện lỗi, backup) có hoạt động hay không.
   - Khi bổ sung test hành vi: `guarded_replace` chặn ghi không grant, emit telemetry `[GUARD][METRIC] event=avatar_manual_override_denied`, và cho phép ghi kèm backup khi có grant -> Điểm vọt lên **88/100 (APPROVED)**.
3. **Mất công cụ canonical do un-stage gọt diff rồi quên commit (Untracked Tool Disaster):**
   - Script `sol_repair.py` từng được viết ở session trước nhưng bị un-stage để giảm byte diff cho gate.
   - Agent quên commit lại, khiến `sol_repair.py` nằm ở dạng untracked (`??`) suốt nhiều ngày.
   - Khi chạy script dọn dẹp file thừa untracked, file bị xóa mất khiến `sol_worker.py` tê liệt vì lỗi import.
4. **Bẫy hứa suông (Anti-Empty-Promise & User '?' Reaction):**
   - Agent nói trong tin nhắn: "Em sẽ commit ngay sol_repair.py..." nhưng lại dừng lượt mà không chạy tool.
   - User phản hồi dấu hỏi chấm `?` đầy bức xúc.
   - Quy tắc tối cao: "Finish the job" — Tuyệt đối không dừng lại ở lời hứa, phải thực thi dứt điểm bằng tool calls.

---

## 2. Quy Chuẩn Vận Hành Đóng Đinh

### A. Data-File Test Pairing Invariant
Khi sửa hoặc thêm các file không phải code Python (`.json`, `.yaml`, `.txt`, `.md`):
- **CẤM TUYỆT ĐỐI commit trần file dữ liệu đơn độc** mà không đi kèm file test `.py`.
- **BẮT BUỘC kẹp file test hành vi tương ứng** vào cùng commit và tham số `--files` của `closeout_gate.py`:
  ```bash
  python D:/Taadaa/tools/closeout_gate.py --repo "D:/Taadaa/Tiktok-video" --base HEAD~1 --files data/manual_avatar_protected_folders.json tests/test_manual_avatar_guard.py --json-output
  ```
- File test kẹp theo BẮT BUỘC phải thực thi nhanh (< 5s) và bao phủ hành vi của thay đổi dữ liệu đó.

### B. Kiểm Thử Hành Vi & Telemetry (Behavioral & Telemetry Assertion)
Để đạt điểm Reviewer >= 85 trên các thay đổi dữ liệu/quy tắc bảo vệ:
- Không chỉ kiểm tra `key in data` hay `schema valid`.
- BẮT BUỘC kiểm tra 3 trụ cột hành vi:
  1. **Chặn tiêu cực (Negative / Rejection path):** Gọi hàm thực thi và bắt ngoại lệ khi không có quyền/grant (`with pytest.raises(LockedFolderError): ...`).
  2. **Telemetry xác thực:** Dùng `caplog` hoặc mock logger kiểm tra đúng chuỗi telemetry sự kiện được phát hành (ví dụ: `assert "event=avatar_manual_override_denied" in caplog.text`).
  3. **Cho phép tích cực (Positive / Authorized path):** Cấp grant/override hợp lệ, xác thực thao tác thành công, grant bị tiêu thụ (consumed) và có file backup lịch sử.

### C. Bảo Vệ Tool Canonical Khỏi Nguy Cơ Bị Dọn Rác
- Mọi tool mới tạo trong `D:/Taadaa/tools/` BẮT BUỘC phải được đưa vào Git tracking (`git add` và commit) ngay khi hoàn thành kiểm thử.
- Tuyệt đối không để tool cốt lõi ở trạng thái untracked (`??`).
- Mọi thao tác dọn dẹp bắt buộc dùng `safe_recycle.py` (Atomic Quarantine vào `D:/.quarantine/`), TUYỆT ĐỐI CẤM dùng `rm`, `shutil.rmtree`, hay viết script xóa cứng diện rộng.

### D. Anti-Empty-Promise Invariant
- Không bao giờ phát ngôn "Em sẽ làm X ngay" rồi kết thúc lượt trả lời.
- Phải gọi tool thực hiện X ngay lập tức, thu thập bằng chứng thực thi thành công, rồi mới báo cáo kết quả đã hoàn thành.
