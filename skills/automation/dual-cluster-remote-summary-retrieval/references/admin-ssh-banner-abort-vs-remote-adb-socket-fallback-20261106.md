# Admin Cluster SSH Banner Abort vs Remote ADB Socket Fallback (2026-11-06)

## 1. Hiện Tượng Thực Tế
- Báo cáo 2FA TikTok ban đêm toàn farm (`night_2fa_trace_2026-11-06.log`):
  - Farm Kibe (Máy 1-80): Hoàn tất 12 | Bỏ qua 3 | Lỗi 48 (47 ConsumerPreflightError, 1 TWO_STEP_NOT_REACHED).
  - Farm Admin (Máy 201-280): Hoàn tất 0 | Bỏ qua 0 | Lỗi 0 | Lỗi runner: mã thoát 255.
- Cụm Admin liệt 100% mục tiêu do lệnh bọc qua SSH `admin_ssh.py` / `ssh admin-farm` văng mã thoát 255 ngay lập tức.

## 2. Bản Chất Lỗi SSH & Bài Học Triage Từ User (Anti-Hallucination)
- **Triệu chứng mạng:**
  - `ping 192.168.110.119`: Phản hồi `<1ms`, TTL=128 (máy sống bình thường).
  - Cổng 22 TCP Handshake (SYN -> SYN/ACK -> ACK) thành công, nhưng ngay lập tức remote host gửi RST:
    `Socket error: [WinError 10054] An existing connection was forcibly closed by the remote host`
  - Lệnh SSH client báo:
    `kex_exchange_identification: read: Software caused connection abort`
    `banner exchange: Connection to 192.168.110.119 port 22: Software caused connection abort`
- **Bài học Triage khi User phản ánh "Máy reset liên tục mà sao bảo treo SSH?":**
  - Khi máy chủ thường xuyên reboot, bất kỳ tiến trình zombie hay socket treo tạm thời đều đã được giải phóng sau reboot.
  - Do đó, nếu lỗi reset kết nối xảy ra kiên trì sau reboot ngay tại bước trao đổi Banner (`banner exchange`), đây **KHÔNG PHẢI lỗi tiến trình tạm thời**, mà là **lỗi cấu hình/phân quyền tĩnh (Persistent Host State)**:
    1. **Quyền hạn file Host Key (`ssh_host_*_key` ACLs):** Trên Windows OpenSSH, nếu quyền của thư mục `C:\ProgramData\ssh\` hoặc các khóa host private bị thừa/lệch ACL, tiến trình con của `sshd.exe` khi fork sẽ tự hủy kết nối ngay trước khi gửi banner SSH. (Cần chạy `FixHostFilePermissions.ps1`).
    2. **Lỗi mã hóa/cú pháp `sshd_config`:** Lưu sai encoding (UTF-8 BOM) hoặc directive không tương thích.
    3. **Tường lửa/Antivirus:** Chặn child process spawned bởi `sshd`.

## 3. Kiến Trúc Cứu Hộ: Remote ADB Socket Fallback (Port 5037)
- Trong khi SSH (port 22) bị nghẽn, **cổng ADB daemon `192.168.110.119:5037` vẫn LIVE 100%** và nhận đủ 78 thiết bị vật lý (`adb -H 192.168.110.119 -P 5037 devices`).
- `run_capture_phase_b.py` đã có sẵn cơ chế auto-routing:
  ```python
  def resolve_cluster_adb_endpoint(machine: str):
      if int(machine) >= 200:
          return "192.168.110.119", 5037, r"D:\Taadaa\machine-config\admin.yaml"
      return None, None, r"D:\Taadaa\machine-config\kibe.yaml"
  ```
- **Kỷ luật điều phối:** Khi runner điều phối gặp lỗi SSH sang host Admin, không được dừng toàn bộ cụm nếu runner trên Kibe có thể chuyển chế độ chạy trực tiếp sang Remote ADB Socket qua mạng LAN để tiếp tục thi công.

## 4. Triage Cụm Kibe (MobiProxy Timeout Preflight)
- 47 máy Kibe văng `ConsumerPreflightError` do DNAT trên MikroTik (`20001..20038` trỏ sang MobiProxy `116.107.124.158:5101..5138`) bị timeout.
- Cổng preflight `check_android_vpn` fail-closed chuẩn xác, ngăn chặn việc rò rỉ IP gốc nhà mạng khi proxy chết.
