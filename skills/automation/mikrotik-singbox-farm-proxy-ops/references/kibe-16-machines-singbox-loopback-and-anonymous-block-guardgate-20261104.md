# RCA & Bài Học Kỹ Thuật: Bẫy Loopback Singbox 16 Máy Kibe & Anti-Anonymous-Block GuardGate (2026-11-04)

## 1. Bẫy Tự Trỏ Loopback (Self-Loopback) Trong Generator Singbox
- **Hiện tượng:** Runner nuôi acc / lướt feed báo lỗi hàng loạt `Client.Timeout exceeded while awaiting headers` khi gọi `GET http://ifconfig.me/ip`. Log MikroTik RouterOS container báo:
  `ERROR connection: open connection to ifconfig.me:80 using outbound/http[proxy_m38]: dial tcp 192.168.110.2:20038: connect: cannot assign requested address`.
- **Nguyên nhân gốc rễ:**
  - Trong cấu hình Singbox gộp (`singbox_full_160.json`), 16 máy Kibe (`M33–M38`, `M71–M80`) không đi qua MobiProxy Thái Bình mà chạy qua các line MikroTik PPPoE Đà Nẵng (`10001..10007`) và line KhoaLee (`16002`).
  - Khi script `generate_singbox_config.py` đọc từ file Excel, cột proxy của các máy này bị điền thành `192.168.110.2:200xx` (chính là IP/port inbound của container).
  - Kết quả: Khi S7 gửi request vào `192.168.110.2:20033`, container Singbox nhận gói tin rồi lại mở socket kết nối vào chính cổng `20033` của chính nó $\rightarrow$ Tự nuốt socket, cạn port, sập preflight fail-closed.
- **Giải pháp chuẩn hóa:**
  - Trong `generate_singbox_config.py`, bắt buộc ánh xạ cứng bằng map:
    - `MIROTIK_MACHINES = [33, 34, 35, 36, 37, 71, 72, 73, 74, 75, 77, 78, 79, 80]` trỏ tới `mirotik1.taadaa.click:10001..10007` (user/pass: `admin@1:admin@1`).
    - `KHOALEE_MACHINES = [38, 76]` trỏ tới `khoalee.duckdns.org:16002` (user/pass: `5ns08q:AmLmaMJ0`).
  - Sinh file JSON minified (~27KB) và PATCH trực tiếp qua RouterOS REST API (`/rest/file/*8072575`), sau đó restart container `*6`.

## 2. Invariant GuardGate: `case_invariant_require_step_by_step_structure` (Chống Anonymous Block)
- **Quy tắc cứng:** Khi thêm/sửa code $\ge 15$ dòng trong các file `.py`, GuardGate cấm viết khối code vô danh liền mạch. Bắt buộc phải có comment định danh phân bước `# Step 1: ...`, `# Step 2: ...` (hoặc `# Bước X: ...`).
- **Khoảng trống Auto-Wire & Guidance:**
  - Mặc dù rule đã được ghi nhận trong `rules.json` và được theo dõi 24/7 qua watchdog `gate_compliance_watchdog.py` (Gate G4), nhưng ở tầng `unified_patch_pipeline.py` và `dispatch_worker.py` chưa tự động inject yêu cầu này vào prompt ban đầu cho Worker.
  - Khi Worker viết code mà thiếu `# Step X`, Closeout Gate sẽ bị `REJECTED (Score: 0)`.
  - **Kỷ luật thi công:** Khi dispatch Worker hoặc thực hiện Emergency Surgery, bắt buộc phải chủ động chia nhỏ và gắn comment `# Step 1: ...`, `# Step 2: ...` ở các khối logic mới $\ge 15$ dòng, đồng thời cập nhật kèm file test assertion tương ứng để thỏa mãn `MANDATORY_TEST_DELTA_VIOLATION`.
