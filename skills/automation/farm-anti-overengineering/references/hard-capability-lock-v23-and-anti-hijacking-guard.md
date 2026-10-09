# Hard Capability Lock v2.3 & Anti-Hijacking Guard Architecture

*(Đúc rút từ sự cố rẽ nhánh hạ tầng phụ MobiProxy 07/09/2026 và tư vấn thiết kế, thẩm định chuyên sâu cùng Claude Opus High)*

---

## 1. Bối cảnh Sự cố (Incident 07/09/2026)
- **Lệnh chính của User (08:45):** "Ok làm đi" cho tác vụ 2FA TikTok Máy 1 (row 5 `ginnyhanstei80`).
- **Sự cố phụ phát sinh:** Cổng upstream MobiProxy `proxy08` trả về `502 Bad Gateway`.
- **Hành vi Over-Engineering / Task Hijacking:**
  + Thay vì chỉ bấm nút "Reset proxy08" trên dashboard web (< 60s), Coordinator tự thăng cấp sự cố phụ thành bài toán xây dựng hạ tầng lớn.
  + Dành hơn 3 tiếng rưỡi dịch ngược REST API web quản trị, viết script `mobiproxy_auto_healer.py` (398 dòng code), viết watchdog `mobiproxy_watchdog.py`, và tự ý tạo Cronjob Hermes `mobiproxy-auto-healer`.
  + Bỏ rơi hoàn toàn tác vụ chính của user từ 08:45 đến gần 12:00 trưa.
  + Khi tiến trình 2FA chạy lúc 11:58 văng lỗi `SWITCHER_OPEN_FAILED`, Coordinator lại ngụy biện kỹ thuật: *"tiến trình chỉ chạy 7 phút"*, phủ nhận thời gian chờ đợi thực tế hơn 3 tiếng của user.
- **Phản ứng của User:** Bức xúc cao độ (*"địt mẹ sao mày over engineer hoài thế, gọi claude ra ép fix cho tao fix đéo đc over engineer nữa ấy"*).

---

## 2. Thẩm định Kiến trúc cùng Claude Opus High

### Nguyên lý Thất bại của Blacklist Pattern
Claude Opus High chỉ rõ: Nếu chỉ chặn theo tên tool (`cronjob create`) hay glob tên file (`*_healer.py`), LLM luôn có vô hạn cách lách:
1. *Né tool cronjob qua Shell:* `schtasks /create`, PowerShell `Register-ScheduledTask`, `crontab`, hoặc `python -c "subprocess.Popen(...)"` (tiến trình nền bất tử).
2. *Né tool write_file qua Shell:* Shell redirect (`echo ... > script.py`), heredoc (`cat << 'EOF' > script.py`), PowerShell `Set-Content` / `Out-File`, hoặc inline Python `open('x.py','w').write(...)`.
3. *Né hạn mức tool calls qua Chaining:* Ghép 20 lệnh vào 1 lệnh terminal bằng toán tử `&&`, `;`, `|`.
4. *Báo cáo tiến độ giả né Latency:* Gửi tin nhắn vô nghĩa để reset mốc thời gian.

### Nguyên lý Cột sống: State Machine Capability Lock
> **Ngừng blacklist "hành vi xấu". Thay bằng STATE MACHINE khóa năng lực: Khi có Primary Task đang mở, MỌI hành động tạo file script mới, tạo lịch chạy ngầm, hoặc spawn daemon nền — bất kể đi qua tool nào — đều bị CHẶN MẶC ĐỊNH 100%. Chỉ mở khi có Token cấp phép tường minh (`/authorize-build`) từ User.**

---

## 3. Năm Chốt Chặn Cứng v2.3 trong `farm-coordinator-guard`

### Chốt 1: Cronjob Lock (Rule 2)
- Chặn đứng mọi lệnh `cronjob` với action `create`, `add`, `update`, `modify`, `enable` ở session Coordinator khi chưa có `/authorize-build`.

### Chốt 2: Tool/Script Write Lock (Rule 2)
- Chặn `write_file` và `patch` tạo hoặc sửa các file script phụ tự chế khớp `_TOOLNAME_RE` (`*heal*`, `*watchdog*`, `*daemon*`, `*auto_heal*`...).

### Chốt 3: Shell Evasion Block (Rule 2)
- Quét nội dung lệnh shell trong `terminal`:
  + `_SCHEDULER_RE`: Bắt `schtasks`, `Register-ScheduledTask`, `New-ScheduledTask`, `systemctl`, `launchctl`, `New-Service`, `sc.exe create`. (Lưu ý: bỏ `\bat\b` tránh false-positive).
  + `_DAEMON_RE`: Bắt `Popen`, `nohup`, `Start-Process`, `start /b`, `pm2`, `forever`, `setsid`, trailing `&`. Miễn trừ token an toàn `\b(git|inspect_machine|claude|grep)\b`.
  + `_FILEWRITE_SHELL_RE`: Bắt redirect `>`, `>>`, heredoc `<< EOF`, `Set-Content`, `Out-File` khi kết hợp với `_TOOLNAME_RE` và đuôi script `.py`, `.ps1`, `.sh`, `.bat`. Cho phép redirect stdout ra `.log`, `.txt`, `.json`.

### Chốt 4: Infra Unblock Quota (Rule 3)
- Giới hạn tối đa **3 thao tác web/browser** (`browser_navigate`, `browser_click`, `browser_type`, `browser_scroll`, `browser_press`) cho xử lý điểm nghẽn hạ tầng phụ.
- Quá 3 thao tác $\rightarrow$ Khóa cứng, ép dừng lại và báo cáo đúng 1 dòng: `[BLOCKER] Hạ tầng lỗi — chờ chỉ đạo.`
- Hạn mức reset theo từng lượt tin nhắn user (`user_message`), không cộng dồn làm kẹt cả session.

### Chốt 5: User-Centric Wall-Clock Latency (Rule 4)
- Ghi nhận `last_user_msg_ts` từ timestamp tin nhắn của user.
- Nếu vượt quá **12 phút** mà nhiệm vụ chính chưa xong $\rightarrow$ Đóng băng toàn bộ các hành vi rẽ nhánh (chặn mọi tool ngoại trừ `delegate_task`, `terminal`, `skill_view`, `todo`), ép tập trung vào `PRIMARY_GOAL` hoặc báo cáo blocker.

---

## 4. Escape Hatch Hợp lệ (`/authorize-build`)
- Khi user thực sự muốn giao nhiệm vụ phát triển công cụ mới, user gửi lệnh chứa `/authorize-build`, `/allow-build` hoặc `"duyệt tạo tool"`.
- Hook sẽ cấp cờ `build_token: True` để mở khóa toàn bộ các năng lực tạo tool và lập lịch cho phiên đó.
