---

name: android-device-automation

description: Patterns for automating Android devices — VPN preflight, TikTok login flows, UI popup handling, AdbKeyboard input, and reconcile workflows across consumer repos.

---
# Android Device Automation

References:
- Chi tiết toàn bộ quy trình và phân tích chuyên sâu: xem các tài liệu trong thư mục `references/` của skill.

## 🛑 STOP GATE (bắt buộc — chi tiết: skill taadaa-farm-ops-rules)
Máy live + script chạy/lỗi → KHÔNG tự sửa code, KHÔNG tự chạy lại, KHÔNG tự probe/tay khi chưa được user yêu cầu.
Lỗi → screencap → gửi ẢNH THẬT (MEDIA:<path> dòng riêng, KHÔNG bọc markdown, KHÔNG gửi đường dẫn text) → DỪng chờ user hướng dẫn.
User hướng dẫn bước nào → encode bước đó vào script + test → mới chạy lại. Nghi ngờ → HỎI.

General patterns for automating Android devices (Samsung SM-G930 series) in consumer

repos that depend on `automation-core`. Covers TikTok login, account inventory,

VPN/proxy preflight, popup dismissal, and the reconcile workflow.



## VPN / Proxy Preflight (MANDATORY)



Before ANY device interaction after a reboot, the VPN must be connected. The

workbook `PROXYgandienthoai.xlsx` maps serials to proxy requirements.



```python

from automation_core.preflight import require_android_vpn, serial_is_mapped_in_workbook

from automation_core.adb import AdbClient



adb = AdbClient(adb_path, serial, default_timeout=20)

require_android_vpn(

    adb,

    required=serial_is_mapped_in_workbook(

        proxy_mapping_path, serial,

        serial_headers=("phoneId", "deviceId", "serial"),

    ),

)

```



This check MUST run:

- After acquiring device lock, before any device action

- In the `verify_post_reboot` callback of `reboot_and_restore`



If the proxy watcher (`gan-proxy/scripts/vi_c`) holds a lock, the device is NOT

ready — skip or wait; never force-run without VPN.



### Vichanger (vn.vichanger.app) quirk — refs `references/vichanger-vpn.md`



- Popup "No LSPosed access !!!" khi mở app = NHIỄU, kệ nó (máy VPN OK cũng không

  có LSPosed trong `pm list packages`).

- Blocker thật khi workflow fail `ACQUIRE_LOCKS` / `live VPN verifier failed ...

  tun0 does not exist` = VPN chưa connect; recovery 3-bước UI KHÔNG cứu được.

- "Invalid API Key!!!" = trường API Key trống, key là secret của user → báo

  blocker + hỏi, không tự nhập đại.

- User rule: kệ popup app, mở TikTok chạy upload TRƯỚC, recovery chỉ SAU khi

  workflow báo lỗi thật; không pre-dismiss / tự sửa VPN bằng tay.

- BẪY ORIENTATION: screencap có thể ra 1920x1080 (landscape) khi tưởng portrait

  → mọi `input tap` tọa độ portrait trượt. Đọc `img.size` (PIL) TRƯỚC khi suy

  tọa độ; nếu tap trượt nhiều lần → crop vùng nghi có nút + vision_analyze hỏi

  tọa độ, map ngược về ảnh gốc.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
