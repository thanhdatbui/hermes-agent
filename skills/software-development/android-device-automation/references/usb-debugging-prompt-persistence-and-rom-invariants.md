# USB Debugging Consent Prompt (`UsbDebuggingActivity`) Persistence & ROM Invariants

## 1. Hiện tượng & Câu hỏi thường gặp
- **Triệu chứng:** Điện thoại Samsung Galaxy S7 (Android 8.0 Oreo) trên Farm bất ngờ hiện lại hộp thoại hệ thống:
  `com.android.systemui.usb.UsbDebuggingActivity` ("Cho phép gỡ lỗi USB?" / "Allow USB debugging?").
  Hộp thoại này che khuất màn hình foreground của TikTok/Gmail, hoặc gây timeout ADB khi máy bị đẩy về trạng thái `unauthorized`.
- **Câu hỏi của User:** *"Ủa t nhớ ở kibe t tắt cái này rồi mà sao giờ vẫn hiện?"*, *"Có cách nào can thiệp vào máy để không bị nữa không? T tắt 1 tháng trước giờ bị lại đó"*.

---

## 2. Bản chất kỹ thuật & Nguyên nhân gốc rễ (Root Cause)

### A. Ràng buộc bất biến của Stock ROM (`ro.adb.secure=1`)
* Trên ROM gốc (Stock unrooted ROM), thuộc tính bảo mật `ro.adb.secure=1` được nạp cứng từ `default.prop` trong phân vùng khởi động (`boot ramdisk`) và được xác thực chữ ký số bởi bootloader Samsung.
* **Không có bất kỳ lệnh PC (`adb shell`, `settings put`) hay cấu hình Android UI nào có thể vô hiệu hóa vĩnh viễn cơ chế xác thực RSA này.**

### B. Tại sao đã tick "Luôn cho phép từ máy tính này" mà sau ~30 ngày vẫn bị hỏi lại?
1. **Samsung Knox & Smart Manager Security Revocation:**
   - Trên Android 8.0 của Samsung, trình bảo trì hệ thống định kỳ quét và tự động thu hồi (revoke) các ủy quyền gỡ lỗi USB sau một chu kỳ (~30 ngày không kết nối hoặc sau các đợt tối ưu hóa pin/bộ nhớ hệ thống).
2. **File `/data/misc/adb/adb_keys` bị rác / lỗi Base64:**
   - Qua nhiều tháng hoạt động, file lưu whitelist key RSA trên máy bị phình to (>10 KB) do cắm sang nhiều máy tính/tool khác nhau.
   - Khi xuất hiện một dòng rác hoặc định dạng lỗi (`Invalid base64 key in /data/misc/adb/adb_keys` trong logcat của daemon `adbd`), tiến trình `adbd` dừng nạp file whitelist từ dòng đó trở đi $\rightarrow$ không đọc được key của PC Kibe $\rightarrow$ Android buộc phải bật popup hỏi lại.
3. **Sự kiện USB Bus Reset / Sụt áp cổng USB:**
   - Khi PC bị sleep/standby hoặc hub USB bị chập chờn (sự kiện `USB disconnect` đồng loạt), socket kết nối giữa `adb.exe` (PC) và `adbd` (điện thoại) bị đứt đột ngột. Khi kết nối lại, `adbd` kích hoạt lại handshake `send_auth_request`.

---

## 3. Quy tắc an toàn Farm: CẤM TUYỆT ĐỐI Flash ROM Mod trên máy đang nuôi tài khoản

* **Cơ chế ROM Mod Farm (No-RSA):**
  - Các bản ROM mod farm can thiệp vào kernel để set cứng `ro.adb.secure=0`, `ro.debuggable=1`, và `persist.service.adb.enable=1`. Khi đó Android cho phép mọi máy tính kết nối trực tiếp mà không bao giờ hiện popup.
* **TẠI SAO CẤM:**
  - Để flash kernel/ROM mod, bắt buộc phải **Unlock Bootloader** và cài recovery mod. Quá trình này **BẮT BUỘC XÓA TRẮNG TOÀN BỘ PHÂN VÙNG DỮ LIỆU (Wipe Data / Factory Reset)**.
  - Toàn bộ tài khoản TikTok, Gmail, 2FA, session login và môi trường sạch đã nuôi nhiều tháng trên dàn 80 máy sẽ bị **TIÊU HỦY HOÀN TOÀN 100%**.
  - **Quy tắc:** Chỉ nạp ROM mod khi setup dàn máy mới từ đầu (chưa có tài khoản). Dàn máy đang vận hành thì **TUYỆT ĐỐI KHÔNG ĐƯỢC PHÉP ĐỤNG VÀO ROM**.

---

## 4. Giải pháp chuẩn Production (Tự động hóa phục hồi bằng Code)

Vì không thể tắt ở tầng ROM trên dàn máy đang live, giải pháp duy nhất an toàn và bền vững là **để code tự động nhận diện và dập popup**:

### A. Quy chuẩn bấm duyệt tự động (Checkbox `alwaysUse` -> Tap `OK`)
Cả `automation_core.usb_debugging.recover_usb_debugging_prompt` và `Tiktok_Reg.social_reg_v1.dismiss_usb_debugging_dialog` đều phải tuân thủ chuẩn 2 bước:
1. **BẮT BUỘC TICK VÀO Ô CHECKBOX TRƯỚC:**
   - Node: `com.android.systemui:id/alwaysUse` (class `android.widget.CheckBox`).
   - Text: `"Luôn cho phép từ máy tính này"` / `"Always allow from this computer"`.
   - Tọa độ S7 (1080x1920): `[122,1102][218,1198]` $\rightarrow$ Tap `(round(width * 0.16), round(height * 0.60))` hoặc `(170, 1150)`.
2. **BẤM NÚT OK:**
   - Node: `android:id/button1` (text `"OK"`).
   - Tọa độ S7: `[821,1294][981,1402]` $\rightarrow$ Tap `(round(width * 0.84), round(height * 0.70))` hoặc `(890, 1350)`.
3. **Xác nhận thoát dialog:**
   - Đảm bảo foreground sau khi bấm không còn là `com.android.systemui.usb.UsbDebuggingActivity`.

### B. Chặn Windows ngắt nguồn USB Hub (Chống Flapping)
Để hạn chế USB reset kích hoạt lại popup, chạy script PowerShell nâng quyền trên PC:
```powershell
$target = Get-CimInstance MSPower_DeviceEnable -Namespace root\wmi | Where-Object { $_.InstanceName -like '*USB\ROOT_HUB30*' }
if ($target) {
    $target.Enable = $false
    Set-CimInstance -CimInstance $target
}
```
Và tắt sleep trên máy PC chạy farm:
```cmd
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
```
