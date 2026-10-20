# Hashtag Reversion Trap: Authority Cron Overwrite & Multi-Cluster Sync Failure

## Triệu Chứng
Khi người vận hành hoặc agent sửa Keyword Video và Hashtag Pool trong file bảng tính cấu hình (ví dụ sửa từ `Thú cưng` sang `Khoa học`), chỉ sau một chu kỳ cron (ví dụ 15 phút), dữ liệu trong bảng tính lại bị tự động ghi đè lộn ngược lại giá trị cũ.

## 3 Nguyên Nhân Gốc Rễ

### 1. Cron Watchdog chạy ngầm định kỳ
- Tiến trình cron ngầm chạy bộ đồng bộ keyword/hashtag định kỳ để đảm bảo tính nhất quán giữa cơ sở dữ liệu và bảng tính.
- Nguồn chân lý (Source of Truth) mà cron đọc vào là kho dữ liệu thẩm quyền (authority database).
- Cron duyệt qua các dòng trong bảng tính, lấy số folder video gốc, tra vào authority database, rồi tự động tính toán lại và ghi đè cột Keyword Video & Hashtag Pool.

### 2. Authority Database bị gán sai niche từ khâu thu thập ban đầu
- Khi thu thập video về kho lưu trữ, hệ thống tự động gắn nhãn sơ bộ (có thể bị phân loại sai niche).
- Dù file bảng tính được sửa tay, nhưng authority database vẫn lưu nhãn cũ -> Đến chu kỳ tiếp theo, cron đọc nhãn cũ và ghi đè ngược lại bảng tính.

### 3. Thiếu đồng bộ đa cụm (Multi-cluster) & Bỏ sót cờ khóa cứng (`.manual_hashtag_locked`)
- Script đồng bộ chỉ quét cụm máy chính mà bỏ quên cụm máy phụ, khiến cụm phụ bị lệch dữ liệu.
- Script đồng bộ thiếu logic kiểm tra sự tồn tại của file cờ bảo vệ `.manual_hashtag_locked` trong thư mục video trước khi ghi đè.

### 4. Bẫy đè ô Video Gốc trước khi kiểm tra khóa (Pre-check Mutation Trap & $F_{src}$ vs $F_{vid}$)
- Script đồng bộ tự động tính toán $F_{src} = (S-1)*80 + M$ theo công thức toán học và vội vàng ghi đè vào ô `Video Goc` của sheet `TaiKhoan` *trước khi* kiểm tra hàm `is_folder_hashtag_protected`.
- Với các máy dùng folder lệch chuẩn (ví dụ Máy 20 Slot 1 dùng folder render/nguồn 153 thay vì 20):
  * Khi script đè `curr_vg` thành 20, nó chỉ kiểm tra `is_folder_hashtag_protected(20)`. Nếu chỉ có folder 153 được đăng ký mà folder 20 chưa đăng ký, script sẽ xem như tài khoản chưa khóa!
  * Sau đó, script tra Folder 20 vào CSDL thẩm quyền (đang lưu nhãn cào cũ như `noithat`), rồi ghi đè Keyword thành `Nội thất` và Hashtag thành `#noithat ...`, phá nát kênh thể thao / gym của người vận hành.
- **Quy tắc vàng Dual-Folder Lock**: Khi chuẩn hoá tài khoản có $F_{vid} \neq F_{src}$, bắt buộc đăng ký **CẢ HAI FOLDER** ($F_{src}$ và $F_{vid}$) vào `manual_hashtag_protected_folders.json` và cập nhật cùng niche trong CSDL thẩm quyền. Script đồng bộ phải kiểm tra `is_folder_hashtag_protected(f_src) or is_folder_hashtag_protected(curr_vg)` *trước khi* thực hiện bất kỳ phép gán ô nào.

## Quy Trình Xử Lý Triệt Để (4 Chốt Chặn Bắt Buộc)

1. **Khóa cứng Authority Database:** Cập nhật trường `niche` của folder nguồn trong cơ sở dữ liệu thẩm quyền trước khi sửa bảng tính.
2. **Cập nhật đồng thời toàn bộ các cụm:** Cập nhật cả 2 sheet (TaiKhoan và Hashtag theo Folder) trên mọi cụm máy (Kibe, Admin).
3. **Cắm cờ khóa cứng vật lý trong cả 2 kho (render & gốc):** Tạo file rỗng `.manual_hashtag_locked` và `.manual_avatar_locked` trong thư mục video render và video gốc.
4. **Bảo vệ chống ghi đè:** Kiểm tra sự tồn tại của marker `.manual_hashtag_locked` trước khi thực hiện bất kỳ lệnh đồng bộ tự động nào.
