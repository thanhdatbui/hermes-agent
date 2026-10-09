# ADB Device Inventory & 3-State Offline/Missing Triage Reference

Tài liệu quy chuẩn phân loại 3 trạng thái kết nối ADB thiết bị farm, quy trình kiểm kê chính xác (chống báo thiếu số máy ảo), và thang leo thang cứu hộ phần mềm vs phần cứng.

---

## 1. Bản Chất 3 Trạng Thái Thiết Bị (Hardware Bus vs Software Protocol)

Khi đối chiếu giữa danh sách quy hoạch chuẩn trong Excel (`PROXYgandienthoai.xlsx` gồm 80 máy Kibe hoặc 80 máy Admin) với kết quả `adb devices`:

| Trạng thái | Hiện diện trong `adb devices` | Hiện diện trong Windows PnP | Bản chất kỹ thuật | Khả năng tương tác |
|---|---|---|---|:---:|
| **1. `device` (ONLINE)** | Có serial kèm nhãn `device` | `Status: OK`, `Problem: CM_PROB_NONE` | Cáp USB tốt, cổng nhận diện, daemon `adbd` trên Android đã bắt tay RSA với PC host thành công. | Hoạt động bình thường |
| **2. `offline` (KẸT GIAO THỨC / TREO HĐH)** | Có serial kèm nhãn `offline` | `Status: OK` hoặc `Unknown (CM_PROB_PHANTOM)` | Cáp USB & phần cứng kết nối vẫn nhận trên Windows bus, nhưng tầng phần mềm bị đứt: tiến trình `adbd` bị crash, kernel Android bị freeze (treo đen màn hình), hoặc máy sập nguồn nhưng chip sạc vẫn nuôi tín hiệu USB thụ động. | Không nhận lệnh `adb shell` |
| **3. `missing` (MẤT KẾT NỐI VẬT LÝ)** | **KHÔNG** xuất hiện trong `adb devices` (mất tích) | `Present: False` hoặc biến mất khỏi PnP | Mất tín hiệu vật lý 100%: tuột cáp USB, lỏng chân cắm Hub, Hub USB mất nguồn phụ, hoặc máy cạn kiệt pin tắt nguồn hoàn toàn. | Mất tích hoàn toàn |

---

## 2. Bẫy Đếm Thiếu Số Máy Ảo Sau Khi Khởi Động ADB Server (Warm-Up Desync)

### Hiện tượng & Cạm bẫy:
- Khi vừa restart daemon ADB (`adb kill-server && adb start-server`), nếu chạy ngay `adb devices` trong vòng 1–2 giây đầu, danh sách có thể chỉ hiện 50–60 máy (ví dụ chỉ thấy 58/80 máy).
- **Nguyên nhân:** PC farm cắm hàng chục thiết bị qua nhiều tầng Hub USB (Industrial USB Hub 20–30 ports). Quá trình enumerate và USB handshake giữa Windows host controller và 80 chip Exynos/Snapdragon cần từ **3 đến 5 giây** để ổn định toàn bộ bus.
- **Kỷ luật:** CẤM TUYỆT ĐỐI vội vã báo cáo số máy thiếu khi chưa đợi bus ổn định. Sau khi restart ADB, bắt buộc sleep tối thiểu 3 giây trước khi đếm máy.

---

## 3. Thang Leo Thang Cứu Hộ Thiết Bị Kẹt `offline` (Rescue Ladder)

### Cấp độ 1: Thử cứu mềm qua lệnh ADB
1. Bắn lệnh reconnect đồng loạt:
   `adb reconnect offline`
2. Bắn lệnh reconnect từng serial:
   `adb -s <serial> reconnect`
3. Nếu không đổi, restart daemon ADB:
   `adb kill-server && adb start-server` (chờ 3–5 giây rồi kiểm tra lại).

### Cấp độ 2: Kiểm tra chẩn đoán tầng mạng LAN & Windows PnP
1. **Kiểm tra liveness mạng LAN nội bộ:**
   - Dùng socket probe kiểm tra cổng `7912` (atx-agent) và cổng `5555` (ADB Wi-Fi) tới IP tĩnh của máy (ví dụ `192.168.10.1xx` hoặc `192.168.110.1xx`).
   - Nếu cả port 7912 và 5555 đều không phản hồi: Hệ điều hành Android bên trong đã chết/treo cứng hoặc máy đã tắt nguồn.
2. **Kiểm tra trạng thái PnP trên Windows:**
   ```powershell
   Get-PnpDevice | Where-Object { $_.InstanceId -match '<serial>' } | Select-Object Status, Problem, InstanceId, FriendlyName
   ```
   - Nếu báo `CM_PROB_PHANTOM`: Windows đang giữ bóng thiết bị cũ, máy thực tế không còn gửi data USB.
3. **⚠️ CẢNH BÁO CẤM:** CẤM TUYỆT ĐỐI dùng lệnh `Disable-PnpDevice` rồi `Enable-PnpDevice` trên Windows đối với thiết bị Samsung USB Composite. Khi tắt PnP qua PowerShell, Windows sẽ giải phóng driver và đẩy thiết bị từ `offline` rớt thẳng thành `missing`, không tự nhận lại được nếu không rút cắm cáp vật lý!

### Cấp độ 3: Can thiệp phần cứng vật lý (User Action)
Khi đã qua Cấp 1 và Cấp 2 mà máy vẫn `offline` hoặc `missing`:
- Máy đã bị treo kernel Android (black screen freeze) hoặc sập nguồn cạn pin.
- **Hành động duy nhất hiệu quả:** Bấm giữ tổ hợp phím cứng `Nguồn + Giảm âm lượng` trong **7 giây** để cưỡng chế khởi động lại Android (Hard reboot). Khi máy lên lại logo Samsung, `adbd` khởi động và máy sẽ tự động nhảy về trạng thái `device` (ONLINE) ngay lập tức.
