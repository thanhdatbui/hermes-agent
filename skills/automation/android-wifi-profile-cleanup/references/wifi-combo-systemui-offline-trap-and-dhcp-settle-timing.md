# SystemUI wifi_combo Offline Trap & S7 DHCP Settle Timing Window

## 1. Hiện Tượng & Triệu Chứng (2026-10-28)
Trong phiên nuôi sáng sớm (06:00 AM), Watchdog báo lỗi hàng loạt "Mất kết nối Wi-Fi (AP)" trên các máy cụm Admin (M216, M229, M268, M277), nhưng đến phiên 08:00 AM các máy này đều tự động pass 100% mà không hề reboot hay đổi AP.

Đối soát log hiện trường phát hiện 2 cơ chế lỗi phần mềm:

---

## 2. Bẫy Bắt Nhầm Status Bar Android Thành Lỗi TikTok (`wifi_combo status`)
### Cơ chế:
- Trên farm Android sử dụng HTTP Proxy toàn cục (`settings put global http_proxy 192.168.110.2:100xx`), các request kiểm tra captive portal của Android OS (`generate_204`) ra ngoài direct internet thường bị trễ hoặc chặn.
- Hệ điều hành Android 8 gắn nhãn cho icon Wi-Fi trên thanh trạng thái hệ thống:
  `<node package="com.android.systemui" resource-id="com.android.systemui:id/wifi_combo" content-desc="Tín hiệu Wi-Fi đủ.,Không có Internet." />`
- Trong `feed_swipe_smoke.py`, hàm `_switcher_offline_reason(popup_xml)` quét chuỗi `khong co internet` trên toàn bộ XML màn hình (bao gồm cả `com.android.systemui`).
- Khi mở Account Switcher để đổi nick, code thấy chuỗi "Không có Internet" trên đỉnh màn hình (thanh pin/sóng) liền kích hoạt early abort với lý do `manual-needed:network-offline: Wi-Fi has no internet connection (wifi_combo status)`, dù danh sách nick TikTok (`yenau9428`,...) đã hiển thị đầy đủ và sẵn sàng để tap!

### Quy tắc khắc phục (Invariants):
1. **Lọc sạch SystemUI trước khi check offline marker**:
   Hàm `_switcher_offline_reason()` bắt buộc phải loại bỏ các node thuộc `com.android.systemui` và `wifi_combo` khỏi XML trước khi kiểm tra marker offline.
2. **Account Element Priority**:
   Trong `verify_and_switch_profile`, chỉ được phép early abort khi:
   `if offline_reason is not None and account_element is None:`
   Nếu target account đã render thành công trên giao diện switcher (`account_element is not None`), runner BẮT BUỘC phải tap chuyển nick trước; cấm huỷ sớm vì cờ báo status bar.
3. **Cơ giới hoá GuardGate**:
   Repo `tiktok-luot nuoi acc` bắt buộc duy trì rule `case_invariant_prohibit_abort_switcher_offline_without_account_check` trong `rules.json` để ngăn chặn việc revert code về dạng `if offline_reason is not None:` đơn lẻ.

---

## 3. Khóa Sàn Thời Gian Chờ DHCP Settle Time Sau Wi-Fi Enable (S7 Aruba Timing)
### Cơ chế:
- Khi 80-160 máy đồng loạt thức dậy từ chế độ `Sleep/Dozing` đầu ca sáng (06:00 AM), chip Broadcom PCIe của Samsung S7 và AP Aruba mất trung bình **5–7 giây** để hoàn tất 4-way handshake WPA2 và nhận cấp phát IP DHCP.
- Trong `vpn_preflight.py`, nếu sau khi chạy `svc wifi enable` hoặc `adbjoinwifi` mà code chỉ chờ `time.sleep(2.0)` rồi gọi `check_android_vpn` ngay, máy sẽ bị kết luận sai `dumpsys connectivity: Wi-Fi not connected` và kích hoạt fail-closed ngắt ca.

### Quy tắc khắc phục (Invariants):
1. **Stage 1 (Wi-Fi Radio Toggle)**: Thời gian chờ sau `svc wifi enable` trước khi thăm dò `check_android_vpn` bắt buộc phải `>= 6.0s`.
2. **Stage 2 (`adbjoinwifi`)**: Thời gian chờ sau khi đóng activity (`input keyevent 3`) trước khi probe lại VPN bắt buộc phải `>= 5.0s`.
3. **Test Assertion**: Unit test `test_vpn_preflight_router.py` bắt buộc có assertion `mock_sleep.assert_any_call(6.0)` để khóa sàn cơ giới hóa thời gian chờ này.

---

## 4. Kỷ Luật Dispatch Worker Khi Sửa Code
- `delegate_task` bị cấm hoàn toàn cho các task sửa code repo (`[HARD GATE #3 - CODE EDIT DISPATCH BLOCKED]`).
- Bắt buộc gọi Gateway Worker chuyên dụng:
  ```bash
  python D:/Taadaa/tools/dispatch_worker.py --workdir "<repo_path>" --file "<target_file>" "<contract_prompt>"
  ```
- Code sửa đổi thêm mới `>= 15 dòng` bắt buộc phải có comment định danh phân bước (`# Bước X: ...`) để thỏa mãn rule `case_invariant_require_step_by_step_structure` của GuardGate.
