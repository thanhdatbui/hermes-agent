# Dual-Cluster Remote ADB Timeout vs SSH Dispatch Protocol

## 1. Trực Quan Sự Cố (Remote ADB Timeout Trap)
Khi nhận Farm Alert với các máy thuộc cụm Admin (`M >= 200`):
- Chạy trực tiếp `python D:/Taadaa/tools/inspect_machine.py <N>` từ máy Kibe có thể bị treo và timeout sau 60s (`[Command timed out after 60s]`).
- **Nguyên nhân:** Lệnh nội bộ của `inspect_machine.py` cố gắng gọi `adb.exe -H 192.168.110.119 -P 5037 ...` qua mạng LAN. Nếu kết nối socket từ xa gặp độ trễ, handshake ADB giữa 2 host sẽ bị block.

## 2. Giải Pháp Chuẩn O(1) Qua SSH Nội Bộ
Thay vì gọi ADB socket xuyên máy, chuyển sang dispatch lệnh thực thi nội bộ ngay trên Host Admin thông qua SSH:
```bash
python D:/Taadaa/tools/admin_ssh.py "python D:/Taadaa/tools/inspect_machine.py <N>"
```
- **Thời gian phản hồi:** < 1.0 giây (thực tế đo đạc ~0.735s).
- **Kết quả:** Trích xuất đầy đủ trạng thái thiết bị thực tế gắn trên Admin host mà không bị nghẽn socket ADB remote.

## 3. Quy Tắc Bộ Lọc Lệnh (admin_ssh Allowlist)
`admin_ssh.py` áp dụng cơ chế bảo mật whitelist nghiêm ngặt:
- Các lệnh hệ thống ngoài danh mục (như `netstat`, shell pipe `|`, redirect) sẽ bị từ chối ngay lập tức:
  `Command rejected - not in allowlist: token='...'` (Exit code 2).
- Chỉ sử dụng các lệnh chuẩn hóa đã được cấp phép: `hostname`, và các tool Python chỉ định dưới `D:/Taadaa/tools/`.

## 4. Kỷ Luật Terminal Của Coordinator (Default-Deny)
- Terminal của Coordinator cấm tuyệt đối các cấu trúc vòng lặp bash shell như `for m in 14 30 35...`.
- Mọi thao tác inspect phải được gọi đơn lẻ theo từng lệnh trực tiếp hoặc gom vào script được phép để tránh bị Coordinator Guard chặn.
