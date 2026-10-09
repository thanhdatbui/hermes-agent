# BÀI HỌC VẬN HÀNH: 6 HARD GATES BẢO VỆ ĐIỀU PHỐI (CLAUDE OPUS HIGH AUDIT)

*(Rút ra từ sự cố Farm Alert M33 bị ngâm phiên >10 tiếng ngày 11-12/09/2026 do grep diện rộng, canary foreground dài, và worker lách luật dispatch contract)*

## 1. Bối Cảnh & 3 Nguyên Nhân Gốc Gây Treo Phiên
1. **Bẫy Grep Quét Đĩa Sâu (Broad Grep Timeout)**:
   - Coordinator chạy `grep -rn` hoặc `search_files` quét vào `D:/Taadaa`, `.ai-runs`, `runtime/kibe`, `python-envs`.
   - Các thư mục này chứa hàng vạn artifacts/ảnh/virtualenvs, lệnh chắc chắn dính timeout 180s-900s làm đứng im session.
2. **Bẫy Canary Chạy Foreground Chờ Thiết Bị (Synchronous Device I/O Stall)**:
   - Coordinator gọi `run-feed-session.ps1` ở foreground với `timeout=240` hoặc `300s`.
   - Khi điện thoại gặp lỗi UI/mạng, script kích hoạt fallback auto-login recovery chạy 3-5 phút làm toàn bộ session điều phối bị đóng băng hoàn toàn.
3. **Bẫy Lách Luật Dispatch Contract (Fake Compliance & Analysis Paralysis)**:
   - Coordinator điền đủ nhãn `FILE:`, `SCOPE:`, `FOCUSED_TEST:` nhưng bên trong lại giao goal mở ("kiểm tra và hoàn thiện...").
   - Worker nhận task dùng trần 15 tool calls (10-15 phút) chỉ để `read_file` phân trang và lên kế hoạch chứ không ghi byte nào xuống đĩa. Cần tới 4 lượt worker mới patch được code.
4. **Nhầm Lẫn Port Proxy Thiết Bị (Incidental Sidetrack)**:
   - Farm Kibe dùng quy ước: `port = 20000 + Machine_Number` (M33 = 20033).
   - Tự ý swap port hoặc đổi sang MikroTik 10001 (chưa bypass/auth trên Android) làm máy mất mạng thật. Máy nào phải giữ đúng port máy đó.

---

## 2. Kiến Trúc 6 Hard Gates (~/.hermes/hooks/)

Hệ thống chuyển dịch triệt để từ **"Denylist Regex / Soft Prompt"** sang **"Verification & Progress Supervisor"**:

| Gate | Hook File | Cơ Chế Bảo Vệ Vật Lý |
|---|---|---|
| **Gate 0** | `guard_progress_supervisor.py` | **Dead-man Switch**: Theo dõi nhịp tiến độ thực tế (Real State Change: patch, compile pass, pytest, git commit). Nếu sau 15 phút hoặc >8 calls mà không có State Change -> ĐÓNG BĂNG session, ép báo cáo user. |
| **Gate 1** | `guard_read_file_size.py` | Chặn `read_file` trên file > 10MB (ép dùng tail/grep O(1)). |
| **Gate 2** | `guard_pytest_scope.py` | Chặn `pytest` quét toàn bộ repo (ép trỏ đúng 1 file test). |
| **Gate 3** | `guard_dispatch_contract.py` | **Verified Contract Gate**: Phân luồng EDIT vs INVESTIGATE. Với EDIT: Hook tự đọc đĩa kiểm chứng `OLD_STRING` phải tồn tại DUY NHẤT 1 LẦN trong `FILE`. Chặn đứng fake compliance và goal mở. |
| **Gate 4** | `guard_broad_grep.py` | **Expanded Scan Guard**: Chặn toàn bộ họ lệnh quét (`grep -r`, `rg`, `find`, `findstr /s`, `Get-ChildItem -Recurse`, `search_files`) vào root, runs, runtime, envs. Cung cấp đường thay thế O(1). |
| **Gate 5** | `guard_device_bulkhead.py` | **Bulkhead & Circuit Breaker**: (1) Zero-Foreground Device I/O (chặn lệnh thiết bị foreground >60s, ép `background=True`); (2) Circuit Breaker: Cách ly (quarantine) máy fail liên tiếp >= 3 lần, cấm retry tự động làm nghẽn phiên. |

---

## 3. Quy Tắc Bất Khả Xâm Phạm Cho Coordinator
1. **ZERO Foreground Device I/O**: Không bao giờ chạy lệnh chạm điện thoại thật foreground > 60s. Phải chạy `background=True, notify_on_complete=True`.
2. **ZERO Open Goals Trên Monolith**: Coordinator bắt buộc tự grep O(1) lấy exact `OLD_STRING` trước khi dispatch worker. Worker chỉ việc áp patch và compile.
3. **CẤM Đổi Port Proxy Bừa Bãi**: Mỗi máy có port cố định theo quy chuẩn farm (`20000 + M#`). Tuyệt đối không swap port lung tung khi chưa kiểm tra bảng mapping `PROXYgandienthoai.xlsx`.
