# Vòng Đời Chuẩn Hoá 3 Món (Avatar - Hashtag - Pin) & Kích Hoạt Nạp Máy Thật (2026-10-16)

## 1. Bẫy "Tưởng Xong Khi Mới Chuẩn Bị File" (Premature Done Trap)
- **Hiện tượng**: User gửi ảnh profile TikTok 2 kênh yêu cầu *"Chuẩn hoá 2 kênh này"*. Agent thực hiện trích xuất frame sạch, crop 512x512 có headroom, khóa marker `.manual_avatar_locked`, cập nhật `Tik<N>.xlsx`, rồi vội vã báo *"Đã hoàn thành chuẩn hoá 3 món"*. User phản hồi ngay: *"Xong chưa"*.
- **Nguyên nhân gốc rễ**: 
  - Agent nhầm lẫn giữa **giai đoạn chuẩn bị dữ liệu (Data Staging)** và **giai đoạn triển khai hoàn tất (Deployment Done)**.
  - Trên điện thoại thật, tài khoản TikTok vẫn đang giữ avatar cũ (bị dính chữ, lệch niche). Người dùng kiểm tra trực tiếp kênh thấy chưa đổi gì nên đánh giá agent chưa làm xong việc.
- **Quy tắc bắt buộc**:
  - Chuẩn hoá kênh CHỈ HOÀN TẤT khi avatar mới đã được tải thành công lên tài khoản TikTok trên máy thật và có ảnh chụp màn hình profile đối soát sau cùng.
  - Phân tách rõ 2 trạng thái trong báo cáo:
    1. `STAGING_COMPLETED`: File ảnh 512x512 sạch, Niche/Hashtag Excel đã chuẩn hoá, marker khóa đã tạo.
    2. `DEVICE_UPLOAD_IN_PROGRESS` / `DEVICE_UPLOAD_VERIFIED`: Đang nạp hoặc đã nạp thành công lên máy thật qua runner.

## 2. Kích Hoạt Nạp Avatar Lên Máy Thật (Device Push Protocol)
- **Lệnh điều phối chuẩn O(1)**:
  - Sử dụng launcher độc lập:
    ```bash
    python D:/Taadaa/tools/run_avatar_batch_3accs.py --tik <Slot> --machine <M>
    ```
  - Hoặc gọi trực tiếp qua PowerShell:
    ```powershell
    echo RUN | powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Taadaa\Tiktok-video\run_tiktok_upload_avatar.ps1 -Tik <Slot> -MaxParallel 1 -HostConfigPath D:\Taadaa\machine-config\kibe.yaml -ForceAvatarMachineList "<M>"
    ```
- **Kỷ luật chạy ngầm chống Timeout & Guard Check**:
  - Quá trình nạp avatar trên máy thật (wake device, mở TikTok, vào hồ sơ, sửa ảnh, căn khung, lưu) kéo dài từ 60s – 180s.
  - Lệnh terminal foreground có timeout > 60s sẽ bị guard chặn cứng (`GUARD_FOREGROUND_TIMEOUT_EXCEEDED`).
  - **BẮT BUỘC**: Dùng `terminal(background=True, notify_on_complete=True, timeout=360)` để chạy nền, tuân thủ Invariant CẤM POLLING TIẾN TRÌNH NỀN, để harness tự đánh thức khi runner hoàn tất.

## 3. Cạm Bẫy Cột Avatar Excel `OK` vs `FORCE_UPLOAD`
- Nếu gán `Avatar = 'OK'` trong `Tik<N>.xlsx` ngay từ khâu chuẩn bị file, script `resolve_avatar_pending_machines.py` sẽ tự động loại bỏ máy này khỏi danh sách cần up.
- Nếu watchdog hoặc batch launcher chạy mà không truyền tham số `-ForceAvatarMachineList`, máy sẽ bị bỏ qua vĩnh viễn.
- **Quy tắc**:
  - Trong lúc chuẩn bị: Đặt `Avatar = 'FORCE_UPLOAD'` (hoặc `PENDING`).
  - CHỈ chuyển `Avatar = 'OK'` sau khi runner trả về `effectiveExitCode == 0` và xác nhận `FORCED_REPLACED_VERIFIED`.

## 4. Kỷ Luật Guard Của Coordinator Trong Phiên Vận Hành
- `python -c` chỉ được phép dùng cho các thao tác read-only kiểm chứng. Mọi lệnh có ghi file, xóa file, hoặc spawn subprocess qua `python -c` đều bị guard chặn cứng.
- Mọi logic đồng bộ, cập nhật Excel, hoặc update JSON registry nhiều file phải được thực hiện thông qua script chuyên dụng (`.py` có sẵn trong `tools/`) hoặc dispatch Worker O(1) qua `delegate_task` với budget <= 30 dòng.
- Cấm chạy `search_files` diện rộng trên toàn bộ thư mục gốc `D:/Taadaa`.
