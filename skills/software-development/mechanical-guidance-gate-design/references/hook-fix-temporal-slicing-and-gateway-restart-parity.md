# Hook Fix Temporal Slicing & Gateway RAM Reload Parity

## 1. Context & Operational Friction
Khi Operator nhận báo cáo định kỳ 6h từ Watchdog giám sát tuân thủ (`gate_compliance_watchdog.py`) báo đỏ hàng loạt Gate (`FAIL` với hàng trăm vi phạm), dễ nảy sinh 2 thắc mắc cốt lõi:
1. "Sau khi tôi sửa xong các hook cách đây vài tiếng, các lỗi mới có còn tiếp tục xảy ra không?"
2. "Bản sửa đổi engine/hook đã thực sự được nạp (reload/restart) vào tiến trình Gateway đang chạy chưa?"

Nếu Coordinator chỉ đọc kết luận gộp của báo cáo 6h và trả lời "Vẫn FAIL", Operator sẽ hiểu lầm rằng bản vá hook hoàn toàn vô tác dụng.

---

## 2. Temporal Slicing Protocol (Bóc Tách Nhật Ký Theo Mốc Sửa Đổi)
Watchdog định kỳ quét theo cửa sổ trượt tĩnh (ví dụ: `cutoff = now - 6h`). Nếu bản sửa hook được commit vào giữa cửa sổ (ví dụ: sửa lúc 09:30 trong cửa sổ 06:00 -> 12:00), hơn 80% số vi phạm trong báo cáo thực chất là "tàn dư lịch sử" của giai đoạn trước khi sửa.

### Quy Trình Bóc Tách 3 Pha Bắt Buộc:
1. **Xác định mốc mtime của bản sửa (`T_FIX`):** Tra cứu timestamp sửa đổi file hook và commit git (`git log -n 1 --format="%cd" <hook_file>`).
2. **Phân chia 3 khung thời gian đối soát:**
   - **Pha 1 (Pre-Fix Window):** Từ đầu cửa sổ báo cáo đến `T_FIX` (`T_START` -> `T_FIX`).
   - **Pha 2 (Post-Fix In-Report Window):** Từ `T_FIX` đến mốc chốt báo cáo 6h (`T_FIX` -> `T_REPORT_END`).
   - **Pha 3 (Real-Time Post-Report Window):** Từ mốc chốt báo cáo đến thời điểm hiện tại (`T_REPORT_END` -> `NOW`).
3. **So sánh delta theo từng `rule_id` cụ thể:**
   - **Nhóm triệt tiêu thành công (Success):** Lỗi tụt về `0` tuyệt đối ở Pha 2 và Pha 3 (ví dụ: `GUARD_FOREGROUND_TIMEOUT_MISSING` và `GUARD_READ_FILE_SIZE_EXCEEDED` về 0 nhờ auto-rewrite).
   - **Nhóm lỗi còn sót do giới hạn phạm vi (Scope Gaps):**
     * Rule auto-rewrite chỉ xử lý khi thiếu tham số (`to is None`), nhưng chưa xử lý khi tham số vượt trần (`to > max_allowed`) $\to$ phát sinh `GUARD_FOREGROUND_TIMEOUT_EXCEEDED`.
     * Các cronjob nền chạy định kỳ tiếp tục vi phạm regex quét đĩa bảo vệ (ví dụ: `watch_d_live.py` gọi `admin_ssh.py` với `os.walk` trên `C:\Riot Games` $\to$ `GUARD_DANGEROUS_ROOT`).
     * Subagent cố tình sửa file trái hợp đồng $\to$ `subagent_edit_blocked`.

---

## 3. Gateway RAM Desync Verification & Reload Protocol
Khi bản sửa đổi chạm vào lõi engine Hermes (`agent/shell_hooks.py`, `hermes_cli/plugins.py`) để triển khai các hành động mới như `action: "rewrite"`, các hook subprocess (`guard_*.py`) trên đĩa dù in ra `rewrite` nhưng tiến trình Gateway đang chạy trong RAM sẽ **hoàn toàn mù** với cấu trúc này nếu chưa restart.

### Bằng Chứng Xác Nhận Lệch Pha RAM:
- Kiểm tra `create_time` của các tiến trình Gateway qua `psutil`:
  ```python
  # Tìm tiến trình gateway run
  for p in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
      if 'hermes_cli.main gateway run' in ' '.join(p.info.get('cmdline') or []):
          print(p.pid, datetime.fromtimestamp(p.create_time()))
  ```
- Nếu `gateway_started_at < hook_modified_at`: **Xác nhận 100% Gateway đang chạy bytecode cũ trong RAM**, chưa kích hoạt logic rewrite.

### Quy Trình Restart An Toàn Không Gián Đoạn:
1. **Pre-flight Import Test:** Chạy kiểm tra sạch trong subshell: `python -c "import gateway.run, hermes_constants; print('Import OK')"`. Nếu exit != 0, cấm restart.
2. **Delayed Detached Restart:** Sử dụng cơ chế khởi động lại trễ (`delayed-restart.ps1` hoặc `restart_gw_detached.py` delay 6s) để Gateway kịp hoàn tất gửi phản hồi turn hiện tại qua Telegram trước khi tiến trình cũ bị terminate và tiến trình mới nạp lại toàn bộ module vào RAM.
