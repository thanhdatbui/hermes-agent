# Chẩn Đoán Báo Động Batch Nuôi Acc / Lướt Feed & Xử Lý Sự Cố Mất Phiên (Session-Lost)

## 1. Kiến Trúc Bộ Cảnh Báo Dual-Cluster (`batch_aggregator.py`)
Hệ thống giám sát batch tự động gộp kết quả chạy của 2 cluster (Kibe Local: Máy 1-80 & Admin Remote: Máy 201-280) và bắn alert Telegram khi vi phạm ngưỡng an toàn:

- **Marker thông báo**: `D:/Taadaa/runtime/cron-state/batch-alerts/<batch_id>.sent`.
- **Đường dẫn Manifest chạy thực tế**:
  - Kibe: `D:/Taadaa/runtime/kibe/live/<YYYY-MM-DD>/row-<N>-<time>/<timestamp>/run_manifest.json`
  - Admin: `D:/Taadaa/runtime/admin/live/<YYYY-MM-DD>/row-<N>-<time>/<timestamp>/run_manifest.json`
- **Ngưỡng kích hoạt cảnh báo (`should_alert = True`)**:
  1. `session_lost_count > 0`: **Báo động đỏ P0** (phát hiện mất phiên, văng nick khỏi Switcher, lỗi auth). Dù chỉ 1 máy dính cũng kích hoạt alert toàn farm.
  2. `systemic_signatures`: Có từ 5 máy trở lên gặp cùng một loại mã lỗi/chữ ký lỗi.
  3. `challenge_count > 0`: Gặp thử thách bảo mật / captcha / verify danh tính.

---

## 2. Quy Trình Triage O(1) Cho Coordinator (Anti-Insanity & Anti-Overengineering)

### Bước 1: Định vị đợt chạy O(1) từ Marker
Đọc marker mới nhất trong `D:/Taadaa/runtime/cron-state/batch-alerts/` để lấy chính xác `row-N` và thư mục `timestamp`. CẤM dùng `search_files` hay `os.walk` quét toàn bộ ổ đĩa.

### Bước 2: Phân tích `multi_machine_summary` trong Manifest
Dùng Python mở file `run_manifest.json` của 2 cluster:
```python
import json
with open('D:/Taadaa/runtime/kibe/live/<date>/<row_dir>/<ts>/run_manifest.json', 'r', encoding='utf-8') as f:
    kibe_summary = json.load(f).get('multi_machine_summary', [])
```
- **Tách bạch Skipped vs Failed**:
  - Máy Admin báo `config-error: account row N is empty (no username) for machine 2xx, skipping`: Đây là trạng thái **BỎ QUA** do slot chưa có tài khoản, hoàn toàn bình thường, không được tính là lỗi vận hành.
- **Lọc máy P0 Session Lost**:
  - Tìm các máy có `final_status == 'manual-needed'` và `stop_reason` chứa `account-switcher-missing-expected` hoặc từ khóa `login/session lost`.

### Bước 3: Kiểm tra hiện trường O(1) máy dính P0
- Dùng công cụ chuẩn:
  ```bash
  python D:/Taadaa/tools/inspect_machine.py <N>
  ```
- Kiểm tra pin, trạng thái màn hình và activity đang chiếm focus (`mCurrentFocus`).

### Bước 4: Soi Bằng Chứng UI XML & Screencap Trong `artifacts`
Vào thư mục artifact của máy bị lỗi:
`machines/machine_<M>/<ts>/artifacts/device_<id>/account_<id>/feed-session-smoke/`
- So sánh UI XML giữa hai thời điểm:
  - `profile_preflight_switcher_1_guard/attempt_1/ui.xml`: Trạng thái Switcher mở lần đầu trước khi chuyển nick.
  - `profile_preflight_switcher_2_guard/attempt_1/ui.xml`: Trạng thái Switcher mở lần 2 sau khi tap switch thất bại.
- **Dấu hiệu định danh Văng Nick (Eviction)**:
  - `switcher_1` có đủ 8 tài khoản (bao gồm nick mục tiêu).
  - Sau thao tác switch, TikTok tự động văng nick -> `switcher_2` sụt xuống chỉ còn 7 tài khoản và xuất hiện nút *"Thêm tài khoản"*.
  - Đính kèm ảnh `screen.png` từ `switcher_2_guard` làm bằng chứng nghiệm thu hiện trường thực tế (`MEDIA:...`).

---

## 3. Phân Loại Lỗi Phổ Biến & Hướng Xử Lý Chuẩn

| Phân Loại | Triệu Chứng / Stop Reason | Nguyên Nhân Gốc Rễ | Hướng Xử Lý Điều Phối |
| :--- | :--- | :--- | :--- |
| **P0: Mất Phiên / Văng Nick** | `account-switcher-missing-expected` | TikTok hết hạn session, văng nick khỏi switcher còn 7 nick. | Khóa batch; dispatch worker chạy `tiktok_login_v1.py <M> --email <user> --ss` đăng nhập bù; nghiệm thu đủ 8 nick tại Switcher. |
| **Mất Kết Nối ADB / USB** | `device offline or ADB/USB disconnected` | Cáp USB lỏng, hub sập nguồn hoặc cổng USB tiếp xúc kém. | Báo cáo User kiểm tra phần cứng; tuyệt đối KHÔNG tự retry bằng code. |
| **Cản Trở UI Tạm Thời** | `unexpected popup/dialog marker detected` | Bottom sheet gợi ý bạn bè, popup nhập pass Wi-Fi, hộp thoại hệ thống. | Tắt popup / send KEYCODE_BACK / clear recent apps đưa về HOME cho phiên sau. |
| **Gặp Màn Live Stream** | `unknown TikTok state` trên Live Kangaroo/bán hàng | Lướt feed trúng phòng live stream đặc thù có layout chat/ranking khác video thường. | Dừng an toàn bảo vệ farm; bổ sung nhận diện layout live stream nếu cần. |
| **Lỗi Socket Mạng Admin** | `feed swipe command failed` trên Admin remote | Nghẽn đường truyền mạng nội bộ LAN giữa host Kibe và port 5037 của Admin. | Thử lại canary đơn máy qua `inspect_machine.py` hoặc chạy bù khi fleet rảnh. |

---

## 4. Quy Chuẩn Đăng Nhập Bù Cho Máy Bị Văng Nick (Recovery Command)
Khi user phê duyệt cứu phiên cho máy dính P0:
```bash
cd /d/Taadaa/Tiktok_Reg
env -u PYTHONPATH "D:/Taadaa/python-envs/tiktok-reg-recovery/Scripts/python.exe" tiktok_login_v1.py <M> --email <target_username> --ss
```
- **Lưu ý**:
  1. Nếu máy đang dính popup che phủ (như popup Wi-Fi), phải tắt popup trước.
  2. Bắt buộc nghiệm thu bằng screencap tại Account Switcher thể hiện rõ danh sách tài khoản active đủ 8 slot trước khi teardown.
