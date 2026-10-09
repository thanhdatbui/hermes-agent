# Quy tắc Vận hành Wi-Fi & Khắc phục Mạng Farm (Aruba + Android)

Tài liệu này chuẩn hóa toàn bộ quy tắc vận hành, khắc phục lỗi mạng Wi-Fi và các cạm bẫy thực tế phát hiện trên hệ thống Taadaa Phone Farm (cụm Kibe 80 máy + Admin 80 máy, chạy 4 AP Aruba IAP).

---

## 1. Cố định Quy hoạch AP Aruba (Bất Khả Xâm Phạm)
Mỗi AP Aruba IAP được tính toán để gánh tối đa **40 máy** để đảm bảo băng thông và tránh tràn bảng association:
* **Máy 01 – 40:** CỐ ĐỊNH AP `.253` — SSID `kibe 1` (Mật khẩu: `23102025`).
* **Máy 41 – 80:** CỐ ĐỊNH AP `.252` — SSID `kibe 2` (Mật khẩu: `19051995`).
* **Máy 201 – 240:** CỐ ĐỊNH AP `.251` — SSID `admin 1` (Mật khẩu: `19051995`).
* **Máy 241 – 280:** CỐ ĐỊNH AP `.250` — SSID `admin 2` (Mật khẩu: `19051995`).

### 🛑 Các Điều Cấm Tuyệt Đối:
1. **CẤM gán SSID ngoài farm / Fallback bậy:**
   - TUYỆT ĐỐI KHÔNG cho máy nhảy sang các SSID cá nhân (`Dat`, `Dat-1`, `BOX 2`...).
   - Fallback bậy sẽ khiến máy bị cấp IP dải phụ (vd: `192.168.10.x` thay vì `192.168.110.x`), đứt kết nối với Singbox/3proxy trên MikroTik (`192.168.110.2`) và gây rủi ro lộ IP direct FPT.
2. **CẤM tự ý dồn tải sang AP khác:**
   - Khi AP cụm này gặp sự cố hoặc máy mất kết nối, CẤM chuyển máy sang AP cụm khác (vd: dồn máy M1–M40 sang `kibe 2`). Điều này sẽ làm quá tải AP còn lại (>50-60 máy), gây sập Wi-Fi hàng loạt.
   - BẮT BUỘC giữ nguyên hiện trường, báo watchdog và xử lý dứt điểm trên đúng AP phân công.

---

## 2. Các Cạm Bẫy Thực Tế & Cách Xử Lý (Pitfalls & Fixes)

### Pitfall 1: Cắt chuỗi SSID có khoảng trắng khi gọi `adb-join-wifi` qua shell
* **Hiện tượng:** Chạy lệnh `am start -n com.steinwurf.adbjoinwifi/.MainActivity -e ssid 'kibe 1'` thì Android shell cắt chuỗi tại dấu cách, app nhận SSID là `"kibe"`. Máy nhảy sang quét SSID rác không tồn tại, rơi vào vòng lặp `Supplicant state: SCANNING / DISCONNECTED`, mất sạch Wi-Fi toàn dàn.
* **Cách khắc phục:**
  - BẮT BUỘC dùng tham số kiểu string tường minh `--es` và escape dấu ngoặc kép cẩn thận:
    ```bash
    am start -n com.steinwurf.adbjoinwifi/.MainActivity --es ssid "kibe 1" --es password_type WPA --es password "23102025"
    ```

### Pitfall 2: Xung đột Rogue DHCP trên AP Aruba Master
* **Hiện tượng:** Sau khi reload AP slave (`.253`), các máy gửi DHCP Request thì bị AP Master (`.251`) cướp quyền cấp phát IP dải `192.168.10.x` do còn cấu hình cục bộ `ip dhcp kibe_dhcp`. Hậu quả là máy nhận IP dải 10.x, gateway `192.168.10.254`, không thể ping tới router MikroTik `192.168.110.2`.
* **Cách khắc phục:**
  - Kiểm tra và xóa sạch pool DHCP cục bộ trên Master AP:
    ```bash
    conf t
    no ip dhcp kibe_dhcp
    end
    commit apply
    ```
  - Trong code kiểm tra trạng thái wlan0, chỉ coi là online hợp lệ khi IP khớp chính xác dải chuẩn:
    ```python
    re.search(r"inet\s+192\.168\.110\.", out)  # ĐÚNG
    # re.search(r"inet\s+192\.168\.", out)     # SAI: có thể lọt subnet 192.168.10.x
    ```

### Pitfall 3: Cờ `ASSOCIATION_REJECTION` trên Android 8 & Quên mạng triệt để
* **Hiện tượng:** Khi AP Aruba từ chối kết nối (do kẹt session cũ hoặc Client-Match đá), Android 8 gắn cờ nội bộ `NETWORK_SELECTION_DISABLED_ASSOCIATION_REJECTION` và đưa BSSID vào blacklist tạm thời. Dù toggle Wi-Fi vẫn không kết nối lại được.
* **Cách khắc phục:**
  1. Vào menu cài đặt Wi-Fi hệ thống -> Nâng cao -> Quản lý mạng -> Chọn SSID bị kẹt -> Bấm **QUÊN (Forget)** để xóa sạch config và reset cờ blacklist.
  2. Dùng `adb-join-wifi` với `--es ssid` để ép hệ thống tạo lại network config sạch.
  3. Trên Aruba Virtual Controller, nếu client liên tục bị đá, có thể tắt tính năng client-match gây nhiễu:
     ```bash
     conf t
     arm
     no client-match
     end
     commit apply
     ```

### Pitfall 4: Tránh nghẽn USB Bus khi kiểm tra/tác động đồng loạt dàn máy
* **Hiện tượng:** Chạy `ThreadPoolExecutor` với concurrency quá cao (>25-30 workers) gửi lệnh ADB shell dài (`dumpsys wifi`) cùng lúc qua hub USB X99 sẽ gây nghẽn bus EHCI, dẫn tới hàng loạt timeout giả mạo (`ADB_TIMEOUT`) khiến tưởng nhầm máy mất mạng.
* **Cách khắc phục:**
  - Giới hạn concurrency kiểm tra mạng qua USB ở mức an toàn: `max_workers = 6` đến `10`.
  - Stagger hoặc chia batch nhỏ để bảo vệ USB bus controller.
