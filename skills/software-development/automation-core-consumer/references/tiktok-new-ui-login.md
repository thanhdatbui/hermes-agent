# TikTok UI Mới (post-46.x) — Login Navigation

Phiên bản TikTok mới (tháng 7/2026) có giao diện login khác biệt so với phiên bản 46.0.3 mà code gốc được thiết kế.

## Popup Google Sign-In (AssistedSignInActivity)

**Activity:** `com.google.android.gms/.auth.api.credentials.assistedsignin.ui.AssistedSignInActivity`

**Triệu chứng:** Màn hình "Đăng nhập lại vào TikTok bằng Google" với text "Tiếp tục với tên X".

**Xử lý:** `adb shell input keyevent 4` (BACK) — dismiss popup, quay về màn hình đăng nhập chính.

## Màn hình đăng ký/đăng nhập chính (I18nSignUpActivity)

**Activity:** `com.ss.android.ugc.trill/com.ss.android.ugc.aweme.account.login.auth.I18nSignUpActivity`

UI mới có 2 trạng thái:

### Trạng thái 1: Màn hình chọn phương thức (sau khi dismiss Google popup)

```
text="VN"
text="+84"
text="Số điện thoại"           ← clickable, mở dropdown chọn phone/email
text="Đăng nhập"               ← tiêu đề
text="Tạo tài khoản"
```

### Trạng thái 2: Sau khi BACK từ màn hình nhập số điện thoại

```
text="Số điện thoại"
text="Nhập số điện thoại hợp lệ"
text="Đăng nhập"
text="hoặc"
text="Tiếp tục với email/tên người dùng"  ← ĐÂY LÀ SIGNUP, KHÔNG PHẢI LOGIN
text="Tiếp tục với Facebook"
text="Tạo tài khoản"
text="Bạn đã có tài khoản? Đăng nhập"     ← [0,1740][1080,1920] — TAP CÁI NÀY ĐỂ LOGIN
```

**QUAN TRỌNG:** "Tiếp tục với email/tên người dùng" là để **đăng ký** tài khoản mới bằng email. Để **đăng nhập** vào tài khoản đã có, phải tap **"Bạn đã có tài khoản? Đăng nhập"** ở cuối màn hình.

**Quy trình đúng:**
1. Từ màn hình đăng ký → tap "Bạn đã có tài khoản? Đăng nhập"
2. Vào màn hình "Đăng nhập vào TikTok" → tap "Sử dụng số điện thoại/email/tên người dùng"
3. Tap tab "Email/tên người dùng"
4. Nhập username/password

## Màn hình nhập Email/TikTok ID

Sau khi tap "Tiếp tục với email/tên người dùng":

```
text="Email hoặc TikTok ID"    ← EditText, focused=true
text="Đăng nhập"               ← nút submit [72,800][1008,956]
text="Tạo tài khoản"
```

Không còn tab Điện thoại / Email như bản cũ.

## Màn hình nhập Password

```
text="Nhập mật khẩu"
text="Mật khẩu"
text="Quên mật khẩu?"
text="Tiếp tục"                ← [96,1603][984,1759]
```

## Popup Bảo Mật (sau login thành công)

```
text="Hãy cùng kiểm tra bảo mật nhanh nhé"
text="Hoàn thành một số mẹo bảo mật..."
text="Tiếp tục"                ← [48,1718][1032,1872]
```

Có nút Đóng (`content-desc="Đóng"`) ở [936,857][1056,989]. Tap để dismiss.

## Popup Contact Permission

```
text="Cho phép TikTok truy cập vào danh bạ của bạn?"
text="TỪ CHỐI"                 ← [439,1062][675,1206]
text="CHO PHÉP"                 ← [675,1062][951,1206]
```

Tap "TỪ CHỐI".

## Bottom Navigation

Vẫn có 5 tab: Trang chủ, Cửa hàng, Quay, Hộp thư, Hồ sơ. Tab Hồ sơ thường ở [864,1794][1080,1920].

Sau login lần đầu, TikTok có thể vào màn hình Shop thay vì feed. BACK để về feed.

## Consent Popup (sau khi clear data TikTok)

**Triệu chứng:** Full-screen popup với text duy nhất "Đồng ý và tiếp tục" (xuất hiện khi TikTok bị clear data hoặc cài mới).

**Activity:** `UniversalPopupActivity`. Popup này KHÔNG có nút đóng — phải **vuốt lên** (swipe up) để dismiss.

**Xử lý:**
```bash
adb shell input swipe 540 1600 540 400 300
```

**Trong code:** Thêm vào `_start_tiktok_and_wait()` trong vòng lặp chờ startup, sau khi check startup ad splash:
```python
# Dismiss post-install consent popup
try:
    xml_text = navigator.dump_ui()
except Exception:
    xml_text = ""
if "Đồng ý và tiếp tục" in (xml_text or ""):
    navigator.swipe(540, 1600, 540, 400, 300)
    time.sleep(1.0)
    continue
```

## 2FA TOTP từ Workbook

Đọc secret 2FA từ workbook bằng `openpyxl`, generate code bằng `pyotp`:

```python
import openpyxl, pyotp

wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
ws = wb.active
headers = [str(c.value or "").strip().casefold() for c in next(ws.iter_rows(min_row=1, max_row=1))]
# Tìm cột 2FA (case-insensitive): "2fa", "totp", "two factor"
fa2_col = next(i for i, h in enumerate(headers) if h in ("2fa", "totp", "two factor"))
# Tìm row theo machine + ID
for row in ws.iter_rows(min_row=2, values_only=True):
    if row[machine_col] == machine and str(row[id_col]).strip().casefold() == username:
        secret = str(row[fa2_col]).strip()
        break
wb.close()

code = pyotp.TOTP(secret).now()  # 6 digits, ~30s validity
```

**Gửi code qua AdbKeyboard:**
```bash
adb shell am broadcast -a ADB_KEYBOARD_INPUT_TEXT --es text $(echo -n '<code>' | base64)
```

**Nếu code sai:** xóa text cũ → generate code mới → gửi lại (code hết hạn sau ~30s).

## AdbKeyboard Broadcast Timeout (SM-G930W8)

Trên một số thiết bị (đặc biệt SM-G930W8 / heroltebmc), `am broadcast ADB_KEYBOARD_INPUT_TEXT` treo và không trả về kết quả mặc dù text đã được nhập thành công.

**Workaround:** Dùng `adb shell input text` với base64-encoded text (AdbKeyboard decode base64 input):
```bash
# Encode text sang base64 trước
encoded=$(echo -n 'the_password' | base64)
adb shell input text "$encoded"
```

**Hoặc fire-and-forget broadcast** (không đợi kết quả):
```python
subprocess.run([adb, "-s", serial, "shell", "am", "broadcast", "-a", "ADB_KEYBOARD_INPUT_TEXT", "--es", "text", b64], timeout=5)
# Bắt TimeoutExpired, nhưng text vẫn được nhập — verify bằng UI XML dump
```

Luôn verify text đã nhập sau mỗi lần gửi:
```bash
adb shell "uiautomator dump /sdcard/window_dump.xml && cat /sdcard/window_dump.xml" | grep -oP 'text="<expected>"'
```
