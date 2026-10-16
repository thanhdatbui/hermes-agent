# Mode 2 Follower Button Semantic Fallback & Obfuscation Recovery

## 1. Bản chất vấn đề & Triệu chứng
- **Triệu chứng Watchdog:** Phiên follow báo cáo `Bỏ qua: Đã follow sẵn (N)`.
- **Nguyên nhân gốc rễ:**
  1. Module 2 (Follow qua list Following của Anchor) bị degrade sớm do lỗi `MANUAL_REVIEW: follower row không có nút follow semantic`.
  2. Khi Module 2 gặp lỗi UI (nhưng không bị TikTok khóa tính năng/nhả follow), hệ thống tự động degrade sang Module 1 để search bù nick farm an toàn.
  3. Tuy nhiên, các nick an toàn trong danh sách Module 1 thường đã được follow ở các phiên trước, dẫn đến việc bị skip hàng loạt với lý do `đã follow sẵn`.
  4. Lỗi `follower row không có nút follow semantic` xảy ra khi TikTok cập nhật app hoặc obfuscate resource-id của nút quan hệ ("Follow", "Follow lại", "Bạn bè", "Đang theo dõi"). Cũ: `id/tcj`, `id/u2f`, `id/u68`... Khi id mới xuất hiện (ví dụ `id/new_unknown_btn`), bộ lọc gán nút `_cluster_follower_rows` trả về `follow_button = None`, kích hoạt fail-closed `missing_button_rows`.

## 2. Giải pháp kỹ thuật chuẩn hóa (Multi-Tier Fallback)
Không phụ thuộc 100% vào tuple cứng `FOLLOWER_FOLLOW_BUTTON_RESOURCE_IDS`. Triển khai cơ chế 2 tầng trong `_is_follow_button_node(n)`:

```python
_RELATION_BUTTON_TEXTS = frozenset(
    t.casefold() for t in (FOLLOW_BUTTON_TEXT + FOLLOW_BACK_TEXT + FOLLOWED_TEXT)
)

def _is_follow_button_node(n: dict) -> bool:
    if not isinstance(n, dict) or not n.get("clickable") or not n.get("bounds"):
        return False
    # Tầng 1: Khớp resource-id đã biết
    if (n.get("resource_id") or "").rstrip("/").endswith(FOLLOWER_FOLLOW_BUTTON_RESOURCE_IDS):
        return True
    # Tầng 2: Semantic text / content-desc fallback dựa trên vị trí bên phải màn hình
    try:
        semantic = (n.get("text") or n.get("content_desc") or "").strip().casefold()
        matched = bool(n["bounds"][0] >= 450 and semantic in _RELATION_BUTTON_TEXTS)
        if matched:
            global SEMANTIC_FALLBACK_COUNT
            SEMANTIC_FALLBACK_COUNT += 1
            logger.info(
                "[MODE2_TELEMETRY] event=follow_button_semantic_fallback count=%d text=%r content_desc=%r bounds=%s",
                SEMANTIC_FALLBACK_COUNT, n.get("text"), n.get("content_desc"), n.get("bounds"),
            )
        return matched
    except (KeyError, TypeError, AttributeError):
        return False
```

## 3. Quy tắc áp dụng đồng bộ
- Bắt buộc dùng `_is_follow_button_node(n)` ở cả 2 vị trí:
  1. `_cluster_follower_rows`: gom cụm `button_nodes`.
  2. `_follow_button_for_row`: tìm nút follow tương ứng cho một username row cụ thể.

## 4. Lưu ý khi chạy Closeout Gate / Test Suite
- Trong các mock unit test liên quan tới recovery loop (`test_run_mode2_reproves_feed_after_recovery_before_search_retry`), BẮT BUỘC mock `time.sleep` thành no-op (`monkeypatch.setattr(flow.time, "sleep", lambda s: None)`), tránh để test chạy thực tế gây timeout 120s trong Closeout Gate pipeline.
- Bổ sung unit test kiểm chứng cả hai trường hợp nút chỉ có `content-desc` (không có `text`) và trường hợp text semantic.
