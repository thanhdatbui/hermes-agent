# AI Auto-Recovery Git Concurrency & Deduplication Patterns

## 1. Concurrency Bottleneck in Multi-Machine Auto-Recovery
Khi farm chạy hàng loạt máy (ví dụ 30-74 máy cùng chạy feed session), nhiều máy có thể gặp lỗi / popup cùng thời điểm và kích hoạt module AI Auto-Recovery song song.
Các tiến trình Auto-Recovery đều chạy trên cùng shared workspace (`D:\Taadaa\tiktok-luot nuoi acc`).

### Pitfall 1: Non-blocking Mutex (`git_lock_busy`)
- **Triệu chứng:** Máy đầu tiên lấy được `git_patch.lock` để commit/push; các máy tiếp theo kiểm tra thấy file lock tồn tại liền fail ngay lập tức với mã lỗi `❌ git_lock_busy`.
- **Giải pháp:** Phải dùng **Spinlock / Queue Retry Loop** với timeout (ví dụ `timeout=60.0`, `retry_interval=1.0`). Khi máy trước xong và nhả lock, máy sau lấy lock và tiếp tục, không bỏ sót commit.

### Pitfall 2: Rebase with Unstaged Changes (`cannot pull with rebase`)
- **Triệu chứng:** Auto-Recovery ghi code mới vào file (unstaged) ➔ chạy pytest ➔ gọi `git pull --rebase origin master` ➔ Git từ chối vì working tree dirty.
- **Giải pháp:** Thứ tự chuẩn bắt buộc:
  1. Ghi code patch vào file.
  2. Chạy pytest xác nhận GREEN.
  3. `git add <target_path>` + `git commit -m "..."` (Working tree sạch).
  4. `git fetch origin` + `git pull --rebase origin master` (An toàn chống non-fast-forward conflict).
  5. `git push origin master`.

---

## 2. Popup Consolidation & Deduplication in `benign_popup.py`
Do các máy khác nhau có thể gặp cùng loại màn hình/popup tại các thời điểm khác nhau, các hàm handler tự động sinh ra có nguy cơ bị trùng lặp chức năng:

- **Camera / Video Creation Mode:** Nhận diện các nhãn `["CAMERA", "TẠO", "LIVE", "15s", "60s", "10 phút", "ẢNH", "VĂN BẢN"]` và `record/shoot` resource-id. Thoát qua nút [X] (95, 92) hoặc `actions.back()`.
- **Email Update Prompt:** Nhận diện `_EMAIL_UPDATES_KEYWORDS = ("nhận thông tin cập nhật qua email", "email của bạn?", "get email updates", ...)`. Đóng qua nút [X] modal (918, 796).
- **Search Suggestions Overlay:** Gửi `keyevent(4)` để thoát giao diện tìm kiếm về Feed.
- **Hashtag Campaign Modal:** Nhận diện markers chiến dịch (Closeup / Hát lời thơm mát) và tap [X] (78, 312).
- **Location Permission Prompt:** Tự động tap nút "Hủy / Từ chối / Không cho phép" (205, 1200).
- **Creator Highlight Popup:** Nhận diện "nhà sáng tạo mà bạn quan tâm" và tap "Đã hiểu" (540, 1715).

**Quy tắc:** Khi hợp nhất code, luôn giữ lại alias hàm cũ trỏ về hàm chuẩn mới để đảm bảo tương thích ngược 100% cho mọi module gọi cũ.
