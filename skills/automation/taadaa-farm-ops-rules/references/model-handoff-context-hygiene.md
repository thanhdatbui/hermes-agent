# SOP Chuyển giao & Tiếp quản Session Giữa Các Model (Luna ↔ Gemini)

## 1. Bản chất cốt lõi: Ngăn chặn Context Poisoning (Nhiễm độc ngữ cảnh)
- **Vấn đề:** Khi một session cũ bị sa lầy (tranh cãi rubric P1/P2/P3, lặp lại thất bại, over-engineering, code dở dang...), việc dùng lệnh resume hoặc ép model mới đọc lại toàn bộ chat log cũ sẽ khiến model mới bị "nhiễm độc context".
- **Hậu quả:** Model mới sẽ tiếp tục đi sửa đống rác mà model cũ vẽ ra thay vì giải quyết dứt điểm bài toán nghiệp vụ ngoài thực tế.

## 2. Quy trình 3 bước tiếp quản sạch (Clean Handover Protocol):

### Bước 1: Dừng tiến trình cũ & Cách ly Code dở dang
1. Gõ `/stop` tại session cũ để kill toàn bộ background subagents / terminal jobs đang chạy ngầm, tránh xung đột ghi đè repo.
2. Cất toàn bộ thay đổi dở dang vào nhánh backup an toàn (`wip/<model>-backup`):
   ```bash
   git switch -c wip/luna-backup
   git add -A
   git commit -m "wip: backup luna state before handoff"
   git switch master # hoặc branch làm việc chính
   git status --porcelain # Bắt buộc: Working tree phải 100% CLEAN
   ```
   *Lưu ý:* Nếu dính stale index lock: kiểm tra tiến trình git và gỡ bỏ `.git/index.lock` trước khi commit.

### Bước 2: Khởi tạo Fresh Session (`/new`)
- Bắt đầu một session mới hoàn toàn, tuyệt đối không dùng lệnh resume hay copy paste cả đoạn chat cũ vào.

### Bước 3: Handover Contract 5 dòng (Ngắn gọn - Thực tế - Không mang rác)
Chỉ chuyển giao thông tin cốt lõi theo mẫu sau:
```text
Mục tiêu gốc: [Mô tả mục tiêu cụ thể, ví dụ: Sửa lỗi TikTok feed M40 văng login & kích hoạt reg bù]
Hiện trường/Log: [Lệnh O(1) kiểm tra nhanh, ví dụ: python tools/inspect_machine.py <N>]
Trạng thái Git: Đã cất wip/luna-backup, branch chính master đang sạch 100%.
Ranh giới (Scope Lock): Sửa đúng hàm/file X, cấm over-engineering P1/P2/P3, budget <= 30 dòng.
Tiêu chí DONE: Test focused <30s pass + farm chạy lại được.
```

## 3. Quy tắc điều phối khi dùng Gemini tiếp quản:
- **Tận dụng tốc độ:** Gemini rất xốc vác và xử lý nhanh khi nhận bài toán sạch và mục tiêu cụ thể.
- **Giữ chặt 6 Gates & Ngân sách O(1):** Vẫn tuân thủ phân vai Coordinator (không tự sửa code bừa bãi), kiểm soát chặt budget (<= 2 files, <= 30 dòng thay đổi) và test focused trước khi nghiệm thu.
