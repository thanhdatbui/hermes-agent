# Pitfall: Xóa Đè / Tái Tạo Manifest & Cohort Giữa Chừng Gây Lỗi Hàng Loạt `cohort artifact assignment digest mismatch`

## 1. Hiện Tượng Lỗi
- Alert Farm bắn về Telegram:
  `🚨 [MÁY X] DỪNG PHIÊN`
  `• Script: multi-machine-feed-session`
  `• Lý do: cohort artifact assignment digest mismatch`
  `• Trạng thái: 🟡 GIỮ HIỆN TRƯỜNG ĐỂ HERMES AGENT XỬ LÝ`
- Toàn bộ hoặc hàng loạt máy trong phiên (máy 5, 8, 15, 20, 23, 44, 60, 68...) đồng loạt fail chỉ sau vài giây khởi động bước `feed-session-smoke`.

## 2. Nguyên Nhân Cốt Lõi (Anti-Pattern)
1. **Runner cầm tham số cố định khi bắt đầu phiên:**
   - Khi runner khởi động (ví dụ lúc 13:17 hoặc 13:30), nó nhận các tham số dòng lệnh gắn cứng:
     `--cohort-artifact .../cohort-v1-<hash_A>.json`
     `--assignment-manifest .../assignment-v1-<hash_A>.json`
   - File cohort chứa trường `manifest_digest` (mã băm SHA-256 của `assignment_manifest` lúc tạo ra nó).
2. **Background Cron định kỳ xóa sạch và tái tạo Manifest mới:**
   - Script chạy định kỳ (như `hermes_taikhoan_sync_cron.py` chạy mỗi 5 phút) khi phát hiện mtime file Excel thay đổi (hoặc chạy không kiểm tra điều kiện an toàn) đã thực hiện:
     `shutil.rmtree(manifests / today)`
     `shutil.rmtree(cohorts / today)`
     sau đó gọi `tiktok_picker.py` tái tạo manifest mới (`assignment-v1-<hash_B>.json`).
3. **Mâu thuẫn băm (Digest Mismatch) khi worker nạp dữ liệu:**
   - Trong quá trình phiên feed chạy (kéo dài 30–45 phút qua 80 máy), khi các worker của máy tiếp theo chạy đến bước nạp manifest từ ổ đĩa:
     `digest = sha256(assignment_manifest_on_disk)`
     `if digest != plan.manifest_digest: raise ValueError("cohort artifact assignment digest mismatch")`
   - Do manifest trên ổ đĩa đã bị thay thế bởi đợt sinh mới, mã băm không khớp nhau ➔ Toàn bộ các máy còn lại của phiên bị ngắt hàng loạt.

## 3. Quy Tắc Phòng Ngừa Bắt Buộc
1. **Tuyệt đối CẤM xóa đè (`shutil.rmtree`) thư mục `cohorts/<day>` và `manifests/<day>`** khi đang có phiên feed active hoặc khi chạy định kỳ trong ngày.
2. **Không tái tạo manifest giữa chừng khi không có yêu cầu bắt buộc:** Manifest trong ngày sinh ra một lần đầu ngày (06:00) và giữ tính bất biến (immutable) cho các phiên trong ngày.
3. **Bảo toàn trạng thái State:** Khi đồng bộ danh sách tài khoản từ Excel sang cấu hình cron, bắt buộc giữ nguyên lịch sử `last_feed_success_at` của các tài khoản đã hoàn thành trong ngày thay vì gán trắng `None`.
