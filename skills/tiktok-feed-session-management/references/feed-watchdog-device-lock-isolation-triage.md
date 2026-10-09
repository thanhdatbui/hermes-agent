# Triage Lỗi Feed Session & Phân Biệt Device-Lock Isolation (Night 2FA vs Feed)

## 1. Hiện tượng False Alarm "Lỗi App TikTok/Script" diện rộng ban đêm
Trong các ca đêm (đặc biệt Ca 4: 00:00 - 06:00, Row 7/8), báo cáo từ `feed_session_watchdog` có thể cảnh báo số lượng lớn máy fail (ví dụ 35–45 máy) trong mục `Lỗi App TikTok/Script`.

### Bản chất hiện trường:
- Hệ thống Taadaa Farm có các cronjob cuốn chiếu chạy ban đêm, tiêu biểu là `night-tiktok-2fa-watchdog` (project `tiktok-add-bao-mat-f2a`, bật 2FA TikTok cho các tài khoản chưa có 2FA).
- Khi `night-tiktok-2fa-watchdog` chiếm thiết bị, nó ghi file lock chuẩn: `~/.codex/device-locks/machine_<N>.lock.json` và `serial_<serial>.lock.json`.
- Khi runner nuôi feed (`multi_machine_feed_session.py`) quét đến máy đang có active lock, nó tuân thủ cơ chế bảo vệ cách ly thiết bị:
  - Ghi nhận `final_status: skipped-device-locked`.
  - `stop_reason: device lock active: path=... project=tiktok-add-bao-mat-f2a ... command=phase-b-live`.
  - Không can thiệp, không cướp màn hình, không làm gián đoạn tiến trình 2FA.
- **Hạn chế của Watchdog**: Hiện tại watchdog tổng hợp chỉ phân loại nhị phân (`success` vs không phải `success`), nên mọi máy `skipped-device-locked` bị gom chung vào `Lỗi App TikTok/Script`. Điều này tạo ra False Alarm tỷ lệ lỗi cao (trên 30-50%), dù thực chất farm đang tự cách ly tài nguyên an toàn 100%.

## 2. Quy trình trích xuất nguyên nhân O(1) không quét đĩa
Tuyệt đối CẤM dùng `grep -r`, `find`, `os.walk` quét đĩa. Sử dụng đường dẫn chuẩn xác O(1):

1. **Xác định Artifact của Ca/Phiên**:
   - `D:/Taadaa/runtime/<cluster>/live/<YYYY-MM-DD>/<row-X-HHMMSS>/<timestamp>/run_manifest.json`
   - Ví dụ: `D:/Taadaa/runtime/kibe/live/2026-10-10/row-8-013048/20261010-013223/run_manifest.json`

2. **Đọc `blocker_taxonomy_summary` và `multi_machine_summary`**:
   ```python
   import json
   with open(manifest_path, 'r', encoding='utf-8') as f:
       data = json.load(f)
   summary = data.get('multi_machine_summary', [])
   # Phân loại stop_reason
   reasons = {}
   for m in summary:
       st = m.get('final_status')
       rs = (m.get('stop_reason') or '').split('\n')[0][:80]
       reasons.setdefault(f"{st} | {rs}", []).append(m.get('machine'))
   ```

3. **Phân loại 3 nhóm máy trong danh sách Fail**:
   - **Nhóm 1: Device-Lock Isolation (An toàn / Safe Skip)**:
     `final_status == "skipped-device-locked"` với stop_reason chỉ rõ `project=tiktok-add-bao-mat-f2a` hoặc tiến trình hợp lệ khác. Các máy này KHÔNG phải lỗi app hay script, không cần can thiệp.
   - **Nhóm 2: Lỗi Mạng / Proxy / Cáp USB**:
     `blocked-proxy-vpn` (proxy port closed/unreachable, kill switch kích hoạt) hoặc `Device serial not found in adb devices` (cáp USB lỏng, hub rớt nguồn).
   - **Nhóm 3: Lỗi App / UI thật cần fix**:
     `prepare-tiktok failed to focus TikTok`, `unexpected popup/dialog marker detected`, `feed not confirmed`, `feed swipe command failed`.

## 3. Checklist xác nhận trước khi báo cáo User
- [ ] Đã tách riêng số máy `skipped-device-locked` ra khỏi số máy lỗi app/script thật.
- [ ] Đã kiểm tra trạng thái lock hiện tại trong `~/.codex/device-locks/` xem batch 2FA đã giải phóng hết chưa.
- [ ] Đã kiểm tra ca kế tiếp (Ca 1 Sáng lúc 06:00) đã bắt đầu chạy bình thường trên các máy đã nhả lock chưa.
