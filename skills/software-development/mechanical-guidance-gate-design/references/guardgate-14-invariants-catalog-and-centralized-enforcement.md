# GuardGate 14 Invariants Catalog & Centralized Gate Enforcement Architecture (2026-10-27)

## 1. Bối cảnh & Vấn đề Cốt lõi
Khi mở rộng hệ thống Taadaa Farm gồm hơn 20 Git repositories (`tiktok-luot nuoi acc`, `Tiktok-video`, `Tiktok_Reg`, `automation-core`, `GPM auto`, `tools`...), câu hỏi đặt ra:
- *Có nên rải Git hooks (`pre-push`, `pre-commit`) phân tán vào tất cả 20 repo con hay không?*
- *Phân biệt thế nào giữa Regression Gate và Protection Regression Gate?*

### Phán Quyết Kiến Trúc (Anti-Overengineering Consensus)
1. **BÁC BỎ RẢI HOOK PHÂN TÁN (Bureaucratic Theater):**
   - Farm vận hành hằng ngày qua Windows Task Scheduler, Python Cron và ADB daemon — **hoàn toàn chạy local, tuyệt đối không có dòng code nào chạy `git push`**.
   - `git push` chỉ xảy ra khi lập trình viên hoặc AI Coordinator chốt phiên làm việc.
   - Rải 20 file hook vào `.git/hooks/` của 20 repo là over-engineering: khó quản lý, dễ vỡ môi trường virtualenv Python, và cản trở thao tác sửa lỗi khẩn cấp bằng tay qua VS Code / Desktop CLI.
2. **KIẾN TRÚC TẬP TRUNG TẠI ĐẦU NÃO (Single Centralized Gatekeeper):**
   - Toàn bộ chốt chặn được tập trung tại đúng 1 cổng: **`D:/Taadaa/tools/closeout_gate.py` (Step 2.5)** và **`safe_push.py`**.
   - Engine `GuardGate` (`D:/Taadaa/tools/guardgate/engine.py`) quét trực tiếp `git diff` của bất kỳ repo nào đang được review chốt phiên, đối chiếu với bộ luật bất biến tại `guardgate/rules.json`.

---

## 2. Phân Định 2 Cấp Độ Gate
| Tiêu chí | 1. Regression Gate (Chức năng) | 2. Protection Regression Gate (Bất biến) |
| :--- | :--- | :--- |
| **Bản chất** | Kiểm tra logic phần mềm (`pytest`) | Chốt chặn cơ học luật sống còn (`GuardGate` & `infra_regression_gate.py`) |
| **Mục tiêu** | Đảm bảo code chạy đúng tính năng, không làm gãy hàm cũ | Đảm bảo code KHÔNG phạm vào các bài học xương máu lịch sử |
| **Cách kiểm tra** | Chạy toàn bộ suite `test_*.py` của repo | Quét cưỡng chế từng dòng trong `git diff` |
| **Hành vi** | Test fail có thể cập nhật test cho khớp spec mới | Vi phạm là **ĐẠP PHANH NGAY LẬP TỨC (DENY)**, cấm bypass |

---

## 3. Danh Mục 14 Luật Bất Biến trong `guardgate/rules.json`

### Nhóm 1: An toàn Thiết bị & Phần cứng Farm
1. **`case_162_usb_micro_drop_timeout_floor` (`tiktok-luot nuoi acc`):**
   - *Luật:* `connection_wait_timeout >= 20.0s`.
   - *Bảo vệ:* Chống sập hàng loạt máy khi USB Hub bị sụt áp tức thời 5–10s.
2. **`case_invariant_prohibit_shell_uiautomator_dump` (Toàn Farm):**
   - *Pattern:* `(?i)(uiautomator[\s'",]+dump|import\s+uiautomator2|from\s+uiautomator2)`
   - *Bảo vệ:* Cấm shell uiautomator dump vì gây OOM-kill `EXIT=137` trên Samsung S7. Ép dùng WinRT OCR hoặc ATX-Agent port 7912.
3. **`case_invariant_prohibit_rogue_wifi_ssid` (Toàn Farm):**
   - *Pattern:* `(?i)(--es\s+ssid\s+["']?(Dat|Dat-1|BOX\s*2|Home|Office)["']?|join_wifi\(.*["'](Dat|Dat-1|BOX\s*2)["'])`
   - *Bảo vệ:* Cấm kết nối hoặc fallback sang SSID ngoài farm. Cố định 4 AP Aruba farm (`kibe 1`, `kibe 2`, `admin 1`, `admin 2`) để chống lệch subnet và rò rỉ IP direct.
4. **`case_invariant_prohibit_domain_in_android_proxy` (Phone Farm):**
   - *Pattern:* `(?i)settings\s+put\s+global\s+http_proxy\s+[\w.-]+\.(taadaa\.click|com|net|org)`
   - *Bảo vệ:* Cấm gán hostname/domain ngoài vào `http_proxy`. Bắt buộc dùng IP LAN `192.168.110.2:<port>` để tránh Hairpin NAT drop gây chấm than Wi-Fi.

### Nhóm 2: An toàn Tài khoản TikTok & Vận Hành Nuôi Feed
5. **`case_161_natural_follow_limit_ceiling` (`tiktok-luot nuoi acc`):**
   - *Luật:* `follow_limit <= 0` trong popup bạn bè.
   - *Bảo vệ:* Cấm bật tự động follow dạo trong popup làm nick bị TikTok phạt spam.
6. **`case_invariant_prohibit_compound_password_check` (Toàn Farm):**
   - *Pattern:* `(?i)if\s+bool\s*\(\s*username\s*\)\s+and\s+bool\s*\(\s*password\s*\)`
   - *Bảo vệ:* Cấm kiểm tra bắt buộc phải có password vì hàng trăm tài khoản TikTok reg bằng OTP để trống pass nhưng đang chạy feed thật bình thường.
7. **`case_invariant_prohibit_fake_tiktok_password` (Toàn Farm):**
   - *Pattern:* `(?i)row\[["']PASS["']\]\s*=\s*["'](123456|Taadaa@123|password|abc123)["']`
   - *Bảo vệ:* Cột PASS chưa đặt mật khẩu bắt buộc để `None`, cấm gán mật khẩu giả định.
8. **`case_invariant_prohibit_bulk_device_lock_reservation` (Toàn Farm):**
   - *Pattern:* `(?i)(bulk_lock_devices|reserve_all_locks|for\s+\w+\s+in\s+machines:\s*acquire_device_lock)`
   - *Bảo vệ:* Cấm bulk pre-reserve giữ lock hàng loạt trong queue; bắt buộc dùng Just-In-Time (JIT) lock từng máy.
9. **`case_invariant_prohibit_rest_day_no_follow_global_override` (`tiktok-luot nuoi acc`):**
   - *Pattern:* `(?i)os\.environ\[["']TAADAA_REST_DAY_NO_FOLLOW["']\]\s*=\s*["']1["']\s*#\s*global`
   - *Bảo vệ:* Cấm đè cờ dưỡng sinh lên toàn farm làm tắt nhầm tính năng follow của các ca bình thường (Commit `7d3ba44`).

### Nhóm 3: An toàn Dữ liệu & Automation GPM
10. **`case_gpm_prohibit_skip_hotmail_login` (`GPM auto`):**
    - *Pattern:* `(?i)initial_stage\s*=\s*["']CHATGPT_REG["']\s+if\s+has_token`
    - *Bảo vệ:* Bắt buộc mọi tài khoản Hotmail phải khởi tạo `HOTMAIL_LOGIN` để lưu cookie/session trên GPM trước khi sang reg ChatGPT.

### Nhóm 4: An toàn Hạ tầng Hermes, Worker & Context Hygiene
11. **`dispatch_worker_timeout_floor` (Toàn Farm):**
    - *Luật:* `--timeout` mặc định của Worker trong `dispatch_worker.py` và `sol_repair.py` $\ge 300$s.
    - *Bảo vệ:* Cấm hạ timeout worker xuống 180s làm worker đứt gánh giữa chừng.
12. **`case_invariant_prohibit_broad_disk_scan` (Toàn Farm):**
    - *Pattern:* `(?i)(os\.walk\s*\(\s*["'][dD]:[/\\\\]?["']|glob\s*\(\s*["'][dD]:[/\\\\]?\*|rglob\s*\(\s*["'][dD]:[/\\\\]?\*)`
    - *Bảo vệ:* Cấm quét đĩa diện rộng trên thư mục gốc `D:/` gây nghẽn Kernel I/O và treo bot Telegram.
13. **`case_invariant_prohibit_base64_in_terminal` (Toàn Farm):**
    - *Pattern:* `(?i)(cat\s+.*\|\s*base64|base64\s+-w\s*0|echo\s+.*\|\s*base64)`
    - *Bảo vệ:* Cấm dump chuỗi base64 khổng lồ ra terminal stdout gây bloat context và nghẽn Event Loop.
14. **`case_invariant_prohibit_socks5h_scheme` (Hermes Gateway):**
    - *Pattern:* `(?i)TELEGRAM_PROXY=socks5h://`
    - *Bảo vệ:* `httpx` không hỗ trợ scheme `socks5h://`, dùng sẽ gây crash-loop Gateway. Bắt buộc dùng `socks5://127.0.0.1:40000`.

---

## 4. Kiểm Thử Cơ Học (Mechanical Testing)
- Mọi rule mới nạp vào `rules.json` bắt buộc phải có cặp vector đối kháng trong `guardgate/test_rules.py`:
  + Vector `ALLOW`: Code tuân thủ đúng chuẩn $\rightarrow$ `status == ALLOW`.
  + Vector `DENY`: Code vi phạm điều cấm $\rightarrow$ `status == DENY` kèm đúng `rule_id`.
- Chạy toàn bộ suite: `pytest D:/Taadaa/tools/guardgate` (đảm bảo 100% test pass trong < 1.5s).
