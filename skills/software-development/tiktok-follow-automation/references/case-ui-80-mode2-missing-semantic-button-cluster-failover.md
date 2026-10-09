# Case UI-80: Phân Tích Toàn Bộ Fleet Dính 'follower row không có nút follow semantic' Trong Mode 2 & Cơ Chế Failover Mode 1

## 1. Hiện Tượng Thực Tế (User Telemetry 01/10/2026)
- **Triệu chứng:** Trong báo cáo tổng kết nuôi acc Ca 1 (Row 1):
  `• Follow chéo (53 lượt follow) [Module 2 (Anchor): 1 | Module 1 (Bù): 52]`
- **Vấn đề đặt ra:** Vì sao gần như 100% lượt follow thành công đều đến từ Module 1 (Search trực tiếp), trong khi Module 2 (Mở danh sách Following của nick Anchor Tik1/Tik2) chỉ chạy được đúng 1 lượt trên Máy 48 và fail toàn bộ trên các máy còn lại?

---

## 2. Root Cause Telemetry & Code Path Analysis

### A. Kiểm chứng Telemetry trên Dàn Máy
Kiểm tra toàn bộ các file `follow_result.json` tại `D:\Taadaa\runtime\kibe\live\2026-10-01\row-1-060101\*\machines\*\follow_result.json`:
- Toàn bộ các máy (M11, M12, M13, M25, M29, M32, M38, M40, M41, M42, M45, M46, M48, M49, M50, M51, M54, M57, M59, M61, M63, M66, M67, M71, M72...) đều mang cờ:
  ```json
  "details": {
    "mode2_degraded": true,
    "mode2_degraded_reasons": [
      "MANUAL_REVIEW: follower row không có nút follow semantic"
    ],
    "mode1_followed_count": N
  }
  ```
- Duy nhất Máy 48 kịp thực hiện follow 1 nick trước khi gặp lỗi này (`mode2_followed_count: 1`).

### B. Điểm nghẽn trong Code (`mode2_follow_followers.py`)
Tại hàm `run_mode2` (lines 2023–2037):
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

### C. Cơ chế dẫn đến Break liên hoàn:
1. **Lọc Fail-Closed quá ngặt nghèo:**
   - Trong danh sách Following của nick Anchor, luôn xuất hiện cả các tài khoản ngoài farm (external accounts) hoặc tài khoản bạn bè có cấu trúc layout / nút quan hệ khác (hoặc nút quan hệ mang resource-id chưa có trong whitelist `FOLLOWER_FOLLOW_BUTTON_RESOURCE_IDS`).
   - Hàm `_cluster_follower_rows` nếu không gán được nút cho dù chỉ **1 row** không thuộc whitelist (hoặc do khoảng cách `y` giữa username và display name vượt quá dung sai 25px khiến button bị coi là `ambiguous_button`), row đó sẽ có `r["follow_button"] is None`.
2. **Kích hoạt ngắt toàn bộ phiên Mode 2:**
   - Khi `missing_button_rows` không rỗng $\rightarrow$ `res.status = "MANUAL_REVIEW"`, `failed = True`, `break`.
   - Vòng lặp ngoài `for uid in uids:` kiểm tra `if failed: break` $\rightarrow$ Ngắt toàn bộ tất cả các anchor tiếp theo của Mode 2 trên máy đó ngay lập tức.

---

## 3. Hiệu Quả Của Cơ Chế Failover (Case UI-77 Bảo Vệ Sản Lượng)

Nhờ cơ chế Failover được thiết lập tại `follow_engine.py` (lines 854–862):
```python
if mode == "both" and res.status != STATE_OK and not res.follow_failed and not (self.state is not None and self.state.follow_failed):
    # Mode 2 gặp lỗi UI/anchor nhưng KHÔNG bị TikTok chặn follow (follow_failed=False).
    # Chuyển mode2_degraded=True và reset status về OK để Mode 1 tiếp tục chạy bù budget.
    res.details["mode2_degraded"] = True
    if res.reason:
        res.details.setdefault("mode2_degraded_reasons", []).append(res.reason)
    res.status = STATE_OK
    res.failed = False
    res.reason = ""
```
- Hệ thống nhận diện lỗi Mode 2 chỉ là lỗi phân tích giao diện UI (Degraded), **tuyệt đối không phạt hay khóa Cooldown nick**.
- Runner xóa cờ lỗi, chuyển giao toàn bộ chỉ tiêu follow còn lại sang cho **Mode 1**.
- Mode 1 tìm kiếm chính xác từng UID nội bộ qua ô Search, đưa toàn bộ 52 lượt follow về đích thành công.

---

## 4. Khuyến Nghị & Hướng Tối Ưu Hóa (Future Work)

1. **Phân rã kiểm tra nút theo phạm vi Internal vs External:**
   - Chỉ nên áp dụng điều kiện `missing_button_rows` gây `MANUAL_REVIEW` nếu row thiếu nút **thuộc về danh sách nick farm cần follow (`_normalize_handle(r.get("handle")) in internal_uids`)**.
   - Nếu row thiếu nút là nick ngoài farm (`not in internal_uids`), chỉ cần đưa vào `session_external_seen` và tiếp tục cuộn tìm nick farm, không ngắt phiên của anchor.
2. **Cập nhật Whitelist Resource ID:**
   - Tiếp tục theo dõi các biến thể layout mới của TikTok 46.x / 47.x đối với nút quan hệ (Bạn bè, Đang follow, Follow lại) trong danh sách Following.
