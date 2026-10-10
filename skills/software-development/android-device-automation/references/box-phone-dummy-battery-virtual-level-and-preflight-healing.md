# Box Phone Dummy Battery, Virtual Battery Level Drift & Preflight Self-Healing

## 1. Bản chất Phần cứng Box Phone vs Virtual Battery Level trên Android

### A. Hạ tầng Box Phone Mod Pin (Battery Eliminator)
- Trong các box phone farm (20–40 máy/box), cell pin lithium vật lý được tháo bỏ hoàn toàn để chống phù/cháy nổ.
- Nguồn cấp điện là mạch hạ áp DC tổng (buck converter) đưa thẳng điện áp ổn định 4.0V–4.2V vào các chấu tiếp xúc `VBAT` và `GND` trên mainboard.
- **Thực tế:** Không có hiện tượng chai pin hay sụt áp vật lý theo thời gian như điện thoại gắn pin thật.

### B. Hiện tượng "Trôi Pin Ảo" (Virtual Battery Drift)
- Mặc dù điện áp nguồn cấp luôn duy trì 4.1V–4.2V, chip quản lý nguồn (PMIC / Fuel Gauge) và Android Framework (`BatteryManager`) vẫn tích lũy bộ đếm dung lượng tiêu thụ (`charge_counter`).
- Sau nhiều ngày hoạt động hoặc sau các chu kỳ reboot/reconnect ADB, Android OS có thể tính toán sai lệch khiến mức pin hiển thị (`dumpsys battery level`) tụt dần về mức cực thấp (ví dụ: tụt về 2%–5%).

---

## 2. Hệ lụy nghiêm trọng khi Virtual Battery tụt thấp (< 15%)

Khi mức pin ảo tụt xuống dưới 15% trên các máy farm (như Samsung Galaxy S7 / Android 8):
1. **Kích hoạt Chế độ Tiết kiệm pin cực độ (Extreme Power Saving / Doze):**
   - Android tự động ngắt kết nối mạng Wi-Fi nền khi màn hình tắt (`wlan0` bị de-authenticate hoặc unassigned IP).
   - Hệ quả: Lượt chạy tiếp theo bị fail preflight vì không ping được Gateway/Proxy, dẫn đến báo động giả "Lỗi Proxy".
2. **Bóp xung nhịp CPU (CPU Throttling):**
   - Hệ thống hạ xung nhịp CPU tối đa để tiết kiệm điện, làm chậm luồng xử lý mạng Cronet/TTNet của TikTok, gây lag hoặc timeout tải video.
3. **System Battery Warning Popup:**
   - Android ném dialog hệ thống *"Pin yếu, vui lòng kết nối bộ sạc"* lên foreground.
   - Dialog này cướp `mCurrentFocus` từ ứng dụng mục tiêu (TikTok, Gmail), làm sai lệch tọa độ bấm và khiến uiautomator/OCR đọc nhầm UI.

---

## 3. Cạm bẫy "Random Mức Pin" (Anti-Fraud Vector trên TikTok/Google)

Tuyệt đối **KHÔNG** dùng script random mức pin ngẫu nhiên (`random.randint(50, 90)`) trước mỗi ca nuôi:
- **Cơ chế Telemetry của TikTok AppLog SDK:** App liên tục gửi sự kiện chứa `battery_level`, `is_charging`, `battery_plugged`, `uptimeMillis`, và điện áp `voltage`.
- **Bẫy Anomaly Detection:** Nếu máy cắm nguồn liên tục mà mỗi ca chạy (cách nhau 2 tiếng) mức pin lại **nhảy cóc giật lùi phi vật lý** (ví dụ: Ca 1 pin 35% ➔ Ca 2 pin 88% ➔ Ca 3 pin 42%):
  - Thuật toán Anti-Fraud sẽ định danh ngay đây là thiết bị giả lập hoặc bị can thiệp bằng phần mềm/ADB hook.
- **Tiêu chuẩn chuẩn hóa cho Box Phone:**
  - Hàng trăm triệu người dùng thật có thói quen vừa cắm sạc vừa lướt video; việc duy trì mức pin ổn định **80%–90%** và trạng thái **Charging (`status: 2`, `USB powered: true`)** là hoàn toàn tự nhiên và an toàn 100%.

---

## 4. Giải pháp: Preflight Self-Healing Tự Bù Pin (`ensure_safe_battery_level`)

Tích hợp bước tự phục hồi pin vào đầu luồng `vpn_preflight.py` trước khi mở app mục tiêu:

```python
import re
import logging
from typing import Any

logger = logging.getLogger(__name__)

def ensure_safe_battery_level(
    adb: Any,
    serial: str,
    min_level: int = 20,
    target_level: int = 85,
) -> int | None:
    """Ensure battery level is safe and emit auditable preflight telemetry.
    
    If level < min_level (e.g. 20%), elevate to target_level (85%) and status 2 (Charging).
    If level >= min_level, leave untouched to preserve natural state.
    """
    clean_serial = str(serial or "").strip() or "unknown"
    try:
        b_res = adb.shell(["dumpsys", "battery"], timeout=3.0, check=False)
        out = str(getattr(b_res, "stdout", "") or "")
        m = re.search(r"level:\s*(\d+)", out)
        if not m:
            logger.warning("[BATTERY_PREFLIGHT] serial=%s kept=unknown reason=no_level", clean_serial)
            return None
        cur_lvl = int(m.group(1))
        if cur_lvl < min_level:
            adb.shell(["dumpsys", "battery", "set", "level", str(target_level)], timeout=3.0, check=False)
            adb.shell(["dumpsys", "battery", "set", "status", "2"], timeout=3.0, check=False)
            logger.info(
                "[BATTERY_PREFLIGHT] serial=%s elevated=%s from=%s",
                clean_serial, target_level, cur_lvl,
            )
            return target_level
        logger.info("[BATTERY_PREFLIGHT] serial=%s kept=%s", clean_serial, cur_lvl)
        return cur_lvl
    except Exception as exc:
        logger.warning(
            "[BATTERY_PREFLIGHT] serial=%s kept=unknown error_type=%s",
            clean_serial, type(exc).__name__,
        )
        return None
```

---

## 5. Kinh nghiệm Điều phối Watchdog: Ưu tiên `stop_reason` hơn `final_status`

Khi thiết kế hoặc debug script watchdog (`feed_session_watchdog.py`):
- **Cạm bẫy:** Khi preflight fail, wrapper tổng thường gán nhãn thô `final_status: blocked-proxy-vpn` để fail-closed.
- **Hệ quả:** Nếu parser watchdog chỉ đọc `final_status`, mọi lỗi rớt cáp USB (`device is offline or ADB/USB disconnected`) hoặc lỗi AP Wi-Fi (`Wi-Fi not connected`) đều bị gom nhầm thành "Lỗi cấu hình Proxy", khiến đội vận hành điều tra sai hướng sang MikroTik/Singbox.
- **Quy tắc vàng:** Luôn parse `summary.txt` thành dict và ưu tiên lấy `r_map.get("stop_reason")` trước `final_status` để phân loại chính xác nguyên nhân gốc rễ.
