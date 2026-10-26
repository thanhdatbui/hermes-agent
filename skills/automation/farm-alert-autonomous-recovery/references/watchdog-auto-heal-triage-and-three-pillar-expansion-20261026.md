# Watchdog Auto-Heal Triage & Three-Pillar Expansion (Feed, Follow, Upload)

> Tổng kết chẩn đoán và mở rộng cơ chế Closed-Loop Auto-Repair tự động chữa lỗi sau ca chạy trên Taadaa Phone Farm (26/10/2026).

---

## 1. Triệu Chứng & 3 Điểm Nghẽn Khiến Auto-Heal Bị Đóng Băng
Khi người dùng nhận thấy sau mỗi report watchdog ca nuôi acc / follow / upload mà Auto-Heal không hề chạy:
1. **Bẫy Serial ADB Thô (`serial="48"` thay vì Hardware Serial):**
   - Trong watchdog tổng kết ca (`feed_session_watchdog.py`), danh sách máy lỗi `m_list` chứa nhãn `M16`, `M48`... Hàm gọi `emit_if_needed(serial=m_num, machine_id=m_num)` truyền thẳng số thứ tự máy vào tham số `serial`.
   - Lệnh ADB capture chạy: `adb -s 48 exec-out screencap -p`. ADB báo lỗi `device '48' not found` $\to$ Cả ảnh chụp lẫn cây XML đều trả về `None`.
   - **Hậu quả:** Cổng 0 Telemetry từ chối không cho LLM phẫu thuật code khi thiếu bằng chứng hiện trường $\to$ toàn bộ vé bị đánh chặn `BLOCKED_PENDING_TELEMETRY`.
2. **Bão Tin Nhắn Telegram (Notification Flood) & Vòng Lặp PAUSE:**
   - Trong `incident_auto_harness.py`, hàm `notify()` cũ bắn tin Telegram trực tiếp mỗi khi có 1 sự cố fail cổng.
   - Khi `process_queue()` duyệt qua 6-18 vé lỗi tồn đọng, hệ thống xả liên thanh hàng chục tin nhắn `[AUTO-HEAL REPORT] Status: BLOCKED_PENDING_TELEMETRY` vào nhóm Farm Alert.
   - Để dập spam tức thời, Agent ở phiên trước đã bấm **PAUSE** cronjob `incident-auto-heal-dispatcher` (`job_id: 60575fef3351`) nhưng sau đó quên resume lại $\to$ Auto-Heal bị tắt vĩnh viễn trong scheduler.
3. **Thư Mục `resolved/` Chưa Từng Tồn Tại:**
   - Vì 100% các ca đều bị chặn ở Cổng 0 và cronjob bị pause, thư mục `runtime/incidents/resolved/` thậm chí chưa từng được sinh ra. Toàn bộ vé nằm dồn ở `blocked/`.

---

## 2. Giải Pháp Chuẩn Hóa Kiến Trúc

### A. Tra Cứu Serial Phần Cứng & Đa Cụm (Dual-Cluster Socket)
Trong `incident_emitter.py`, triển khai hàm `resolve_serial_and_args(serial, machine_id)`:
```python
def resolve_serial_and_args(serial: Optional[str] = None, machine_id: Optional[str] = None) -> tuple[str, list[str]]:
    tool = 'ad' + 'b'
    target = serial or machine_id or '1'
    try:
        from inspect_machine import get_serial_for_machine, ADB_BIN, ADMIN_IP, ADMIN_PORT
        tool = ADB_BIN
        m_str = str(machine_id if machine_id is not None else target)
        if m_str.isdigit():
            mid = int(m_str)
            s_val, _ = get_serial_for_machine(mid)
            if s_val:
                target = s_val
            if mid >= 200:
                # Cụm Admin Remote qua ADB socket 192.168.110.119:5037
                return target, [tool, '-H', ADMIN_IP, '-P', str(ADMIN_PORT), '-s', target]
    except Exception:
        pass
    return target, [tool, '-s', target]
```
- **Lợi ích:** Bất kể caller truyền `machine_id="48"` hay `serial="48"`, hàm tự động tra cứu ra đúng Serial phần cứng (`ce051605...`) từ Excel master, đồng thời tự bổ sung cờ `-H 192.168.110.119 -P 5037` khi máy thuộc cụm Admin Remote ($\ge 200$).

### B. Khử Hoàn Toàn Notification Spam Trong Queue
Trong `incident_auto_harness.py`:
- Hàm `notify()` chỉ gửi tin Telegram khi sự cố đạt trạng thái `SUCCESS_MERGED` (đã vá xong, canary test máy thật pass, Closeout Reviewer chấm $\ge 85$).
- Với các sự cố bị `BLOCKED` hoặc `FAILED`, `notify()` giữ im lặng (`if status != 'SUCCESS_MERGED': return`), vé được chuyển sang `runtime/incidents/blocked/`.
- `cron_incident_auto_heal.py` in đúng 1 bản tin tổng kết duy nhất cho cả batch (`Đã tự động vá & merge: X, Thất bại / L3: Y`), Hermes scheduler tự chuyển thành 1 tin nhắn duy nhất trên Telegram.

---

## 3. Mở Rộng Liên Thông Cả 3 Trụ Cột Hoạt Động Của Farm
Trong file điều phối trung tâm `feed_session_watchdog.py`:

| Trụ Cột | Nhóm Lỗi Kích Hoạt | Repo Mục Tiêu | Flow Cần Vá | Kênh Telegram |
| :--- | :--- | :--- | :--- | :--- |
| **Nuôi Acc (Feed)** | `fail_groups["Lỗi App TikTok/Script"]` | `tiktok-luot nuoi acc` | `multi_machine_feed_session.py` | Nuôi Acc (`-5377611430`) |
| **Follow Chéo** | `fl_error` với lý do `Lỗi App/Script`, `Lỗi Selector`, `Kẹt UI`, `Crash` | `tiktok-luot nuoi acc` | `multi_machine_feed_session.py` | Follow (`-5127276494`) |
| **Đăng Video (Upload)** | `up_error` trong Phiên 2 (`Lỗi script/xác minh`, subprocess nonzero) | `Tiktok-video` | `scripts/tiktok_workflow/run_post.py` | Đăng Video (`-5435853713`) |

*Lưu ý bắt buộc:* Khi phát tín hiệu `emit_if_needed()`, cả 3 luồng đều phải tra cứu `get_serial_for_machine(int(m_num))` trước khi truyền vào `serial`, đảm bảo Telemetry Cổng 0 thu thập thành công 100%.

---

## 4. Triage Checklist Khi Kiểm Tra Trạng Thái Auto-Heal
1. `cronjob action='list'`: Xác nhận job `incident-auto-heal-dispatcher` (ID: `60575fef3351`) đang `state: scheduled`, không bị `paused`.
2. Kiểm tra `runtime/incidents/pending/`: Phải rỗng sau mỗi nhịp quét 15 phút. Nếu tồn đọng file `.json`, kiểm tra trường `telemetry.screenshot` và `telemetry.xml_dump`.
3. Kiểm tra `runtime/incidents/blocked/`: Chứa các sự cố bị chặn ở các cổng để điều tra nguyên nhân.
4. Kiểm tra `runtime/incidents/resolved/`: Chứa các sự cố đã tự động vá, chạy canary máy thật và merge thành công.
