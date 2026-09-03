# Quy tắc bảo mật nhập mật khẩu và chạy script tự động toàn Farm

## 1. CẤM gõ mật khẩu bằng `adb shell input text` thô
- Shell MSYS/Android sẽ tự động diễn giải và nuốt các ký tự đặc biệt (`@`, `!`, `&`, `#`, `$`, `%`, `*`, `(`, `)`, `;`, `|`, `<`, `>`...).
- Hậu quả: Mật khẩu đúng sẽ bị gõ thiếu ký tự -> TikTok báo "Mật khẩu không chính xác" -> Gây chẩn đoán sai bản chất lỗi (như sự cố m76 ngày 25/08).

## 2. BẮT BUỘC dùng cơ chế nhập mật khẩu chuẩn
- Dùng `AdbKeyboard` qua broadcast base64 (`am broadcast -a ADB_INPUT_B64 --es msg <base64>`).
- Hoặc dùng helper nhập chuẩn của repo có escape đầy đủ (`_input_password` trong `live_phase_b_adapter.py` / `flows`).

## 3. TUÂN THỦ SCRIPT CỦA REPO — CẤM TỰ Ý GÕ TẮT BẰNG SHELL
- Khi chạy automation/batch, toàn bộ tương tác trên thiết bị (navigate, login, đổi pass, nhập OTP) phải thực thi qua script/runner chính thống của repo.
- Tuyệt đối không tự ý dùng terminal adb shell gõ mò/can thiệp thô khi gặp màn hình mới/blocker. Mọi thử nghiệm phải viết script kiểm soát có lock và ghi log đầy đủ.
