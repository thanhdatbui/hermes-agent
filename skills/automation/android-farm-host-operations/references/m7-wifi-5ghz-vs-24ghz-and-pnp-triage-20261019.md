# Chẩn Đoán Lệch Băng Tần 5GHz vs 2.4GHz, Ngưỡng Client Aruba & Kỷ Luật PnP USB (19/10/2026)

## 1. Bản Chất Băng Tần Farm (5.0GHz Only) vs Mạng Vãng Lai (2.4GHz / All)
- **Quy hoạch Farm Aruba:** Toàn bộ SSID farm (`kibe 1`, `kibe 2`, `admin 1`, `admin 2`) được cấu hình khóa cứng **`Band: 5.0`** (chỉ phát 5GHz, tắt hoàn toàn 2.4GHz). Mục đích: triệt tiêu nghẽn airtime và nhiễu sóng khi 40+ máy cùng xem video TikTok.
- **Mạng vãng lai ngoài Farm (`Dat`):** Cấu hình **`Band: all`** (phát đồng thời cả 2.4GHz và 5GHz).
- **Hiện tượng máy bắt được `Dat` nhưng tạch `kibe 1` (Auth / Assoc Reject):**
  * Sóng 2.4GHz có bước sóng dài (12cm), đâm xuyên qua kệ sắt và nắp lưng kim loại cực tốt, công suất phát ngược (Uplink TX) từ điện thoại lên AP mạnh ➔ Hoàn tất 4-way handshake ngay lập tức.
  * Sóng 5GHz có bước sóng ngắn (6cm), rất dễ bị phản xạ, triệt tiêu bởi khung sắt hộp hoặc hở chân tiếp xúc lò xo ăng-ten 5GHz ở góc trên cùng bên trái màn hình Samsung S7 (nhìn từ trước).
  * Khi máy đặt sát góc kệ hoặc nắp lưng hở tiếp xúc 5GHz: RSSI tụt sâu ($\le -70$ dBm, yếu hơn máy bên cạnh tới 15 dBm). Khi AP gửi Message 1 (`wpa2-key1`), điện thoại phát Message 2 (`wpa2-key2`) nhưng tín hiệu TX quá yếu không chạm tới AP, khiến AP retransmit 3 lần rồi hủy session ➔ Android hiểu nhầm là sai mật khẩu (`WPA: 4-Way Handshake failed - pre-shared key may be incorrect`).
- **Cảnh báo an toàn Farm:** CẤM TUYỆT ĐỐI cho máy nhảy sang `Dat` vì sẽ bị cấp IP dải `192.168.10.x` (thay vì dải chuẩn Farm `192.168.110.x`), đứt kết nối Singbox/3proxy (`192.168.110.2:200xx`), dính lỗi `blocked-proxy-vpn` và nguy cơ rò rỉ IP gốc.

## 2. Bản Chất Ngưỡng 40 Máy/AP Trên Hạ Tầng Aruba IAP
- **Khuyến nghị airtime vs Trần cứng kỹ thuật:**
  * Con số 40 máy/AP là **quy chuẩn phân bổ tải airtime khuyến nghị** chia đều 160 máy cho 4 AP để tối ưu hóa hiệu năng lướt video farm.
  * **KHÔNG PHẢI trần cứng chặn kết nối:** Cấu hình thực tế trên Virtual Controller Aruba IAP-325/315 thiết lập `Max Clients Threshold = 64` máy (phần cứng hỗ trợ tối đa 256 associations).
  * CẤM Coordinator ngụy biện coi 40 máy là giới hạn cứng không thể kết nối thêm.

## 3. Kỷ Luật Chẩn Đoán Ngoại Vi: CẤM Phán Bừa Rút Cáp Khi `adb devices` Mất Máy
- **Sai lầm chẩn đoán:** Thấy `adb devices` không còn serial của máy là vội vàng kết luận "người dùng đã rút cáp" hoặc "máy sập nguồn".
- **Quy trình đối soát PnP USB bắt buộc (O(1)):**
  1. Chạy lệnh kiểm tra Windows Device Manager qua PowerShell:
     ```powershell
     Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -like "*<SERIAL>*" } | Select-Object Status, Class, FriendlyName, InstanceId
     ```
  2. **Đánh giá kết quả:**
     - Nếu trả về `SAMSUNG Mobile USB Composite Device` với `Status: OK`: Cáp USB, nguồn VBUS 5V và kết nối phần cứng vẫn cắm chặt 100%.
     - Nguyên nhân mất ADB thực chất là ở tầng ứng dụng/hệ điều hành:
       + Màn hình khóa đang hiện popup hỏi *"Cho phép gỡ lỗi USB?" (Allow USB debugging)* và chưa được bấm tick *"Luôn cho phép" (Always allow)*.
       + Người dùng vừa thao tác tay trên màn hình chuyển chế độ USB sang *"Chỉ sạc" (Charge only)* hoặc *"Truyền tệp" (MTP)* làm tắt interface ADB.
       + Tiến trình daemon `adbd` trên Android bị crash/kill ngầm hoặc treo socket pipe.
- **Hành động:** Hướng dẫn người dùng kiểm tra màn hình điện thoại để bấm "Cho phép gỡ lỗi USB" hoặc kiểm tra chế độ USB, tuyệt đối không phán ẩu người dùng rút dây.

## 4. Chuẩn Hóa Cú Pháp Intent Nạp Wi-Fi `com.steinwurf.adbjoinwifi`
- **Bẫy cắt cụt chuỗi shell:** Khi SSID có khoảng trắng (`"kibe 1"`, `"admin 1"`), cờ `-e ssid "kibe 1"` bị Android shell `/system/bin/sh` tách thành `ssid="kibe"`, dẫn đến lưu sai profile mạng rác.
- **Cú pháp chuẩn:**
  ```bash
  am start -S -n com.steinwurf.adbjoinwifi/.MainActivity --es ssid "<SSID>" --es password_type WPA --es password "<PASSWORD>"
  ```
  * BẮT BUỘC dùng `--es` để ép kiểu String tường minh.
  * Thêm cờ `-S` (force-stop trước khi khởi động Activity) để dọn timer và extras cũ trong memory.
