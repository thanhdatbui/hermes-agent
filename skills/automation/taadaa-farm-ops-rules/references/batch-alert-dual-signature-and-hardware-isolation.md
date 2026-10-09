# Bóc Tách Dual Signature Khi Gặp Batch Alert Farm & Protocol Điều Tra Hiện Trường

Đúc kết bài học từ ca xử lý Batch Alert lỗi hệ thống 80 máy (11/09/2026).

---

## 1. Bản Chất Của "Số Cụm Lỗi Hệ Thống: N"
- Khi một batch chạy trên farm (ví dụ 80 máy), hệ thống gom lỗi cuối batch (*End-of-Batch Aggregation*) gom các máy lỗi theo `error_signature`.
- Một lỗi được coi là **Cụm lỗi hệ thống (Fleet-wide Pattern)** khi và chỉ khi thỏa mãn **Ngưỡng kép (Dual Threshold)**:
  1. Tỷ lệ máy dính lỗi trên toàn batch $\ge 10 - 15\%$ (ví dụ: $10/80 = 12.5\%$).
  2. Số lượng máy dính lỗi $\ge 3$ máy.
- Các máy lỗi dưới ngưỡng hoặc lỗi rải rác mỗi máy một kiểu được coi là lỗi hao hụt tự nhiên (Transient Errors) và tự động bị **Silent Skip** để chống Alert Fatigue.

---

## 2. Quy Trình Phân Tích Dual Signature (O(1) Inspection)
Khi nhận Batch Alert chứa 2 cụm lỗi song song:

### Cụm Lỗi 1: Phần mềm / App UI (`script-blocker:...`)
- **Ví dụ:** `script-blocker:profile username still mismatched after switch`
- **Các bước inspect nhanh O(1):**
  1. Dùng serial máy đại diện (hoặc tra nhanh từ `taikhoan_run_safe.xlsx` tại `D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx`).
  2. Chụp screencap hiện trường qua ADB:
     `adb -s <serial> exec-out screencap -p > /path/to/screen.png`
  3. Dùng tool OCR hoặc dump UI XML (`uiautomator dump` hoặc ATX port 7912) để đọc text màn hình hiện tại.
  4. **Triệu chứng điển hình:** Màn hình xuất hiện popup mạng nội bộ của TikTok: *"Đã xảy ra lỗi - Thử lại sau"* (nút "Thử lại"), hoặc UI bị kẹt ở nick cũ do lag mạng chưa load kịp profile mới.
  5. **Quy tắc điều phối:** Coordinator KHÔNG tự sửa code trực tiếp trong session chính; BẮT BUỘC dispatch worker subagent qua `delegate_task` để thực hiện patch và unit test trong context cô lập.

### Cụm Lỗi 2: Phần cứng / Mạng vật lý (`proxy-vpn:... Wi-Fi not connected`)
- **Ví dụ:** `dumpsys connectivity: Wi-Fi not connected`
- **Các bước inspect nhanh O(1):**
  1. Lấy danh sách máy dính lỗi (ví dụ: M38, M61-M74).
  2. Chạy nhanh vòng lặp kiểm tra `dumpsys wifi` qua ADB trên danh sách serial:
     `adb -s <serial> shell dumpsys wifi | grep -E "mWifiInfo SSID:|Supplicant state"`
  3. **Đối chiếu:** Nếu toàn bộ cụm máy bị `Supplicant state: UNINITIALIZED` hoặc `RSSI: -127`, trong khi các cụm máy khác (ví dụ M1-M10) vẫn online bình thường $\rightarrow$ Khẳng định **100% là sự cố Access Point (AP) / router Wi-Fi vật lý** cấp phát cho dãy máy đó bị mất nguồn, tuột dây LAN hoặc treo DHCP.
  4. **Hành động:** Báo ngay cho người vận hành / kỹ thuật farm đi kiểm tra phần cứng tại chỗ; KHÔNG can thiệp code vô ích khi phần cứng mất mạng.

---

## 3. Cạm Bẫy File Safe Workbook Trên Môi Trường OneDrive Multi-PC
- **Đường dẫn chuẩn của Kibe PC:**
  `D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx` (hoặc bản clone `D:\Taadaa\tiktok-luot nuoi acc\data\taikhoan_run_safe.xlsx`).
- **Cạm bẫy:** Tuyệt đối không nhầm sang thư mục `D:\OneDrive\TaadaaData\admin\` (chứa file của máy Admin với định dạng máy `201-280` và dữ liệu có thể bị lệch cột timestamp nếu chưa chạy sync).
