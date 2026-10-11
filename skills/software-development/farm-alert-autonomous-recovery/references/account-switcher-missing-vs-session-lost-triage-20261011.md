# Triage Quy Trình: [ACCOUNT_SWITCHER_FAILED] ACCOUNT_MISSING vs Mất Phiên / Văng Account (False Alarm Triage)

**Ngày ghi nhận:** 11/10/2026  
**Ngữ cảnh áp dụng:** Khi nhận Farm Alert P0 dạng:
`⚠️ [P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]: Máy Mxx: UploadHook/FeedSession: [ACCOUNT_SWITCHER_FAILED] select account failed: ACCOUNT_MISSING: expected account was not found.`

---

## 1. Cơ Chế Lỗi & Nguyên Nhân Gốc Rễ (False Alarm Mechanism)

### Bản chất:
- Khi một máy nuôi nhiều tài khoản TikTok (theo các ca / slot Tik 1 -> Tik 8):
  - Máy đang mở ở nick của ca trước (ví dụ slot Tik 6 `@julesuqi6h4`).
  - Ca mới (ví dụ Ca 1 - Tik 1 `muyduyen4589`) yêu cầu chuyển đổi tài khoản (Account Switcher).
- Runner thực hiện tap vào tiêu đề profile (Header anchor, ví dụ tọa độ `(240, 322)` tương ứng với `bounds="[36,280][444,364]"`).
- **Lỗi xảy ra tại UI anchor tap:**
  - Trên TikTok (đặc biệt v47.x Samsung S7), menu bottom-sheet/dropdown danh sách tài khoản **không bung ra** (`stop_reason: manual-needed:account-switcher-not-open: profile screen remained after switch-anchor tap`).
  - Màn hình vẫn ở nguyên trang Profile cá nhân của nick hiện tại.
- **Dây chuyền phán đoán sai:**
  - Script chuyển sang bước vuốt tìm tên tài khoản mục tiêu (`muyduyen4589`).
  - Do bottom-sheet chưa mở, UI không có danh sách tài khoản -> Sau 3 lần swipe, script văng `ACCOUNT_MISSING: expected account was not found`.
  - Watchdog bắt chuỗi lỗi `ACCOUNT_MISSING` và lập tức kích hoạt cảnh báo `P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT`.
- **Thực tế:** Nick không hề bị văng, không bị logout, không bị checkpoint hay ban. Phiên đăng nhập của tài khoản hiện tại và các tài khoản trong máy vẫn hoàn toàn nguyên vẹn.

---

## 2. Quy Trình Khảo Sát T0 Bắt Buộc (Evidence-First Verification)

1. **Kiểm tra thông số máy O(1):**
   ```bash
   python D:/Taadaa/tools/inspect_machine.py <N>
   ```
   Xác nhận serial máy, trạng thái pin, màn hình awake và Wi-Fi.

2. **Truy vết Artifact & Run Directory O(1):**
   - Đọc kết quả trong `D:/Taadaa/runtime/kibe/live/<YYYY-MM-DD>/row-X-xxxxxx/<run_id>/machines/machine_<N>/<run_id>/upload_result.json` hoặc `summary.txt`.
   - Tìm thư mục run chi tiết trong `D:/CodexRuntime/tiktok-video/runs/run_<serial>_<timestamp>/`.
   - Tìm file ảnh snapshot hiện trường lúc cố gắng switch: `account-switcher-profile.png` hoặc `artifacts/.../screen.png`.

3. **Soi mắt kiểm chứng (Invariant Vision Mandatory):**
   - Mở ảnh qua `browser_vision` (hoặc WinRT OCR) để xác nhận màn hình:
     - Nếu màn hình là **Tab Hồ sơ có avatar, username, video, follower** -> **100% FALSE ALARM**, nick vẫn sống và đang đăng nhập bình thường.
     - Nếu màn hình là **Guest Profile** (nút "Đăng ký / Đăng nhập"), màn hình đen, hoặc thông báo vi phạm/bị khóa -> Mới là mất phiên thật sự.

---

## 3. Kỷ Luật Điều Phối & Phục Hồi (Recovery & Governance)

1. **Tuyệt đối cấm thao tác mù:**
   - CẤM bấm tay ADB (`input tap`, `input keyevent`) để chữa cháy tạm bợ.
   - CẤM vội vàng xóa tài khoản, đổi password, đổi mail hay chuyển nick sang trạng thái DIE.
2. **Device Lock Invariant:**
   - Mọi lệnh tương tác ADB với thiết bị bắt buộc bọc qua device lock:
     ```bash
     python D:/Taadaa/tools/with_device_lock.py --machine <N> -- <adb_cmd>
     ```
3. **Phân loại lỗi & Xử lý:**
   - Lỗi này thuộc về **UI Switcher Anchor Reliability** (tọa độ tap hoặc nhịp trễ animation mở bottom sheet trên TikTok v47.x), KHÔNG PHẢI lỗi tài khoản.
   - Báo cáo rõ ràng hiện trạng kèm ảnh `MEDIA:` đã soi mắt cho User.
   - Đánh giá batch: Nếu xảy ra rải rác khi chuyển ca, hệ thống sẽ tự reconcile ở các phiên tiếp theo hoặc trong đợt bảo trì hook UI Switcher.
