# Regression Gate vs Protection Regression Gate & GuardGate 14 Invariants (2026-10-27)

## 1. Phán Quyết Về Kiến Trúc Chốt Chặn (Anti-Overengineering Consensus)
- **Câu hỏi của User**: *"Protection regression gate và regression gate đã phủ tất cả repo hệ thống chưa? Còn cái git hook gì đó phải hook quan trọng để vận hành farm hay là over-engineer?"*
- **Nguyên tắc cốt lõi**:
  1. **BÁC BỎ RẢI HOOK PHÂN TÁN:** Tuyệt đối KHÔNG rải các file `pre-push` / `pre-commit` vào `.git/hooks/` của 20 repos con. Farm hằng ngày chạy ngầm bằng Windows Task Scheduler và Python Cron, không bao giờ chạy `git push`. Rải hook khắp nơi là "bureaucratic theater" gây cản trở và lỗi môi trường khi thao tác bằng tay ngoài VS Code/CLI.
  2. **TẬP TRUNG TẠI 1 ĐẦU NÃO DUY NHẤT:** Mọi hoạt động chốt phiên bắt buộc đi qua `closeout_gate.py` (Step 2.5 gọi `guardgate/runner.py`) và `safe_push.py`. 
  3. **PHÂN BIỆT RÕ 2 CẤP ĐỘ GATE:**
     - *Regression Gate:* Kiểm tra chức năng (`pytest tests/test_*.py`). Đảm bảo code chạy đúng, tính năng không lỗi.
     - *Protection Regression Gate:* Chốt chặn cơ học luật bất biến sống còn (`GuardGate` đọc `rules.json` và `infra_regression_gate.py`). Quét trực tiếp `git diff`; vi phạm là đạp phanh (DENY) ngay lập tức, cấm bypass.

---

## 2. Danh Mục 14 Luật Bất Biến trong `guardgate/rules.json`

| # | Rule ID | Scope bảo vệ | Cơ chế kiểm tra (Predicate / Pattern) | Lý do lịch sử |
|---|---|---|---|---|
| 1 | `case_162_usb_micro_drop_timeout_floor` | `tiktok-luot nuoi acc` | `connection_wait_timeout >= 20.0s` | Chống sập cả dàn máy khi USB Hub sụt áp tức thời 5-10s |
| 2 | `case_161_natural_follow_limit_ceiling` | `tiktok-luot nuoi acc` | `follow_limit <= 0` | Cấm tự động bật follow dạo trong popup làm nick bị phạt spam |
| 3 | `case_invariant_prohibit_shell_uiautomator_dump` | Toàn Farm | `(?i)(uiautomator[\s'",]+dump\|import\s+uiautomator2)` | Cấm dump XML gây OOM-kill EXIT=137 trên Samsung S7; ép dùng WinRT OCR |
| 4 | `dispatch_worker_timeout_floor` | Toàn Farm | `--timeout >= 300s` | Cấm hạ timeout worker xuống 180s gây đứt gánh giữa chừng |
| 5 | `case_gpm_prohibit_skip_hotmail_login` | `GPM auto` | `initial_stage = "CHATGPT_REG" if has_token` | Bắt buộc khởi tạo `HOTMAIL_LOGIN` để lưu session/cookie (cứu 535 acc) |
| 6 | `case_invariant_prohibit_broad_disk_scan` | Toàn Farm | `(?i)(os\.walk\s*\(\s*["'][dD]:\|glob\s*\(\s*["'][dD]:)` | Cấm quét đĩa diện rộng trên root D:/ làm nghẽn Kernel I/O và treo Telegram |
| 7 | `case_invariant_prohibit_domain_in_android_proxy` | Phone Farm | `settings put global http_proxy <domain>` | Cấm domain ngoài; bắt buộc dùng IP LAN 192.168.110.2 để tránh Hairpin NAT drop |
| 8 | `case_invariant_prohibit_socks5h_scheme` | Hermes Gateway | `TELEGRAM_PROXY=socks5h://` | `httpx` không hỗ trợ `socks5h://`, gây crash-loop tiến trình Gateway |
| 9 | `case_invariant_prohibit_compound_password_check` | Toàn Farm | `if bool(username) and bool(password)` | Cấm bắt buộc password vì tài khoản reg OTP hợp lệ để trống pass |
| 10 | `case_invariant_prohibit_bulk_device_lock_reservation` | Toàn Farm | `bulk_lock_devices\|reserve_all_locks` | Cấm pre-reserve giữ lock hàng loạt trong queue, bắt buộc JIT lock từng máy |
| 11 | `case_invariant_prohibit_base64_in_terminal` | Toàn Farm | `cat ... \| base64\|base64 -w 0` | Cấm dump chuỗi base64 khổng lồ ra stdout làm phình context và nghẽn Event Loop |
| 12 | `case_invariant_prohibit_rogue_wifi_ssid` | Phone Farm | `--es ssid (Dat\|Dat-1\|BOX 2)` | Cấm gán SSID ngoài farm; cố định 4 AP Aruba farm |
| 13 | `case_invariant_prohibit_fake_tiktok_password` | Toàn Farm | `row["PASS"] = "(123456\|Taadaa@123)"` | Cột PASS chưa đặt pass bắt buộc để None, cấm ghi pass ảo |
| 14 | `case_invariant_prohibit_rest_day_no_follow_global_override` | `tiktok-luot nuoi acc` | `TAADAA_REST_DAY_NO_FOLLOW = "1" # global` | Cấm đè cờ dưỡng sinh lên toàn farm làm tắt nhầm follow ca bình thường |

---

## 3. Chốt Chặn Protection Regression Gate Hạ Tầng (`infra_regression_gate.py`)
Ngoài code farm, các thông số hạ tầng Hermes & OmniRoute được khóa cứng qua `infra_regression_gate.py`:
- `compression.threshold`: `[0.28, 0.35]` (chuẩn `0.30`).
- `agent.api_max_retries`: `[3, 4]`.
- `agent.api_retry_delay`: `[5.0, 12.0]` (chuẩn `6.0s`, tổng headroom ~90s).
- `fallback_providers`: Cấm trỏ ngược vào cổng 20129 (self-fallback loop).
- `PROXY_FAST_FAIL_TIMEOUT_MS`: `[4000, 10000]` (chuẩn `5000ms`, cấm 2000ms).
- `PROXY_FAIL_OPEN`: Bắt buộc `false` (cấm `true` tránh rò rỉ IP dân cư).
- `$MaxDeadlockFailures`: `[4, 6]` (chuẩn 4, ~120s).
- `cleanup_omniroute_db.py`: `RETENTION_DAYS <= 3` ngày trên đủ 6 bảng nặng, cron chạy mỗi 6h (`every 6h`).
