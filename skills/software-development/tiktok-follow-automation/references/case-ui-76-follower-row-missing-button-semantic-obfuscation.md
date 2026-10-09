# Case UI-76: Follower Row Missing Button Semantic Obfuscation Recovery (`MANUAL_REVIEW`)

## 1. Hiện trường sự cố (Farm Alert Ca 1 Sáng 25/09/2026)
- **Cảnh báo diện rộng:** 21 máy đồng loạt dừng phiên Follow TikTok Mode 2 với cùng lý do:
  - Máy bị ảnh hưởng: M7, M8, M12, M24, M26, M29, M31, M37, M38, M39, M42, M44, M46, M48, M49, M50, M58, M59, M62, M63, M70.
- **Triệu chứng log (`follow_result.json`):**
  ```json
  {
    "status": "MANUAL_REVIEW",
    "reason": "MANUAL_REVIEW: follower row không có nút follow semantic",
    "followed_count": 0,
    "failed": 1,
    "follow_failed": false
  }
  ```

---

## 2. Bản chất kỹ thuật & Cơ chế Fail-Closed
Trong `follow_runner/flows/mode2_follow_followers.py`:
```python
missing_button_rows = [
    r for r in rows
    if r["follow_button"] is None
    and _normalize_handle(r.get("handle", "")) != active_account
    and not state.is_followed(r.get("handle", ""))
    and not state.is_skipped(r.get("handle", ""))
    and _normalize_handle(r.get("handle", "")) not in session_external_seen
    and not _is_top_cutoff_row(r, top_cutoff_y)
    and not _is_bottom_cutoff_row(r, bottom_cutoff_y)
]
if missing_button_rows:
    res.status = "MANUAL_REVIEW"
    res.reason = "MANUAL_REVIEW: follower row không có nút follow semantic"
    failed = True
    break
```
- **Ý định ban đầu:** Bảo vệ tài khoản tránh tap mù/sai tọa độ khi layout danh sách người theo dõi bị lỗi hoặc thiếu nút follow.
- **Nguyên nhân kích hoạt hàng loạt trên farm:**
  1. **Selector Drift / Obfuscation mới:** TikTok cập nhật mã nguồn làm thay đổi resource-id hoặc cấu trúc node của nút follow (tiếp sau các đợt đổi `id/u2f`, `id/u68`...).
  2. **Thẻ gợi ý / Header / Card danh bạ xen kẽ:** Các card gợi ý bạn bè, liên kết danh bạ, hoặc header nhóm ("Gợi ý cho bạn", "Gần đây") có chứa text giống user handle nhưng không mang nút follow semantic chuẩn (`r["follow_button"] is None`).
  3. **Row bị che khuất hoặc cắt biên một phần:** Không lọt vào ngưỡng `top_cutoff_y` hoặc `bottom_cutoff_y` chuẩn khiến bộ lọc gom nhầm vào `missing_button_rows`.

---

## 3. Quy trình chẩn đoán & Xử lý chuẩn (Coordinator & Worker)
1. **Trích xuất XML hiện trường O(1):**
   - Đọc trực tiếp file XML dump tại artifact của máy bị lỗi:
     `D:/Taadaa/runtime/kibe/live/<DATE>/<RUN>/machines/machine_<M>/<RUN>/artifacts/.../follower_list.xml`
     hoặc chạy:
     `python D:/Taadaa/tools/inspect_machine.py <M>`
2. **Xác định Node gây lỗi:**
   - Dùng script Python focused parse danh sách row và in ra node nào có `follow_button is None`:
     - Kiểm tra text, content-desc, bounds, và class của node đó.
     - Phân loại: Do nút bấm bị đổi resource-id (cần bổ sung vào `FOLLOWER_FOLLOW_BUTTON_RESOURCE_IDS`) hay do thẻ rác/gợi ý/header (cần bổ sung điều kiện loại trừ).
3. **Cập nhật Code (`tiktok-follow`):**
   - Nếu là Selector Drift: Cập nhật tuple `FOLLOWER_FOLLOW_BUTTON_RESOURCE_IDS` trong `follow_runner/core/selectors.py`.
   - Nếu là Card gợi ý/Banner: Bổ sung regex hoặc text exclusion trong `_cluster_follower_rows()` và `missing_button_rows`.
4. **Kiểm thử Canary trước khi áp dụng toàn Farm:**
   - Chạy canary trên 1 máy thật (ví dụ Máy 7 hoặc 12) với cờ `--skip-identity-verify`:
     `powershell.exe -ExecutionPolicy Bypass -File D:/Taadaa/tiktok-follow/scripts/run-follow.ps1 -Machine 7 -AccountRow 1 -DryRun`
   - Kiểm tra output log xác nhận `missing_button_rows` = 0 và follower list được duyệt bình thường.
