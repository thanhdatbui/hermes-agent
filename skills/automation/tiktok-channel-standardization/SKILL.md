---
name: tiktok-channel-standardization
description: "Use when standardizing TikTok profiles (bio, pin, avatar)."
---

# TikTok Channel Standardization (5-in-1 Protocol)

## Trigger & Scope
Áp dụng khi người dùng yêu cầu *"Chuẩn hoá kênh này"* hoặc *"Chuẩn hoá N kênh"* kèm ảnh chụp màn hình Profile TikTok.
Quy trình chuẩn hoá bao gồm trọn gói **5 hạng mục bắt buộc (5-in-1)**:
1. **Avatar (Ảnh đại diện):** Khớp với giới tính/chủ thể video (ví dụ: video creator nam thì avatar bắt buộc là nam; video ẩm thực/nấu nướng thì avatar mang tính chất ẩm thực; cấm để avatar nữ cho kênh video nam).
2. **Tên hiển thị (Display Name):** Họ tên người thật tiếng Việt chuẩn có dấu, cấm viết hoa chữ cái giữa chừng (ví dụ: `Ngọc TRinh` ➔ `Ngọc Trinh`), cấm số/hậu tố rác. **CẤM tự ý tạo cờ `.manual_name_locked`** trừ khi User yêu cầu rõ (để bảo lưu quyền đổi tên sau 7 ngày cooldown của TikTok).
3. **Tiểu sử (Bio):** Bắt buộc 100% tiếng Việt có dấu, nhập qua AdbKeyboard UTF-8 Base64 bằng `do_rename_canonical_runner.py`. Xoá sạch các nhãn rác từ đợt reg nick (`Đang hỗ trợ: WWF-UK`, donation badges).
4. **Ghim video Top (Pin Top):** Chọn video có lượt xem cao nhất ($\ge 1.000$ views) và chạy `pin_top_videos.py` ghim lên ô số 1 trang cá nhân (nhãn đỏ *"Đã ghim"*).
5. **Hashtag & Niche Reconciliation:** Kiểm tra nội dung video thực tế so với cột `Keyword` / `Hashtag` trong `Tik*.xlsx` (tránh bẫy lệch ngách: video đồ ăn nhưng bảng ghi 'Âm nhạc'). Cắm cờ `.manual_avatar_locked` và `.manual_hashtag_locked` tại cả 2 thư mục `F_src` (`D:/video goc/...`) và `F_vid` (`D:/TIKTOK-videonuoinick/...`), đồng thời cập nhật vào `manual_avatar_protected_folders.json` và `manual_hashtag_protected_folders.json`.

---

## 1. Tra Cứu Toạ Độ Farm O(1) Từ Ảnh
- **Bắt buộc:** Từ `@username` trên ảnh, đọc trực tiếp:
  - `D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx` (`Accounts` sheet) ➔ `May`, `Device ID` (Serial ADB).
  - `D:\OneDrive\TaadaaData\kibe\Tik*.xlsx` (`TaiKhoan` sheet) ➔ `F_vid` (Cột D), `F_src` (Cột E), `Keyword/Niche` (Cột F), `Hashtag` (Cột G).
- **CẤM:** Quét đĩa diện rộng (`os.walk`, recursive glob, `find`) để tìm file.

---

## 2. Các Lệnh Thi Công Canonical
- **Cập nhật Bio có dấu:**
  ```bash
  python D:/Taadaa/tools/do_rename_canonical_runner.py --machine <N> --serial <SERIAL> --username <USER> --bio "<BIO_TIẾNG_VIỆT>" --bio-only
  ```
- **Ghim bài Top:**
  ```bash
  python D:/Taadaa/tools/pin_top_videos.py --machine <N> --account <USER> --min-views 1000
  ```
- **Khóa Avatar & Hashtag:**
  ```python
  # Copy file avatar chuẩn vào F_src và F_vid
  # Touch .manual_avatar_locked và .manual_hashtag_locked tại cả F_src và F_vid
  # Ghi nhận folder vào D:/Taadaa/data/manual_avatar_protected_folders.json & manual_hashtag_protected_folders.json
  ```

---

## 3. Nghiệm Thu Thực Tế (Visual Evidence Gate 6)
- Bắt buộc kéo ảnh Profile sau khi cập nhật về máy:
  ```bash
  adb -s <SERIAL> shell screencap -p /sdcard/profile_final.png
  adb -s <SERIAL> pull /sdcard/profile_final.png D:/Taadaa/reports/<FILE>.png
  ```
- Dùng `run_winrt_ocr.py` hoặc Vision soi mắt kiểm tra trước khi gửi:
  - Đúng Username, Tên hiển thị chuẩn.
  - Bio tiếng Việt có dấu đầy đủ, sạch đuôi WWF-UK.
  - Video Top có nhãn đỏ "Đã ghim".
- Đăng ký receipt qua `guard_media_vision_gate.py` trước khi đính kèm `MEDIA:<path>` gửi User.
