# Case 176: Telemetry Sức Khỏe Tài Khoản & Cơ Chế Phục Hồi 0-View Jail (Part 1)

## 1. Bối Cảnh & Mục Tiêu Telemetry Thực Chiến
- Trong các hệ thống phone farm lớn (160 máy), các tài khoản sau một thời gian hoạt động có thể bị TikTok bóp phân phối (0-View Jail) hoặc dính penalty nhả follow.
- Nếu hệ thống tiếp tục ép nick cày (Follow + Upload video liên tục) trong khi tài khoản đang bị hạn chế, nick sẽ nhanh chóng bị shadowban vĩnh viễn và làm dơ luôn dải IP proxy.
- **Mục tiêu:** Xây dựng cơ chế quan sát sức khỏe (Observability) chuẩn **Zero Extra Cost**: tận dụng dữ liệu UI XML có sẵn ở bước Profile Preflight để bóc tách view các video gần nhất mà không tốn thêm bất kỳ lệnh ADB hay thao tác mở app nào.

## 2. Giải Pháp Bóc Tách View Từ Profile XML (`feed_swipe_smoke.py`)
- **Vị trí áp dụng:** Hàm `_profile_identity_from_xml` trong `python_runner/flows/feed_swipe_smoke.py`.
- **Nguyên tắc lọc & phòng thủ giao diện TikTok (UI Defenses):**
  1. **Loại trừ Header ($y < 850$):** Chỉ lấy các UI element ở nửa dưới màn hình (`bounds[0][1] >= 850`) để tránh nhận nhầm số Follower/Following/Likes hiển thị ở phần header trên cùng.
  2. **Bỏ qua nhãn đặc thù:** Loại bỏ các ô video chứa text `"Đã ghim"` (Pinned), `"Nháp"` (Draft), `"Thích"` (Liked) để không lấy nhầm các video cũ được ghim lên đầu.
  3. **Regex chuẩn hóa view TikTok:** `re.compile(r"^\d+(\.\d+)?[KMkm]?$")` (khớp các định dạng `0`, `15`, `950`, `1.2K`, `3.5M`).
  4. **Sắp xếp thứ tự lưới video:** Sắp xếp theo tọa độ từ trên xuống dưới theo từng hàng (`y1 // 100`) và từ trái sang phải (`x1`) để đảm bảo video mới nhất luôn nằm ở đầu danh sách.
  5. **Mở rộng kết quả trả về:** Thêm trường `"latest_views": latest_views` vào dictionary định danh của tài khoản.

## 3. Cơ Chế Phục Hồi: Deep Organic Rest & Quy Tắc 0-View Thực Chiến (Cách B)
- **Quy tắc đánh giá 0-View Jail (Chống phạt oan video flop lẻ):**
  1. **Điều kiện ngấm:** Chỉ xét các video đã đăng qua > 24 giờ. Video mới đăng <24h luôn coi là an toàn.
  2. **Kênh mới toanh:** Có duy nhất 1 video mà sau 24h vẫn dính `0 view` $\rightarrow$ Kích hoạt Deep Organic Rest 3 ngày.
  3. **Kênh đã có nhiều video:** CHỈ kích hoạt khi **cả 2 video gần nhất liên tiếp đều dính `0 view`**. Nếu chỉ có 1 video mới nhất dính 0 view nhưng video liền kề trước đó có view (ví dụ `['0', '150', '320']`) $\rightarrow$ Vẫn tính là **HEALTHY** (flop nội dung cá biệt, không phạt oan). Vì hệ thống đã có sẵn cơ chế chặn follow khi dính cooldown nên không cần siết quá gắt ở tầng video.
- **Hành vi khi kích hoạt Deep Organic Rest (3 ngày / 72h):**
  - Mở rộng hàm `_is_account_organic_rest_day` trong `python_runner/flows/multi_machine_feed_session.py` với tham số `force_rest_ledger: dict[str, Any] | None = None`.
  - Tài khoản được đánh dấu cờ ép nghỉ dưỡng sinh: bypass 100% Follow Hook và Upload Hook trong 3 ngày, chỉ lướt feed tích lũy trust trước khi được cày trở lại.

## 4. Kiểm Chứng & Test Suite
- Test bóc tách trên XML mẫu chứa cả header follower và video ghim:
  - `extracted == ['1.2M', '0', '245']` $\rightarrow$ PASS 100%.
- `python -m py_compile` cả 2 file `feed_swipe_smoke.py` và `multi_machine_feed_session.py`: PASS exit 0.
- Git Commit: `20295cd feat(telemetry): extract latest video views from profile xml for zero-view detection (Case 176 - Part 1)`.
