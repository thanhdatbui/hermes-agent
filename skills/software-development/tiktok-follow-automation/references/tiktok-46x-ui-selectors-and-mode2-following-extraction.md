# TikTok 46.x UI Selectors and Mode 2 Following Extraction

## TikTok 46.x Profile & Action Selectors
- **Profile Action Button IDs:** `id/fds` (máy cũ), `id/ff8` (máy 2), `id/fij` (máy 6+), `id/fi6` (máy 16+), fallback regex `id/f[a-z0-9]{2,3}$` hoặc action row band (y: 750-1000, height: 90-180).
- **Profile Stat Counters:** `id/sdn`, `id/shq`, `id/svt`, `id/svs`, `id/suu`, `id/sut` — chứa các số liệu đếm follower/following, tuyệt đối loại trừ khỏi action button classifier.
- **Search Navigation:** Search back button trên giao diện mới có ID `id/bqp` (hoặc `id/bow`, `id/back_btn`), cần ưu tiên tap icon trước khi dùng keyevent back.

## Mode 2 Following List Parsing & ID Extraction
- **RecyclerView ID:** `id/uoc` (bên cạnh `id/u5r`, `id/u_q`).
- **Follow Button in Row:** `id/tvn` (bên cạnh `id/tcj`, `id/thb`).
- **Empty Title ID:** `id/yxo` (bên cạnh `id/yby`, `id/yhj`).
- **Two-Line Username Logic:**
  1. Nếu `txt_desc` chứa `@handle` (ví dụ `@laphufkc18d`) ➔ Lấy trực tiếp handle này.
  2. Nếu `txt_desc` chứa subtext mô tả phụ (*"Được follow bởi..."*, *"Follow..."*, *"Bạn bè chung..."*) ➔ Handle chính là `txt_user_name` (dòng 1).
  3. Lọc nội bộ Farm: Chỉ tap Follow khi `_normalize_handle(handle)` nằm trong `internal_uids` (`taikhoan_run_safe.xlsx`). Nick ngoài farm tự động `skip`.

## Test Execution Rule
Khi user yêu cầu chạy test một mode (như Mode 2), phải chạy trọn vẹn toàn bộ chuỗi quota của session (`--mode 2`), không được ngắt sau 1 tap đơn lẻ gây hiểu nhầm session bị lỗi hay dừng sớm.
