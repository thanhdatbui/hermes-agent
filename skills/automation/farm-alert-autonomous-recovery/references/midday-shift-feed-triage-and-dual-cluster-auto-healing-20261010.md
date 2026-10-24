# Midday Shift Feed Triage & Dual-Cluster Auto-Healing (2026-10-10)

## 1. Ngữ cảnh & Dấu hiệu Nhận biết
Khi nhận báo cáo watchdog ca nuôi TikTok định kỳ (ví dụ `[TIKTOK NUÔI ACC] Ca 2 - Phiên 1/2 (Chiều) hoàn tất (Row 4)`), tỉ lệ lỗi ban đầu có thể vượt ngưỡng cảnh báo (ví dụ Kibe 20 fail / Admin 28 fail).
CẤM quét đĩa diện rộng (`grep -rn`, `os.walk`, `search_files`).

## 2. Quy trình Triage O(1) Chuẩn hóa
1. **Định vị run manifest chính xác:**
   - Kibe: `D:\Taadaa\runtime\kibe\live\<YYYY-MM-DD>\row-<ROW>-<HHMMSS>\<TIMESTAMP>\run_manifest.json`
   - Admin: `D:\Taadaa\runtime\admin\live\<YYYY-MM-DD>\row-<ROW>-<HHMMSS>\<TIMESTAMP>\run_manifest.json`
2. **Trích xuất phân loại taxonomy nhanh qua Python một dòng:**
   - Đọc `multi_machine_summary` trong `run_manifest.json` để bóc tách `final_status` và `stop_reason`.
   - Phân loại vào 4 nhóm:
     * **Mất kết nối ADB/USB:** `device not found`, `device offline`, `unauthorized`.
     * **Mất kết nối Wi-Fi (AP):** `Wi-Fi not connected`, `association_rejection`, `no-carrier`.
     * **Nghẽn Proxy MikroTik:** `dial tcp 192.168.110.2:<PORT>: connect: network is unreachable`, `i/o timeout`.
     * **Lỗi TikTok App / Script:** `startup ad/splash`, `unexpected popup`, `feed not confirmed`, `login/account screen`, `prepare-tiktok failed to focus`, `ATX_SESSION_UNAVAILABLE`.

## 3. T0 Autonomous Multi-Healer Execution
Trước khi kết luận hay báo cáo, Coordinator chủ động kích hoạt các công cụ auto-heal có sẵn để cứu máy ngay tại hiện trường:
1. **Hồi phục Wi-Fi:**
   Chạy `python C:/Users/Kibe/AppData/Local/hermes/scripts/farm_wifi_auto_healer.py` (timeout=60s).
   - Cơ chế: Cấp 1 Radio toggle (`svc wifi disable` -> `enable`), Cấp 2 Ép re-join đúng SSID (`kibe 1` M1-40, `kibe 2` M41-80, `admin 1` M201-240, `admin 2` M241-280) qua `adbjoinwifi`.
   - Minh chứng thực tế: Cứu ngay 4 máy M7 (force-join kibe 1), M210 (force-join admin 1), M217 & M264 (radio-toggle).
2. **Hồi phục ADB Transport Hang:**
   Chạy `python C:/Users/Kibe/AppData/Local/hermes/scripts/farm_adb_transport_auto_healer.py` (timeout=60s).
   - Giải phóng socket USB bị kẹt, phục hồi máy bị hung.
3. **Kiểm tra Proxy Egress Transient:**
   Dùng `curl -x http://192.168.110.2:<PORT> --connect-timeout 5 http://ifconfig.me/ip`.
   - Xác nhận cổng đã hồi phục sau nhịp quay PPPoE của router, phân loại đúng là lỗi Transient không cần can thiệp cấu hình.
4. **Đối soát Phiên cuốn chiếu tiếp theo (Phiên 2/2):**
   Kiểm tra run directory của phiên 2 (`row-X-140015`) để xác nhận delta phục hồi thực tế (+10 máy Kibe phục hồi lên 70/80 pass).
