# Batch Alert 2 Cụm Lỗi: Profile Switcher Mismatch + Wi-Fi Disconnected (11/09/2026)

## 1. Đọc Batch Alert "Số cụm lỗi hệ thống: 2"
- Nghĩa: End-of-Batch Aggregation phát hiện 2 signature cùng vượt ngưỡng kép
  (rate >= 10% toàn batch VÀ count >= 3 máy). Mỗi signature trong case này 10/80 = 12.5%.
- 26 máy lỗi = 20 máy trong 2 cụm + 6 máy lỗi lẻ (Silent Skip, không sửa).
- Hiển thị bắt buộc: header có `Tổng tỷ lệ thất bại toàn batch`, mỗi signature tách
  `Tỷ lệ trên toàn batch` vs `Tỷ lệ trong số máy lỗi` (tránh nhầm 75% vs 100%).

## 2. Cụm script-blocker: profile username still mismatched after switch
- Hiện trường M33 (screencap + OCR tay): TikTok ở profile nick cũ, overlay
  "Đã xảy ra lỗi / Thử lại sau" kèm nút Thử lại (`com.ss.android.ugc.trill:id/dcj`).
- Root cause: tap switcher xong TikTok lag / lỗi mạng nội bộ, profile chưa load nick mới;
  verify ngay lập tức thấy username cũ → fail closed.
- Fix chuẩn (đã commit `tiktok-luot nuoi acc` 1623c41): trong `verify_and_switch_profile`,
  sau `if not verified and selected_account_by_exact_switcher:` kiểm tra xml lower có
  `dcj` / `thử lại` / `đã xảy ra lỗi` → tap fallback (540,1436 trên 1080x1920) + sleep 3s,
  else sleep settle 2s → re-read `_read_profile_identity_with_add_phone_guard` → verify lại
  username/display_name qua `matches_switcher_identity`. Kèm focused test
  `test_profile_switcher_retry.py` (3 passed).
- Pitfall: Case 146 từng nâng `PROFILE_SWITCH_MAX_ATTEMPTS` 2→3 cho nick mới Row 7;
  lỗi lần này khác (màn hình lỗi mạng), không tăng attempts mù mà phải tap retry + settle.

## 3. Cụm proxy-vpn: Wi-Fi not connected (kill switch)
- Chẩn đoán O(1) bằng ADB trực tiếp, không quét đĩa:
  `adb -s <serial> shell dumpsys wifi | grep mWifiInfo`
- Máy rớt mạng: `SSID: <unknown ssid>, Supplicant state: DISCONNECTED/UNINITIALIZED,
  RSSI: -127, score: 0`. Máy khỏe (M1 đối chứng): `SSID: kibe 1, ... COMPLETED, RSSI: -68, score: 56`.
- Cả 10/10 máy cụm này DISCONNECTED → sự cố AP vật lý dải M6x–M7x/M38, không phải code.
  Không can thiệp đồng loạt; nhờ người tại farm kiểm tra nguồn/dây LAN AP + DHCP.
- Đối chứng hạ tầng: MikroTik `mirotik1.taadaa.click:10001..10035` timed out toàn dải
  (nghi đường mạng), trong khi MobiProxy `test.taadaa.click:5101..` vẫn OPEN.

## 4. Workbook truth & bẫy nhầm số máy
- Truth cho feed runner: `D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx` (May 1–80,
  serial thật ở cột Device ID). File `admin/taikhoan_run_safe.xlsx` là mapping May 201–280
  (M33 ↔ 233) và đang hỏng cột serial (403 dòng bị timestamp `2026-09-07...` thay serial).
- Luôn đối chiếu serial qua file kibe trước khi kết luận máy offline; `adb devices | grep <serial>`.
- `inspect_machine.py` hiện chỉ là stub in `adb devices` — giá trị duy nhất là xác nhận
  ADB daemon sống; hiện trường thật phải lấy bằng `dumpsys window`, `screencap`, `dumpsys wifi`.
