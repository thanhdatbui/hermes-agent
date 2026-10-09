# Multi-Stage Lifecycle Watchdog Reporting & Stage/Status Parity

## 1. Context & Motivation

Trong các hệ thống quản trị vòng đời tài khoản số lượng lớn (ví dụ: Hotmail -> GPM Login -> ChatGPT Reg -> Codex OAuth -> Wait 7D -> Change Info), một supervisor quản lý state machine cho hàng trăm profile thông qua file JSON state (`cron-state/*.json`).

Định kỳ (ví dụ mỗi 6 giờ), một watchdog reporting script (`cron_*_6h_report.py`) chạy để tổng hợp số liệu tiến độ và gửi báo cáo về Telegram (Farm Alerts).

Khi thiết kế báo cáo cho pipeline nhiều stage, có 3 cạm bẫy kỹ thuật kinh điển thường dẫn đến việc "che mắt" operator hoặc hiển thị sai lệch nghiêm trọng:

---

## 2. Pitfalls & Kỹ thuật Xử lý

### Pitfall 1: Flat List Truncation Monopolization (Cắt lát phẳng nuốt chửng lỗi stage khác)
- **Hiện tượng:** Script gom toàn bộ tài khoản bị lỗi (`status in ['FAILED', 'ERROR', 'BLOCKED']`) vào một danh sách phẳng `failed_profiles = []`. Khi in báo cáo ra màn hình / Telegram, script chỉ in 15 dòng đầu:
  ```python
  for fp in failed_profiles[:15]:
      print(f"  • M{fp['machine']} | {fp['email']} -> {fp['stage']} ({fp['detail']})")
  if len(failed_profiles) > 15:
      print(f"  • ... và {len(failed_profiles) - 15} tài khoản khác.")
  ```
- **Hậu quả:** Nếu một stage downstream (ví dụ `CODEX_OAUTH`) có cơ chế retry định kỳ và tích lũy 198 tài khoản lỗi, toàn bộ 15 dòng mẫu đầu tiên sẽ bị CODEX_OAUTH chiếm sạch. 33 tài khoản bị kẹt nghiêm trọng ở `HOTMAIL_LOGIN` và 1 tài khoản ở `CHATGPT_REG` bị đẩy hoàn toàn vào dòng `... và 217 tài khoản khác`. Operator nhìn báo cáo tưởng rằng Hotmail Login không có lỗi nào, chỉ có Codex OAuth lỗi.
- **Giải pháp (Per-Stage Bucketed Reporting):**
  Phân nhóm tài khoản lỗi theo Stage trước khi in:
  ```python
  from collections import defaultdict

  failed_by_stage = defaultdict(list)
  for fp in failed_profiles:
      failed_by_stage[fp['stage']].append(fp)

  print(f"\n🔴 TỔNG HỢP {len(failed_profiles)} TÀI KHOẢN GẶP LỖI THEO GIAI ĐOẠN:")
  for stage, items in sorted(failed_by_stage.items()):
      print(f"  📌 [{stage}]: {len(items)} tài khoản")
      for fp in items[:5]:  # Mẫu tối đa 5 nick cho mỗi stage
          m_str = f"M{int(fp['machine']):02d}" if fp.get('machine') is not None else "M??"
          print(f"     • {m_str} | {fp['email']} ({fp['detail']})")
      if len(items) > 5:
          print(f"     • ... và {len(items) - 5} nick khác.")
  ```

---

### Pitfall 2: Stage Identifier vs Completion Status Mismatch (Lệch trường định danh Stage và Status)
- **Hiện tượng:** Supervisor khi xử lý bước cuối cùng (`CHANGE_INFO`) ghi nhận:
  ```json
  "stage": "CHANGE_INFO",
  "status": "DONE",
  "last_result": { "stage": "CHANGE_INFO", "status": "DONE" }
  ```
  Nhưng script báo cáo lại kiểm tra theo chuỗi `stage`:
  ```python
  if st == "WAIT_24_48H":
      waiting_24h += 1
  elif st == "WAIT_7D":
      waiting_7d += 1
  elif st == "DONE":
      done += 1  # st ở đây lấy từ info.get("stage") -> luôn là "CHANGE_INFO", không bao giờ bằng "DONE"!
  ```
- **Hậu quả:** Dù thực tế 29 tài khoản đã hoàn thành toàn bộ chu trình (`status: DONE`), báo cáo vẫn in: `Đã hoàn thành toàn bộ chu kỳ (DONE): 0`. Operator hoang mang tưởng chưa nick nào hoàn tất.
- **Giải pháp:**
  Kiểm tra điều kiện hoàn thành kết hợp cả `status` lẫn `stage`:
  ```python
  if status == "DONE" or last_status == "DONE" or st == "DONE":
      done += 1
  elif st == "WAIT_24_48H":
      waiting_24h += 1
  elif st == "WAIT_7D":
      waiting_7d += 1
  ```

---

### Pitfall 3: Selective Auto-Unblock tạo ảo giác "chỉ có 1 loại lỗi đang chạy"
- **Hiện tượng:** Trong hàm `select_candidates()` của supervisor:
  - Tài khoản kẹt `CODEX_OAUTH` có cờ `chatgpt_registered_at` được supervisor tự động unblock mỗi 30 phút (`stage = "WAIT_24_48H"`, `status = "PENDING"`) để quét bù số điện thoại.
  - Tài khoản lỗi ở `HOTMAIL_LOGIN` hoặc `CHATGPT_REG` bị đánh dấu `BLOCKED` và bị loại trừ vĩnh viễn (`if status in {"WAITING", "FAILED", "ERROR", "BLOCKED"}: continue`).
- **Hậu quả:** Mục `Tiến độ xử lý trong 6h vừa qua` chỉ toàn hiện 110 sự kiện `CODEX_OAUTH: FAILED`. Hotmail Login không sinh thêm sự kiện nào trong 6h vì đã bị `BLOCKED` từ tuần trước. Operator thấy log 6h chỉ có Codex OAuth nên tưởng Hotmail Login không chạy hoặc không có vấn đề gì.
- **Giải pháp:**
  Trong báo cáo định kỳ, tách biệt rõ:
  1. **Lỗi tĩnh (Stale Blocked Backlog):** Số tài khoản đang bị kẹt BLOCKED cần operator can thiệp mở khóa / thay proxy / kiểm tra pass.
  2. **Tiến độ động (Dynamic Events in Last 6H):** Số lượt thực thi phát sinh trong cửa sổ thời gian gần nhất.
