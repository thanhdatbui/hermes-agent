# Postmortem: Sự Cố Sập Mass-Alert "Profile Username Still Mismatched After Switch" & Cơ Chế Phục Hồi MikroTik / Sing-box

## Hiện tượng & Bối cảnh (2026-09-12)
- **Batch Alert:** Kích hoạt cảnh báo hệ thống trên batch Nuôi Acc / Lướt Feed (`tiktok-luot nuoi acc`).
- **Triệu chứng:**
  - 20/80 máy thất bại (25.0%).
  - Cụm lỗi vượt ngưỡng kép: `script-blocker:profile username still mismatched after switch` trên 9 máy (M34, M36, M37, M72, M73, M77, M78, M79, M80).
  - Tỷ lệ: 45.0% trong số máy lỗi toàn batch.
- **Canary Policy ban đầu:**
  - Chạy `python D:/Taadaa/tools/inspect_machine.py 34`. M34 online ở `LauncherActivity`.

## Bẫy Chẩn Đoán Của Coordinator (Pitfall Cần Khắc Phục)
- **Nhầm Lẫn Tai Hại:**
  - Ban đầu Coordinator probe socket tới `127.0.0.1:20034` (localhost PC Kibe) -> Thấy `CLOSED / DEAD`.
  - Quét dải `127.0.0.1:20001..20080` -> Đều `CLOSED` -> Vội kết luận nhầm: *"Toàn bộ 80 cổng Singbox sập"*.
- **Sự Thật Kiến Trúc:**
  - **Sing-box chạy TRÊN ROUTEROS (MikroTik), KHÔNG CHẠY TRÊN PC KIBE!**
  - IP đích đúng của Sing-box là `192.168.110.2:20001..20080` (được NAT qua `172.17.0.2` trên RouterOS container `veth-singbox`).
  - Khi user nhắc nhở: *"Vào mikrotik (từ repo ai tool) kiểm tra coi"*, Coordinator truy cập vào MikroTik (`192.168.110.2:9090`) qua `mikrotik_manager.py` và phát hiện container Sing-box vẫn đang chạy (`running`), 35/35 PPPoE vẫn sống!

## Nguyên Nhân Gốc Rễ Thực Sự Của Batch Alert (Root Cause)
1. **Lệch Cấu Hình Proxy Trên Thiết Bị S7:**
   - 9 máy bị alert (M34, M36, M37, M72, M73, M77, M78, M79, M80) trước đó đã bị chạy script gán nhầm hoặc sót cấu hình gán trực tiếp vào cổng 3proxy nội bộ:
     - M34 -> `192.168.110.2:10002`
     - M36 -> `192.168.110.2:10004`
     - M37 -> `192.168.110.2:10005`
     - M72 -> `192.168.110.2:10001`
     - M73 -> `192.168.110.2:10002`
     - M77 -> `192.168.110.2:10005`
     - M78 -> `192.168.110.2:10006`
     - M79 -> `192.168.110.2:10007`
     - M80 -> `192.168.110.2:10007`
2. **Cổng 10001-10007 Yêu Cầu Basic Auth:**
   - Dải port `10001..10035` trên MikroTik là cổng proxy PPPoE có xác thực (`admin@1:admin@1`).
   - Android `settings put global http_proxy 192.168.110.2:1000x` **không hỗ trợ truyền user:pass**.
   - Thiết bị nhận mã lỗi `HTTP 407 Proxy Authentication Required` -> Mất toàn bộ kết nối mạng Internet.
3. **Cơ Chế Phát Sinh Lỗi Mismatched:**
   - Khi TikTok mất mạng do HTTP 407, bot thực hiện tap switch account.
   - UI TikTok không kết nối được server để fetch hồ sơ/token tài khoản mới, âm thầm giữ nguyên tài khoản cũ.
   - Script feed session so sánh username mong đợi vs username trên UI -> Thấy không đổi -> Bắn lỗi `profile username still mismatched after switch`.
   - Đây là **hệ quả phụ (symptom)** của việc mất mạng proxy, không phải do ADB click trượt hay do code flow switch acc.

## Quy Trình Xử Lý Chuẩn (Recovery Procedure)
1. **Kiểm tra trạng thái MikroTik RouterOS:**
   ```bash
   python D:/Taadaa/AI-Tools/scripts/mikrotik_manager.py --check
   ```
   - Xác nhận RouterOS version, uptime, 35 PPPoE running và container `3proxy`, `api`, `veth-singbox` đều ở trạng thái `running`.
2. **Kiểm tra dải cổng Sing-box trên MikroTik (`192.168.110.2:200xx`):**
   ```python
   import urllib.request
   proxy = urllib.request.ProxyHandler({'http': 'http://192.168.110.2:20034'})
   opener = urllib.request.build_opener(proxy)
   print(opener.open('http://api.ipify.org', timeout=5).read().decode())
   ```
3. **Gán chuẩn lại Proxy toàn farm bằng script chuẩn:**
   - CẤM gán thủ công port 100xx.
   - Chạy script chuẩn hóa:
     ```bash
     python D:/Taadaa/AI-Tools/scripts/set_proxy_farm_adb.py
     ```
     Script sẽ tự động:
     - Map từng máy $N$ với cổng Sing-box tương ứng: `192.168.110.2:20000+N` (ví dụ M34 -> 20034).
     - Tắt Captive Portal: `settings put global captive_portal_mode 0` và `captive_portal_detection_enabled 0`.
4. **Kiểm chứng Canary (Ví dụ M34):**
   - Đọc proxy trên máy: `adb -s ce031603b3158b0b02 shell settings get global http_proxy` -> Trả về `192.168.110.2:20034`.
   - Chụp màn hình hiện trường: `screencap -p /sdcard/canary.png && adb pull /sdcard/canary.png`.
   - Thiết bị có mạng bình thường, sẵn sàng chạy lại batch.
