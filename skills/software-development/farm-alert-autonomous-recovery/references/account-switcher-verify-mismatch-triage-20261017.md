# Triage Quy Trình: [ACCOUNT_SWITCHER_FAILED] ACCOUNT_VERIFY_MISMATCH vs Mất Phiên / Văng Account (False Alarm Triage)

**Ngày ghi nhận:** 17/10/2026  
**Ngữ cảnh áp dụng:** Khi nhận Farm Alert P0 dạng:
`⚠️ [P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]: Máy Mxx: UploadHook/FeedSession: [ACCOUNT_SWITCHER_FAILED] ACCOUNT_READY verify failed: ACCOUNT_VERIFY_MISMATCH: Profile did not show the expected account.`

---

## 1. Cơ Chế Lỗi & Phân Tích Hiện Trường (False Alarm Mechanism)

### Bản chất:
- Khi máy chuyển ca (ví dụ từ Ca Tik 5 `chungan981` sang Ca Tik 8 `phanlan097`):
  - Runner mở Account Switcher thành công (`[ACCOUNT_SWITCHER] Switcher opened via core ✓`).
  - Runner tìm thấy target account trong danh sách và tap chọn thành công (`[ACCOUNT_SWITCHER] Target account selected via core ✓`).
- **Hiện tượng nghẽn UI transition:**
  - Sau khi tap chọn tài khoản, TikTok hiển thị dialog loading trung gian (`com.ss.android.ugc.trill:id/tux_loading_hud`).
  - Quá trình reload Profile bị trễ hoặc animation chuyển context chưa hoàn tất trong khoảng thời gian `settle` ngắn.
  - Runner chuyển sang state `ACCOUNT_READY` và gọi `verify_selected_account(..., target_account)`.
  - Lúc này, UI Profile vẫn đang hiển thị thông tin và username của nick ca trước (`@chungan981`).
  - Runner ném ngoại lệ: `ACCOUNT_VERIFY_MISMATCH: Profile did not show the expected account`.
- **Dây chuyền cảnh báo sai lệch:**
  - Watchdog bắt chuỗi lỗi `ACCOUNT_SWITCHER_FAILED` và tự động gắn nhãn `⚠️ [P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]`.
  - Thực tế: Màn hình vẫn là trang Profile hợp lệ (có avatar, username, follower, lưới video), nick ca trước và target account đều đăng nhập nguyên vẹn trong app, không hề bị logout, checkpoint hay ban.

---

## 2. Quy Trình Khảo Sát T0 & Kiểm Chứng Bắt Buộc

1. **Khảo sát thiết bị O(1):**
   ```bash
   python D:/Taadaa/tools/inspect_machine.py <N>
   ```
2. **Truy vết Run Directory & Artifacts:**
   - Đọc `checkpoint.json` và `report.json` trong `D:/CodexRuntime/tiktok-video/runs/run_<serial>_<timestamp>/`.
   - Kiểm tra `popup_before.xml` để xác nhận có node `com.ss.android.ugc.trill:id/tux_loading_hud` hay không.
3. **Soi mắt kiểm chứng (WinRT OCR / Vision Invariant):**
   - Chạy WinRT OCR trên `account-switcher-profile.png` và `soft-reboot-account_ready-before.png`:
     * Nếu OCR thấy thông tin Profile đầy đủ (Follower, Đang follow, Thích) với username của ca trước -> **100% FALSE ALARM**.
   - BẮT BUỘC nạp qua `evidence_gate_verifier.py` trước khi đính kèm `MEDIA:` để tránh bị Evidence First Gate chặn:
     ```bash
     python D:/Taadaa/tools/evidence_gate_verifier.py --pre-image "<path_to_image>" --allow-single-inspection --max-age 86400
     ```

---

## 3. Kế Hoạch Xử Lý & Đề Xuất Kỹ Thuật

1. **Kỷ luật an toàn tuyệt đối:**
   - CẤM bấm tay ADB trên máy.
   - CẤM xóa tài khoản hoặc đánh dấu DIE trên Excel / database.
2. **Khắc phục tầng Core (Root Cause Fix):**
   - Tăng `settle` sau `select_exact_account` từ `0.75s` lên `1.5s - 2.0s`.
   - Bổ sung bước đợi `tux_loading_hud` biến mất trước khi thoát khỏi switcher và bước vào `ACCOUNT_READY`.
   - Trong `verify_selected_account`, bổ sung polling nhẹ chờ Profile refresh sang username mới thay vì fail-fast ngay khi thấy username ca trước.
3. **Phục hồi ca chạy:**
   - Thiết bị sau soft reboot đã được dọn sạch về Home và nhả lock an toàn. Cho phép re-run đợt sau bình thường.
