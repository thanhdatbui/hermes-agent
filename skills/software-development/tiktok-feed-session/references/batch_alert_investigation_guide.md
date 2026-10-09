# Hướng Dẫn Điều Tra Batch Alert & Pitfalls Nuôi Feed TikTok

## 1. Đường Dẫn Log & Manifest Batch Chuẩn O(1)
Khi nhận Batch Alert từ hệ thống giám sát hoặc user báo lỗi diện rộng:
- Thư mục chạy thực tế:
  `D:/Taadaa/runtime/kibe/live/<YYYY-MM-DD>/row-<ROW>-<HHMMSS>/<RUN_ID>/`
- File quan trọng nhất:
  - `run_manifest.json`: Chứa `multi_machine_summary` (chi tiết 80 máy) và `blocker_taxonomy_summary` (phân loại lỗi theo nhóm).
  - `summary.txt`: Báo cáo tổng hợp số swipe, event_counts (`success`, `manual-needed`, `blocked-proxy-vpn`).
  - Thư mục từng máy: `machines/machine_<N>/<RUN_ID>/` gồm `summary.txt`, `log.jsonl`, `recovery_lock_handoff.json`, và `artifacts/`.

**Quy tắc:** Tuyệt đối không dùng find/grep quét toàn ổ đĩa. Truy cập trực tiếp theo cây thư mục `live/<date>/<session>/`.

---

## 2. Pitfall: Giao Diện Full-Tab "Bạn bè / Đề xuất kết bạn" (Friends Feed)
- **Hiện tượng:**
  Script dừng ở `manual-needed: unexpected popup/dialog marker detected; swipe recovery (2 swipes) still stuck`.
- **Dấu hiệu nhận diện trong UI XML:**
  - Chứa các text: `"Bạn bè"`, `"Đề xuất"`, `"Vuốt lên để bỏ qua"`, danh sách tài khoản bạn bè có nút `"Follow"`, `"Không quan tâm"`.
  - Thanh bottom bar có nút `"Trang chủ"`, `"Cửa hàng"`, `"Hộp thư"`, `"Hồ sơ"`.
- **Nguyên nhân gốc rễ:**
  - Detector nhận nhầm đây là popup nổi `follow_friends_suggestion_popup`.
  - Bộ xử lý popup cố gắng tap đóng popup nhưng đây là một trang feed cuộn toàn màn hình (full-tab) chứ không phải dialog overlay có nút đóng/hủy.
  - Thử lại 3 lần không đổi màn hình dẫn đến kích hoạt fail-safe `manual-needed`.
- **Cách xử lý đúng:**
  - Bổ sung cơ chế phát hiện màn hình full-tab Bạn bè/Đề xuất: Nếu phát hiện đang ở tab này, điều hướng quay lại For You bằng cách tap nút `"Trang chủ"` ở bottom bar hoặc gửi phím `BACK`, không cố dismiss như popup.

---

## 3. Transient Alert vs Terminal State (Cảnh báo thoáng qua vs Lỗi thật)
- Cảnh báo như `Máy M<N>: verify dialog not dismissed` hoặc `transient issues recovered` thường là log giữa chừng khi máy gặp captcha/popup nhưng script đã tự dismiss hoặc tự phục hồi sau đó.
- **Quy trình kiểm tra:**
  1. Chạy O(1): `python D:/Taadaa/tools/inspect_machine.py <N>` xem focus hiện tại (nếu là Launcher Home thì phiên đã kết thúc an toàn).
  2. Đọc `recovery_lock_handoff.json` và dòng cuối của `summary.txt` trên máy đó. Nếu `final_status == success` và `lock_status == released` thì máy đã hoàn thành tốt, không cần can thiệp.

---

## 5. Taxonomy Label Batch Alert ≠ Lỗi Đồng Nhất

> **Xem chi tiết + ví dụ thực tế:** `references/batch-alert-log-triage-2026-09-21.md`

Alert `detector-miss:network/error/retry` là label taxonomy watchdog tổng hợp, KHÔNG phải lỗi đồng nhất.  
Đọc `run_manifest.json` → `machines[]` → từng `blocker_type` + `stop_reason` để biết nguyên nhân thật của từng máy.

Ví dụ: 1 alert nhưng machines có 5 loại khác nhau (network spike, splash ad, unknown state, proxy-vpn, ADB offline).

## 4. Tách Biệt Lỗi Phần Cứng Mất ADB vs Lỗi Logic Script
- Nếu `run_manifest.json` ghi nhận `device offline or ADB/USB disconnected: adb.exe: device '<serial>' not found`:
  - Đây là lỗi vật lý (lỏng cáp USB, hub USB ngắt điện, hoặc điện thoại sập nguồn).
  - Báo cáo rõ danh sách máy mất ADB vật lý để xử lý cắm lại, tránh dispatch sửa code nhầm hướng.
