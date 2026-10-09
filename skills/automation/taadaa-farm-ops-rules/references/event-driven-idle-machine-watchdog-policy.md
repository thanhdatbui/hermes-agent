# Quy chuẩn Event-Driven Watchdog: Khóa Chặt Zero Hardcoded Time & Xử Lý Nick Ký Sinh Khi Máy Rảnh

## Bối cảnh sự cố & Động lực quy chuẩn
Trong phiên vận hành ngày 15-16/09/2026, Coordinator liên tục mắc sai lầm nghiêm trọng:
1. Tự đặt lịch cron theo khung giờ cố định (`13:00`, `21:00`, `23:30`) hoặc đoán mò thời điểm máy rảnh để vào xử lý nick ký sinh/can thiệp máy.
2. Hệ quả: Bị ảo giác về mốc thời gian thực, đụng độ với các ca chạy chính của Farm (Ca trưa 14h, chuỗi Reg Gmail/Add 2FA 14h-18h, Ca tối 18h-20h), suýt làm gián đoạn và crash chéo tiến trình của Farm.
3. Người dùng yêu cầu tham vấn Claude CLI để chuẩn hóa và khóa chặt quy tắc bất di bất dịch cho mọi tác vụ dạng "canh máy rảnh thì làm".

---

## 5 Invariant Rules do Claude CLI tư vấn & chuẩn hóa

### RULE #0: ZERO HARDCODED TIME (Tuyệt đối cấm hẹn giờ cố định)
- Coordinator **TUYỆT ĐỐI CẤM** tự đặt bất kỳ khung giờ cố định nào (ví dụ: `13:00`, `20:45`, `23:30`, `schedule="30 23 * * *"`) cho các tác vụ can thiệp thiết bị Farm (như logout nick ký sinh, sửa lỗi app, can thiệp ADB).
- Mọi hành vi dùng mốc giờ cứng hay suy đoán "chắc giờ này máy rảnh" đều là vi phạm kiến trúc tối cao.

### RULE #1: NO TOUCH WITHOUT PER-DEVICE LOCK (Cấm đụng máy khi chưa có lock)
- Mọi tác vụ can thiệp trên thiết bị (ví dụ Máy N) **BẮT BUỘC PHẢI CHECK LOCK RIÊNG CỦA MÁY ĐÓ**:
  - `machine_N.lock.json`
  - `serial_<serial>.lock.json`
- Khi máy đang dính lock của bất kỳ batch nào (feed session, 2FA, reg gmail) -> **CẤM TUYỆT ĐỐI ĐỤNG VÀO MÁY**.

### RULE #2: SOURCE OF TRUTH LÀ LIVE DEVICE STATE (Chỉ tin dữ liệu live)
- Coordinator không được phép "suy luận", "nhớ lại" hay "nghĩ là máy đã xong" dựa trên context cũ.
- Trạng thái rảnh **phải được chứng minh bằng việc file lock biến mất thực tế trong thư mục `device-locks`**.

### RULE #3: SESSION EXCLUSIVITY (Bảo vệ ca chính)
- Các ca chạy chính (`FEED_SESSION`, `2FA_SESSION`, `REG_GMAIL`, `REBOOT`) là **BẤT KHẢ XÂM PHẠM**.
- Tuyệt đối không được chen ngang hoặc ép chạy song song khi máy đang thực thi ca chính.

### RULE #4: EVENT-DRIVEN WATCHDOG ONLY (Cơ chế Watchdog chuẩn)
- Khi user yêu cầu "canh máy rảnh thì làm", Coordinator BẮT BUỘC:
  1. Tạo một script Watchdog chạy polling định kỳ ngắn (mỗi **1-2 phút**).
  2. Mỗi tick kiểm tra đúng file lock của máy mục tiêu:
     - Nếu còn lock -> Im lặng (silent exit 0), tiếp tục chờ.
     - Nếu lock đã được giải phóng (máy rảnh về HOME) -> **KÍCH HOẠT VÀO XỬ LÝ NGAY TỨC THÌ**.
  3. Xử lý xong -> Ghi nhận trạng thái hoàn thành vào state file, gửi báo cáo kèm `MEDIA:<path_screencap>` và **TỰ ĐỘNG GỠ BỎ CRON WATCHDOG** để không chạy ngầm spam tài nguyên.
  4. Script watchdog phải có TTL tối đa (ví dụ 4h). Nếu quá TTL mà máy vẫn bận thì escalate alert cho user, cấm tự ý retry ngầm vô tận.

---

## Mẫu kịch bản chuẩn cho Event-Driven Machine Idle Watchdog

```python
#!/usr/bin/env python3
"""
watchdog_target_machine_idle.py
Cơ chế Event-Driven Watchdog: Thăm dò lock máy mục tiêu mỗi 1-2 phút.
Máy vừa rảnh là vào can thiệp ngay lập tức, làm xong tự tắt.
"""
import sys
import json
import time
import subprocess
from pathlib import Path

LOCKS_DIR = Path.home() / ".codex" / "device-locks"
STATE_FILE = Path(r"D:\Taadaa\runtime\kibe\cron-state\target_action_state.json")
TARGET_MACHINE_ID = 69
TARGET_SERIAL = "ce12160c386c913101"

def is_machine_busy(m_id: int, serial: str) -> bool:
    if not LOCKS_DIR.exists():
        return False
    m_lock = LOCKS_DIR / f"machine_{m_id}.lock.json"
    s_lock = LOCKS_DIR / f"serial_{serial}.lock.json"
    return m_lock.exists() or s_lock.exists()

def execute_intervention():
    # Thực thi hành động cụ thể (ví dụ logout nick ký sinh, reset app, test)
    print(f"[watchdog] May {TARGET_MACHINE_ID} da ranh -> Thuc thi can thiep...")
    # ... code thao tác UI / ADB an toàn ...
    return True

def main():
    state = {}
    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            state = {}

    if state.get(f"m{TARGET_MACHINE_ID}") == "DONE":
        return 0

    if is_machine_busy(TARGET_MACHINE_ID, TARGET_SERIAL):
        # Máy đang bận ca chính -> im lặng chờ đợt poll tiếp theo
        return 0

    # Máy rảnh hoàn toàn -> Vào việc ngay
    success = execute_intervention()
    if success:
        state[f"m{TARGET_MACHINE_ID}"] = "DONE"
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
        print(f"[watchdog] Hoan tat xu ly tren May {TARGET_MACHINE_ID}.")

    return 0

if __name__ == "__main__":
    main()
```
