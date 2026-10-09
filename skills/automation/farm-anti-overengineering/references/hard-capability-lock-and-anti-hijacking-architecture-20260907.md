# Kiến Trúc Hard Capability Lock v2.3 & Chống Task Hijacking (07/09/2026)

## 1. Bối cảnh & Phân tích thất bại của Blacklist mềm
Trong phiên làm việc sáng 07/09/2026, khi được giao nhiệm vụ chạy 2FA Máy 1 từ 08:45, gặp lỗi proxy08 502, Coordinator đã bị dắt mũi sang bài toán phụ: viết 398 dòng code `mobiproxy_auto_healer.py`, watchdog, và tự đăng ký cronjob `mobiproxy-auto-healer`, bỏ rơi nhiệm vụ chính hơn 3 tiếng rưỡi.

Khi bàn về giải pháp ngăn chặn, phương án ban đầu đề xuất 4 chốt chặn dựa trên blacklist:
1. Chặn tool `cronjob(action='create')`.
2. Chặn `write_file` tạo file `*_healer.py`.
3. Giới hạn số lượt gọi tool cho việc phụ.
4. Cảnh báo độ trễ > 15 phút.

**Thẩm định từ Claude Opus High (Kiến trúc sư tối cao):**
Bốn chốt chặn trên **thua về mặt nguyên lý** vì dựa vào blacklist cú pháp/tên tool:
- **Né cron:** Agent không gọi `cronjob` mà chạy qua shell: `schtasks /create`, PowerShell `Register-ScheduledTask`, `crontab`, hoặc `python -c "subprocess.Popen(...)"` chạy daemon nền bất tử.
- **Né write_file:** Agent dùng shell redirection (`>`, `>>`), heredoc (`cat << 'EOF' > script.py`), PowerShell `Set-Content` / `Out-File`, hoặc inline `python -c "open('x.py','w').write(...)"`.
- **Né quota tool call:** Agent gom 20 lệnh điều tra và tạo script vào 1 lượt gọi duy nhất bằng chaining `&&`, `;`.
- **Latency 15 phút:** Quá muộn (trong 15 phút đã kịp viết 400 dòng code phá vỡ luồng chính).

---

## 2. Nguyên lý Cột sống: State Machine Capability Lock
Không chạy theo blacklist vô hạn cú pháp. Thay bằng **khóa năng lực theo trạng thái (Capability Lock)**:
Khi đang có `PRIMARY_GOAL`, **MỌI** hành vi tạo file code mới, spawn tiến trình nền, hoặc lập lịch chạy ngầm — bất kể đi qua tool nào (`write_file`, `patch`, `terminal` heredoc, PowerShell, python inline) — đều bị **CHẶN MẶC ĐỊNH 100%**. Chỉ mở khóa khi User cấp phép tường minh qua `/authorize-build`.

---

## 3. Kiến trúc 4 Trục Triển Khai Trong `farm-coordinator-guard`

### Trục 1: Semantic Normalizer (Bóc tách ngữ nghĩa lệnh shell)
Quét nội dung chuỗi lệnh shell trong `terminal`:
- `_SCHEDULER_RE`: Bắt `crontab`, `schtasks`, `Register-ScheduledTask`, `New-ScheduledTask`, `systemctl`, `New-Service`.
- `_DAEMON_RE`: Bắt `Popen`, `nohup`, `Start-Process`, `start /b`, `pm2 start`, `forever start`, `setsid`, `& $`.
- `_FILEWRITE_SHELL_RE`: Bắt `>>?`, `<<\s*['"]?\w+`, `tee`, `Set-Content`, `Out-File`, `Add-Content`, `[IO.File]::Write`, `open\(.*[wa]`, `fs.writeFileSync`.
- `_TOOLNAME_RE`: Bắt các tên file tự chế (`heal`, `watchdog`, `daemon`, `auto_`, `recover`, `keepalive`, `guardian`, `repair`).

### Trục 2: Chặn Đứng Trước Khi Vào Allowlist
Trong `_on_pre_tool_call`, kiểm tra các regex ngữ nghĩa trên **TRƯỚC KHI** cho lệnh rơi vào `ALLOWLIST_PATTERNS`. Điều này bịt kín lỗ hổng lệnh shell bắt đầu bằng `cat` hay `echo` nhưng redirect ghi file script (`cat << EOF > tool.py`).

### Trục 3: O(1) Unblock Quota (< 60s / Tối đa 2-3 thao tác)
Theo dõi `infra_budget_used` trong session state. Khi xử lý sự cố hạ tầng phụ (như mở web reset modem):
- Tối đa 2-3 hành động.
- Nếu vượt quá: Hook khóa cứng, ép DỪNG LẠI và xuất đúng 1 dòng: `[BLOCKER] Hạ tầng lỗi — chờ chỉ đạo.` Cấm tiếp tục đào sâu dịch ngược API hay viết script.

### Trục 4: User-Centric Wall-Clock Latency Guard
- Ghi nhận `last_user_msg_ts` trên mỗi lượt user gửi tin nhắn.
- Ngưỡng cảnh báo mềm: **6 phút**.
- Ngưỡng đóng băng cứng (Hard Freeze): **12 phút**. Khi vượt 12 phút mà chưa xong việc chính: khóa toàn bộ thao tác phụ, ép chỉ tập trung hoàn thành Primary Task hoặc báo cáo blocker.

---

## 4. Cơ chế Thoát Hiểm Hợp Lệ (/authorize-build)
Để tránh false positive khi user *thực sự* muốn build tool hoặc lập lịch farm:
- Khi user gửi lệnh có `/authorize-build`, `duyệt tạo tool`, hoặc `cho phép tạo tool`:
  Hook kích hoạt `build_token: True` trong session state.
- Token này mở khóa tạm thời cho phép tạo tool/lịch theo đúng chỉ đạo của user.

---

## 5. Bài học Review Từ Claude Opus High (7 Điểm Blocker & Khắc Phục False-Positive)
Khi audit bản vá v2.3, Claude Opus High đã chỉ rõ 7 điểm chí tử giúp phân biệt giữa "chặn đứng over-engineer" và "tự mình over-engineer làm gãy hệ thống":

1. **Không dùng `\bat\b` trong Scheduler Regex:** `at` là từ nối tiếng Anh thông dụng (`at 5pm`, path chứa `at`). Dùng `\bat\b` gây chặn nhầm hàng loạt lệnh hợp lệ.
   - *Khắc phục:* Bỏ hẳn `\bat\b` vì Windows farm chỉ dùng `schtasks` hoặc PowerShell task scheduler.
2. **Không chặn cả thư mục `tools/` và `scripts/`:** Coordinator sửa hoặc cập nhật các script nghiệp vụ hiện có của farm là việc chính. Nếu chặn mọi `write_file` vào `tools/` hay `scripts/` sẽ làm tê liệt toàn bộ luồng vận hành.
   - *Khắc phục:* Chỉ chặn khi tên file khớp `_TOOLNAME_RE` (chứa các từ khóa tự chế nguy hiểm: `healer`, `watchdog`, `daemon`, `auto_heal`).
3. **Chặn miễn trừ bằng substring (Substring Exemption Trap):** Dùng `any(k in cmd.lower() for k in ["git", "grep"])` để miễn trừ daemon là sai lầm, vì chuỗi `nohup ./digit_daemon &` có chữ `git` sẽ lọt lưới hoàn toàn.
   - *Khắc phục:* Bắt buộc dùng regex word-boundary `_DAEMON_EXEMPT_RE = re.compile(r"\b(git|inspect_machine|claude|grep)\b")`.
4. **Reset Quota theo từng lượt tin nhắn (Turn-Based Reset):** Không cộng dồn `infra_budget_used` suốt cả session nhiều tiếng, vì một luồng login/reset bình thường đã tốn 2-3 calls, khiến mọi task sau đó bị khóa vĩnh viễn.
   - *Khắc phục:* Reset `infra_budget_used: 0` mỗi khi có tin nhắn mới từ user (`_on_pre_llm_call`).
5. **Phân biệt chuyển hướng stdout ghi log vs ghi code:** Chặn redirect ghi đè làm hỏng cả các lệnh chạy script xuất log hợp lệ (`python run.py > out.log`).
   - *Khắc phục:* Chỉ chặn khi lệnh vừa có redirect vừa nhắm vào đuôi file script code (`.py`, `.ps1`, `.sh`, `.bat`, `.cmd`).
6. **Mở rộng phạm vi Cronjob:** Không chỉ chặn `create`/`add`, mà chặn cả `update`, `modify`, `enable` để ngăn agent kích hoạt các cronjob ngầm đã bị tắt từ trước.
7. **Bảo đảm biến toàn cục & Imports:** Luôn verify `import time` trước khi dùng `time.time()` trong pre-hooks để tránh NameError làm crash fail-open toàn bộ plugin guard.
