# Mass Device Disconnect (Sập Đàn Loạt) — Chẩn Đoán Tầng USB Bus & Nguồn Hub

## 1. Hiện Tượng (Symptoms)
- Farm 80 máy đột ngột sập hàng loạt (ví dụ 70+ máy báo offline/ngắt kết nối cùng lúc), chỉ còn sót lại vài máy (7-8 máy) ở dãy cuối cùng còn hiển thị live screen.
- User nghi ngờ: "Có phải do lệnh cuối chạy nặng làm sập cả lũ không?".
- Lệnh ADB kiểm tra: `adb devices` chỉ nhận đúng các máy còn sống, các máy khác biến mất hoàn toàn khỏi danh sách (không cả hiển thị `offline`).

## 2. Fast O(1) Triage Lệnh Windows PnP
Chạy ngay lệnh PowerShell sau để kiểm tra trạng thái phần cứng USB:
```powershell
powershell.exe -NoProfile -Command '
Get-PnpDevice -PresentOnly | Where-Object { 
    $_.FriendlyName -like "*Descriptor Request Failed*" -or 
    $_.FriendlyName -like "*Port Reset Failed*" 
} | Measure-Object | Select-Object -ExpandProperty Count
'
```

Nếu trả về số lượng lớn (hàng chục đến hàng trăm lỗi `Configuration Descriptor Request Failed` hoặc `Port Reset Failed`):
- **KẾT LUẬN TUYỆT ĐỐI**: Đây là **LỖI PHẦN CỨNG / NGUỒN / CÁP USB BUS**, **KHÔNG PHẢI** do phần mềm, script Python hay lệnh batch chạy nặng.
- Software (ADB, Python, script PowerShell) không thể gây ra lỗi Descriptor Request Failed ở tầng Kernel PnP trên hàng loạt thiết bị cùng lúc.

## 3. Nguyên Nhân Gốc Rễ Phổ Biến
1. **Sụt áp / Mất nguồn bộ Hub (Power Supply Failure)**:
   - Dàn farm 80 máy thường chia thành nhiều bộ hub USB công nghiệp (chip QinHeng CH334/CH335 `VID_1A86&PID_8095` hoặc tương đương) cấp nguồn bởi các bộ nguồn tổ ong 5V/12V riêng biệt.
   - Khi 1 bộ nguồn bị nhảy aptomat, tuột phích cắm hoặc sụt áp do quá tải nhiệt, toàn bộ nhánh máy kết nối vào hub đó sẽ mất điện VBUS/logic, khiến Host Controller không đọc được descriptor (`Configuration Descriptor Request Failed`). Nhánh hub dùng nguồn khác vẫn sống bình thường.
2. **Lỏng / Tuột cáp USB Uplink Host**:
   - Cáp USB cắm từ PC vào bộ Hub trung tâm bị lỏng hoặc cổng USB trên bo mạch chủ bị quá dòng (overcurrent protection) tự ngắt.

## 4. Quy Trình Phản Ứng Chuẩn Cho Coordinator
1. **Trấn an user ngay lập tức**: Khẳng định rõ không phải do lệnh chạy nặng hay script làm sập máy.
2. **Không cố debug phần mềm / cấm restart lặp vô ích**:
   - Cấm viết script probe hoặc cố restart ADB server liên tục khi USB bus đang ngập lỗi Descriptor.
   - Dọn dẹp các tiến trình nền bị kẹt (nếu có `grep`/`find` quét đĩa ăn CPU).
3. **Chỉ định điểm kiểm tra vật lý**:
   - Yêu cầu kiểm tra dây nguồn tổ ong / adapter của các hub bị mất kết nối.
   - Kiểm tra các đầu cắm USB uplink nối từ PC ra cụm hub.
   - Sau khi cắm lại điện/dây, thiết bị sẽ tự động xuất hiện lại trên ADB và app điều khiển.
