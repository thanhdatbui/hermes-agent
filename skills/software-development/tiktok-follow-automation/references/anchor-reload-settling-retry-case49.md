# Case UI-49: Anchor Reload Settling Retry Polling to Prevent False Identity Mismatch

## 1. Triệu chứng & Bối cảnh
- **Farm Alert:** `[MÁY 7] DỪNG PHIÊN`
- **Quy trình:** `tiktok-follow` Mode 2 (follow followers của anchor)
- **Triệu chứng:** `hồ sơ identity mismatch sau khi reload (missing_header_handle) — từ chối tap Following`
- **Hiện trường:** Giữ hiện trường follow trên máy target.

## 2. Root Cause Analysis
1. Trong Mode 2 (`follow_runner/flows/mode2_follow_followers.py` -> `_open_following_tab`):
   - Trước khi vào xem Following list của anchor, nếu anchor chưa được follow thì runner gọi `_ensure_anchor_followed`.
   - Hàm này bấm follow anchor rồi thực hiện pull-to-refresh (`pull_to_refresh_profile`).
   - Sau cú vuốt pull-to-refresh, UI trên điện thoại trải qua hiệu ứng cuộn quán tính / spring-back settling animation.
   - Trong thời gian này, tọa độ `top_y` của node `@uid` trên header profile tạm thời bị trôi xuống `top_y >= 650`.
2. Hàm `_find_header_handle_node` có bộ lọc an toàn giới hạn vùng header:
   - `if top_y is None or top_y >= 650: continue`
   - Khi node `@uid` nằm ở `top_y >= 650`, hàm bỏ qua node đó và trả về `(None, "missing_header_handle")`.
3. Code cũ kiểm tra ngay lập tức trên bản dump XML duy nhất sau reload (`ensured_xml`):
   - Không có vòng lặp chờ UI ổn định (settling lag).
   - Nếu bản dump đầu tiên dính lag, code lập tức kết luận sai lệch danh tính:
     `reason_holder.append(f"hồ sơ identity mismatch sau khi reload ({status}) — từ chối tap Following")`
   - Dẫn đến dừng phiên fail-closed giả dù nick anchor hoàn toàn đúng.

## 3. Canonical Fix Pattern
Trong `_open_following_tab`, khi `ensured_xml != profile_xml`:
Triển khai bounded settling retry polling loop dựa theo cấu hình `verify_reload_retries` (mặc định 2 lần retry, tổng `settle_attempts = max(1, retries + 1)`):

```python
    if ensured_xml != profile_xml:
        profile_xml = ensured_xml
        retries = int(getattr(engine.cfg, "verify_reload_retries", 2) or 2)
        settle_attempts = max(1, retries + 1)
        identity_ok = False
        status = "not_checked"

        for attempt in range(settle_attempts):
            if attempt > 0:
                time.sleep(1.0)
                try:
                    profile_xml = adapter.dump_ui()
                except FollowAdapterError:
                    continue
            profile_nodes = _parse_mode2_nodes(profile_xml)
            try:
                profile_identity = profile_identity_from_xml(_clean_xml_format_chars(profile_xml))
            except Exception as exc:
                logger.exception(
                    "profile_identity_from_xml reload error on %s (dump_len=%d, is_reload=True, attempt=%d): %s",
                    uid, len(profile_xml), attempt, exc
                )
                if attempt == settle_attempts - 1 and reason_holder is not None:
                    reason_holder.append(f"profile identity helper lỗi sau reload: {type(exc).__name__}: {exc}")
                continue

            identity_element = profile_identity.get("username_element")
            profile_handle = profile_identity.get("username", "")
            handle_node, status = _find_header_handle_node(profile_nodes, uid)
            if (profile_handle and identity_element is not None
                    and status == "ok"
                    and target_normalized == _normalize_handle(profile_handle)):
                identity_ok = True
                break

        if not identity_ok:
            if reason_holder is not None:
                reason_holder.append(f"hồ sơ identity mismatch sau khi reload ({status}) — từ chối tap Following")
            return False
```

## 4. Invariants & Guardrails
1. **Bounded Polling:** Số lần thử tối đa được khống chế bởi `verify_reload_retries + 1` (tổng 3 attempts), không dùng vòng lặp vô hạn hay sleep mù.
2. **Re-dump Fresh UI:** Ở mỗi retry (`attempt > 0`), bắt buộc gọi `adapter.dump_ui()` mới để thu thập UI sau khi hoàn tất animation.
3. **Strict Fail-Closed:** Nếu sau toàn bộ số lần thử mà danh tính vẫn không khớp hoặc thiếu handle, bắt buộc fail-closed trả về `False` và ghi chi tiết lý do vào `reason_holder`. Tuyệt đối không bấm mở tab Following bừa bãi.
4. **Regression Test:** Test `test_open_following_tab_reloads_and_recovers_from_transient_missing_header_handle` trong `test_mode2_follow_followers.py` kiểm tra cả 2 nhánh: phục hồi thành công khi UI settle ở attempt 1 và fail-closed khi lỗi kéo dài.
