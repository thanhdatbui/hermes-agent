# Canonical Tooling Priority & In-Place Core Fix Discipline (2026-10-13)

## 1. Sự Cố & Lời Chỉnh Huấn Từ User
- **Ngữ cảnh:** Khi gặp lỗi đổi avatar trên Máy 33 (TikTok v47 Samsung S7, Layout C), Coordinator thấy runner chính thức `run_tiktok_upload_avatar.ps1` báo lỗi thì lập tức bỏ cuộc và nhảy sang chế biến script ad-hoc tap tọa độ tay (`do_upload_avatar_m71.py` copy sang sửa tọa độ/serial).
- **User chất vấn gay gắt:** *"Là t ns mày ms đọc script chứ trc đó tính viết nguyên code upload ava lại đúng k... Xử lý đi. R làm sao có cơ chế cho mày ưu tiên tìm script có sẵn r chạy (kể cả fix cũng handle luôn vào script có sẵn) thay vì tự ngồi chế lại cái bánh xe đã có sẵn"*.
- **Nguyên nhân gốc rễ hành vi xấu:**
  1. Thói quen tiện tay chế script con gõ `adb shell input tap` mù để "chữa cháy" tạm bợ thay vì kiên trì bám quy trình canonical.
  2. Bỏ qua việc phân tích log/code của runner chính thức để hiểu tại sao nó fail. Khi runner fail do bộ dò giao diện (`TopLeftPencilLayout`) bị lệch bounds (`n.l < 10`), Coordinator không sửa vào codebase của runner mà lại đẻ ra script riêng.

---

## 2. Quy Tắc Bắt Buộc: 3 Bước Ưu Tiên Canonical Tooling & In-Place Fix

Mọi tác vụ vận hành trên Farm (Avatar, Logout, Reg, Feed, Follow, 2FA, Proxy) BẮT BUỘC tuân thủ thứ tự ưu tiên sau:

### Bước 1: Tra Cứu Script Canonical Đã Có Sẵn (Zero Re-invent)
- **CẤM TUYỆT ĐỐI** tự viết script Python/Shell mới khi bắt đầu task.
- Luôn tra cứu và sử dụng bộ tooling canonical đã được kiểm chứng:
  - **Upload Avatar:** `D:\Taadaa\Tiktok-video\run_tiktok_upload_avatar.ps1` (hoặc launcher `run_avatar_m1.py <M>`).
  - **Logout Nick Ký Sinh:** `python D:/Taadaa/tools/do_logout_account.py <M> <username> <serial>`.
  - **Inspect Thiết Bị:** `python D:/Taadaa/tools/inspect_machine.py <N>`.
  - **Bật 2FA TikTok:** `D:\Taadaa\tiktok-add-2fa\batch_2fa_runner.py`.
  - **Mua Hotmail:** `python D:/Taadaa/tools/buy_hotmail.py`.

### Bước 2: Phân Tích Lỗi Thực Sự Khi Runner Vấp (Root-Cause Triage)
- Khi runner chuẩn báo lỗi (exit != 0 hoặc checkpoint fail):
  - **CẤM** bỏ cuộc để viết script ngoài lề.
  - Mở file log chi tiết của run đó (ví dụ: `runs/run_<serial>_<timestamp>/execution.log` hoặc `batch-runs/.../machine-<N>.out.log`).
  - Đọc XML UI dump và đối soát hiện trường để xác định chính xác dòng code / hàm nào trong runner bị vấp (ví dụ: `profile_layouts` trả về `UNKNOWN_LAYOUT` vì bounds icon khác biệt).

### Bước 3: Sửa Trực Tiếp Vào Core Runner (In-Place Core Fix O(1))
- **Nguyên tắc:** Vá lỗi ngay tại codebase của runner chuẩn (`D:\Taadaa\Tiktok-video\scripts\...` hoặc `automation-core`) thông qua quy trình O(1) hoặc Worker dispatch có contract chặt chẽ.
- **Lợi ích:**
  - Một lần sửa đúng gốc rễ sẽ tự động chữa lành cho toàn bộ 80-280 máy trên farm.
  - Giữ vững toàn bộ guardrails kiểm chứng, logging, idempotency, device-lock và báo cáo tự động của runner.
- **Chạy lại runner chuẩn:** Sau khi vá core, kích hoạt lại chính runner canonical đó để kiểm chứng end-to-end.

---

## 3. Checklist Tự Kiểm Tra Trước Khi Chạy Bất Kỳ Script Nào (Anti-Cowboy Gate)
1. Task này đã có runner/script chuẩn trong `tools/` hoặc repo chính chưa? (Nếu có: BẮT BUỘC dùng runner chuẩn).
2. Nếu runner chuẩn fail: Ta đã tìm ra đúng file code gây lỗi trong core runner chưa? (Chưa tìm ra: CẤM viết script thay thế).
3. Bản vá có được đưa trực tiếp vào file core của runner không? (Phải sửa vào core, cấm để lọt script chắp vá bên ngoài).
