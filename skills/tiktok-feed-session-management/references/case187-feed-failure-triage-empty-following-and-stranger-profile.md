# Case 187: Triage 5 Cụm Lỗi Feed Session Farm & Cơ Chế Soft-Fallback (23/09/2026)

## Hiện Tượng & Tỷ Lệ Fail Bất Thường
- Ca trưa Row 3 (14:03, 80 máy): 57 máy thành công (~71.25%), 23 máy không thành công (~28.75%), tiệm cận ngưỡng RED ALERT 30% của Watchdog.
- Không phải do một lỗi duy nhất mà do 4 cụm lỗi logic runner cộng hưởng với lỗi hạ tầng phần cứng.

## Bóc Tách 5 Cụm Lỗi Cốt Lõi & Chữ Ký Nhận Diện

### 1. Tab "Following" Rỗng / False Positive Network Error (M33, M41, M70, M72, M75)
- **Log Signature:**
  - `switch_following_<N>_navigation_confirm` -> `network/error/retry marker detected` -> `manual-needed:network`.
  - Thiết bị đã lướt mượt mà 3–8 video For You, nhưng dừng ngay lập tức khi chuyển sang tab Following.
- **Root Cause:**
  - Nick mới follow ít tài khoản hoặc các nick đang follow chưa đăng bài mới trong 24h. TikTok hiển thị giao diện rỗng hoặc nút "Thử lại / Không có video".
  - Script nhận diện nhầm marker UI này là lỗi rớt mạng nghiêm trọng và abort toàn bộ session.
- **Chuẩn Fix:**
  - Khi gặp màn hình rỗng hoặc retry marker ở tab Following: Ghi nhận trạng thái degraded, soft-fallback quay lại tab "Dành cho bạn" (FYP) để hoàn thành đủ quota swipe (16–22 video) thay vì ngắt cả phiên.

### 2. Kẹt Profile Người Lạ Do Pop-up Đề Xuất Bạn Bè / Follow Back (M17, M23, M25, M76)
- **Log Signature:**
  - `feed-session-smoke/tap_profile` -> `find_navigation_target: not-found` -> `navigation target profile not found in XML` -> `manual-needed` (0 swipes).
- **Hiện trường XML & UI:**
  - Màn hình chứa: `Follow lại`, `Nhắn tin`, `Bạn bè với ...`. Thanh điều hướng đáy không có nút "Hồ sơ" chính chủ.
  - Các tài khoản lạ: `@tolmavhj12k` (M17), `@thanh.h.dng00` (M23), `@hoanghan27093` (M25), `@ngc.trinh6472` (M76).
- **Root Cause:**
  - Pop-up gợi ý bạn bè hoặc follow-back xuất hiện lúc khởi động. Hành động chạm hoặc chuyển hướng của app đưa user vào trang cá nhân của người khác.
  - Runner tìm nút "Hồ sơ" để preflight profile nhưng không tìm thấy vì đang ở profile người lạ, đồng thời logic an toàn chặn `KEYCODE_BACK` vì tưởng đang ở feed.
- **Chuẩn Fix:**
  - Thêm Foreign Profile Guard: Phát hiện nút "Follow lại" / "Nhắn tin" kết hợp thiếu "Sửa hồ sơ" / "Thêm tiểu sử" -> bấm `KEYCODE_BACK` để thoát về Home feed.

### 3. Drift Thị Giác vs XML Ở Profile Preflight (M14, M42)
- **Log Signature:**
  - `xml_detected_screen: profile`, `image_selected_top_tab: following`, `screenshot_xml_mismatch: true`.
  - Kết quả: `safety_reason: known TikTok screen`, `status: manual-needed` (0 swipes).
- **Root Cause:**
  - Máy đã ở đúng Profile chính chủ (`@nguyenlinh04011`, `@danielbsteve01`).
  - Image classifier nhận diện nhầm đường nét trang trí của header profile thành underline tab "Following", ghi đè kết quả phân loại XML và rơi vào vòng lặp retap liên tục.
- **Chuẩn Fix:**
  - XML Precedence Rule: Khi XML đã có các thuộc tính xác thực profile chắc chắn (`profile_selected: true` hoặc có username + "Sửa hồ sơ"), cấm image top-tab classifier ghi đè thành Following.

### 4. Switcher Thiếu Nick & Subprocess Reconcile Timeout (M32)
- **Log Signature:**
  - `manual-needed:account-switcher-missing-expected: expected account not found in account switcher`.
  - Subprocess `reconcile_tiktok_accounts.py` timeout sau 300.0s.
- **Root Cause:** Nick trong workbook chưa có trên máy thật; script đăng nhập tự động chạy vượt quá timeout budget 300s.

### 5. Rớt Kết Nối Phần Cứng & Wi-Fi
- **Log Signature:**
  - M5, M71, M74, M79: `device offline or ADB/USB disconnected`.
  - M46, M56: `Wi-Fi not connected` qua `dumpsys connectivity`.
- **Root Cause:** Lỗi vật lý cáp USB hub hoặc rớt sóng Wi-Fi AP, không can thiệp bằng code.

---

## 3 Patch Contracts Chi Tiết (Implementation Standard)

### Contract 1: `python_runner/core/classifier.py`
Xử lý triệt để bẫy profile người lạ và loại bỏ nhầm lẫn giữa nút "Đã follow" trên profile và tab Following trên feed:
1. **Anchor 1A (Loại trừ action button khỏi username):**
   Thêm `"follow lại"`, `"follow back"` vào set loại trừ để không bóc nhầm nút kết bạn thành tên user:
   ```python
   and label(element) not in {"follow", "nhắn tin", "message", "đã follow", "đang follow", "follow lại", "follow back"}
   ```
2. **Anchor 1B (Bổ sung action buttons nhận diện profile):**
   ```python
   and label(element) in {"follow", "nhắn tin", "message", "đang follow", "đã follow", "follow lại", "follow back"}
   ```
3. **Anchor 1C (Loại bỏ "Đã follow" khỏi feed tab following_terms):**
   Nút "Đã follow" xuất hiện trên profile người mà nick đang theo dõi, KHÔNG phải tên tab Following trên top feed header:
   ```python
   following_terms = (
       "Following",
       "\u0110ang Follow",
       "\u00c4\u0090ang Follow",
   )
   ```

### Contract 2: `python_runner/flows/calibrate_screens.py`
Chặn đứng `calibrate_screens` phân loại nhầm trang profile người lạ thành home/feed sạch:
- Kiểm tra `is_foreign_profile`:
  ```python
  is_foreign_profile = any(
      (el.attrib.get("text") or "").strip() in {"Follow lại", "Nhắn tin", "Follow back", "Message"}
      for el in current_root.iter()
  ) if current_root is not None else False
  ```
- Thêm điều kiện `and not is_foreign_profile` trước khi gán `is_home_or_feed = True` cho cả 2 nhánh (screen name khớp hoặc selected markers khớp).

### Contract 3: `python_runner/flows/feed_swipe_smoke.py`
1. **Anchor 3A (`_profile_guard_drifted_from_profile`):**
   Bảo vệ trạng thái profile khi XML đã xác nhận đang ở profile chính chủ, ngăn logic ngộ nhận là đã drift về home:
   ```python
   def _profile_guard_drifted_from_profile(row: dict[str, Any]) -> bool:
       if _profile_identity_from_profile_attempt(row) is not None:
           return False
       attempts = row.get("attempts") or []
       if any(isinstance(att, dict) and att.get("xml_detected_screen") == "profile" for att in attempts):
           return False

       detected = str(row.get("detected") or "")
       if detected not in {"home", FEED_TYPE_FOR_YOU, FEED_TYPE_FOLLOWING, FEED_TYPE_FRIENDS, "unknown"}:
           return False
   ```
2. **Anchor 3B (Soft-fallback khi gặp màn hình rỗng/lỗi mạng ảo trên tab Following/Friends):**
   *Quy tắc điều phối bất biến (User correction 2026-09-23):*
   - **CẤM** tự ý bỏ qua tab Following từ đầu hoặc ép tỷ lệ 0%. Bot vẫn BẮT BUỘC bấm vào tab Following theo đúng chu trình tự nhiên.
   - Khi vào tab Following, nếu gặp màn hình rỗng hoặc thông báo mạng ảo do chưa follow ai, bot **tuyệt đối không ngắt phiên**, mà tự động tap quay về tab "Dành cho bạn" (For You) và tiếp tục lướt hoàn thành đủ quota:
   ```python
   if manual_guard.record(_safety_from_row(ctx, confirm)):
       if next_feed_type in {FEED_TYPE_FOLLOWING, FEED_TYPE_FRIENDS} and confirm.get("detected") in {"manual-needed:network", "manual-needed:empty", "manual-needed:retry"}:
           ctx.logger.log(
               device_id=ctx.device_id,
               account=ctx.account,
               step=f"{artifact_prefix}/switch_{next_feed_type}_{swipe_count}_empty_feed_fallback_for_you",
               action="fallback_feed_tab",
               result="warning",
               extra={"failed_target": next_feed_type, "fallback_target": FEED_TYPE_FOR_YOU, "reason": "empty_following_or_network_marker_fallback_to_for_you"},
           )
           # Graceful fallback: Tap back to For You feed and continue session quota
           tap_navigation_target(
               ctx,
               _top_tab_target(FEED_TYPE_FOR_YOU),
               current_top_tab=next_feed_type,
               artifact_prefix=artifact_prefix,
               log_prefix=artifact_prefix,
           )
           current_feed_type = FEED_TYPE_FOR_YOU
           next_feed_type = FEED_TYPE_FOR_YOU
           confirm["status"] = ExitStatus.DEGRADED.value
           confirm["safety_status"] = "ok"
           videos_until_tab_decision = random.randint(5, 10)
       else:
           results.append(confirm)
           _store_partial_result(ctx, results, max_swipes, **result_kwargs)
           return finalize_feed_session_cleanup(...)
   ```

---

## Quy Trình Áp Patch & Kiểm Chứng (Execution & Test Standard)

### 1. Cạm bẫy thực thi (Pitfalls)
- **Bash `-c` multiline quote escaping:** Tránh gõ inline python `-c '...'` chứa cả nháy đơn `\'` và nháy kép trong terminal MSYS/bash trên Windows vì rất dễ vấp lỗi `/usr/bin/bash: -c: line X: unexpected EOF while looking for matching \'`.
- **Giải pháp chuẩn:** Dùng file script Python tạm độc lập (ví dụ `_apply_patch_case187.py`) hoặc dùng công cụ file edit (`write_file` / `patch`), sau đó chạy `python -m py_compile`.
- **Đường dẫn Windows với `search_files`:** `search_files` (ripgrep) có thể lỗi `os error 3` nếu truyền định dạng MSYS Unix `/d/Taadaa/...`. Nên dùng đường dẫn Windows chuẩn `D:\Taadaa\...` hoặc `read_file`.

### 2. Lệnh Kiểm Chứng Tập Trung
Sau khi áp 3 Patch Contracts và biên dịch `py_compile`, chạy test runner kiểm chứng duy nhất:
```bash
D:/Taadaa/python-envs/automation/Scripts/pytest "D:/Taadaa/tiktok-luot nuoi acc/python_runner/tests/test_classifier.py" -q
```
