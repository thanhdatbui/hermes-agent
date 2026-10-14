# TikTok Video Pinning Automation (Profile Grid Long-Press)

## 1. Cơ chế UI Ghim Video Thực Chiến
- **Thao tác đè cảm ứng (Long-press):**
  * Không mở video player rồi vuốt tìm trong menu ba chấm `...` (chậm và nhiều bước UI).
  * Long-press vào giữa ô video trên lưới Profile (`adb shell input swipe X Y X Y 1000`).
  * Action Sheet xuất hiện ở đáy màn hình -> tap `"Ghim lên đầu"` / `"Pin to top"`.
  * Nếu video đã được ghim từ trước, Action Sheet hiển thị `"Bỏ ghim khỏi đầu"` / `"Unpin from top"`.

## 2. Bóc tách & Chuẩn hóa số View (Parse View Count)
- Xử lý các định dạng hiển thị của TikTok:
  * `17,8K` / `17.8K` -> `17800`
  * `1,2M` / `1.2M` -> `1200000`
  * `1.140` / `1,140` -> `1140`
  * `375` -> `375`
- **Ngưỡng sàn bảo vệ (Floor Filter):**
  * Mặc định `--min-views 1000`: Chỉ ghim khi video vượt mốc 1.000 view (vượt qua seed pool ban đầu), tránh ghim clip lẹt đẹt 100-300 view.
  * Giới hạn tối đa `--max-pins 3` (trần ghim của TikTok).
  * Bỏ qua tile bản nháp (`bản nháp`, `draft`) và các tile đã có tag `"Đã ghim"` / `"Pinned"`.

## 3. Tính tương thích với Luồng Đăng Video (`state_machine.py`)
- Việc ghim video **hoàn toàn không gây lỗi** cho script đăng video:
  * Script đăng kiểm tra tổng số video tăng lên (`current > baseline`), không bắt buộc ô [0,0] phải là video mới.
  * Tile video đã ghim vẫn giữ nguyên cấu trúc bounds và node XML (`eti`, `cover`, `play_count`), gia số `+1` sau khi xuất bản vẫn được ghi nhận chuẩn xác.
