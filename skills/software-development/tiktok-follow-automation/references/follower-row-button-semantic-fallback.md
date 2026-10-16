# Case Fix: Follower Row Relation Button Semantic Fallback & Obfuscation Recovery

## 1. Bối cảnh & Hiện tượng (Symptom)
- Trong phiên nuôi follow Mode 2 (Anchor Following), Watchdog Telegram báo cáo hàng loạt máy kết thúc với:
  `Bỏ qua: Đã follow sẵn (N)` hoặc `Lỗi script/xác minh: Lệch layout nút Follow`.
- Trong file `follow_result.json`:
  ```json
  "mode2_degraded": true,
  "mode2_degraded_reasons": ["MANUAL_REVIEW: follower row không có nút follow semantic"]
  ```
- **Hệ quả dây chuyền:** Mode 2 gặp cờ này tưởng nhầm layout bị vỡ hoặc màn hình lỗi ➔ Huỷ ngang Mode 2 ➔ Degrade sang Mode 1 (Search). Mode 1 tìm kiếm các tài khoản an toàn trong danh sách farm nhưng hầu hết các nick này đã được follow từ các ca trước ➔ Báo cáo ngập tràn "Đã follow sẵn", không follow thêm được nick nào từ list 150-300 following của anchor.

## 2. Nguyên nhân gốc rễ (Root Cause)
1. **Khớp cứng Resource-ID:** Trong `_cluster_follower_rows` và `_follow_button_for_row`, runner chỉ gán nút follow vào cụm hàng nếu resource-id khớp với tuple cứng `FOLLOWER_FOLLOW_BUTTON_RESOURCE_IDS` (`tcj`, `thb`, `u2f`, `u68`, `ubp`...).
2. **TikTok Obfuscation / Version Drift:** Khi TikTok nâng cấp (v46.x -> v47.x), TikTok đổi resource-id của nút quan hệ (hoặc id động).
3. **Fail-Closed quá cứng nhắc:** Khi `_cluster_follower_rows` không bắt được button node, hàng vẫn nhận diện được handle (từ `txt_desc` hoặc `txt_user_name`), nhưng `r["follow_button"] = None`. Bộ lọc `missing_button_rows` phát hiện nick farm không có nút bấm ➔ Kích hoạt `MANUAL_REVIEW: follower row không có nút follow semantic` và ngắt vòng lặp anchor.

## 3. Kiến trúc Giải pháp Chuẩn (Two-Tier Button Binding)
Trong `mode2_follow_followers.py`, triển khai hàm nhận diện nút `_is_follow_button_node(n)` theo 2 tầng:

```python
_RELATION_BUTTON_TEXTS = frozenset(
    t.casefold() for t in (FOLLOW_BUTTON_TEXT + FOLLOW_BACK_TEXT + FOLLOWED_TEXT)
)

def _is_follow_button_node(n: dict) -> bool:
    if not n.get("clickable") or not n.get("bounds"):
        return False
    # Tầng 1: Khớp Resource-ID đã biết
    if (n.get("resource_id") or "").rstrip("/").endswith(FOLLOWER_FOLLOW_BUTTON_RESOURCE_IDS):
        return True
    # Tầng 2: Fallback theo vị trí cột bên phải và Text/Content-desc quan hệ
    matched = bool(
        n["bounds"][0] >= 450
        and (n.get("text") or n.get("content_desc") or "").strip().lower() in _RELATION_BUTTON_TEXTS
    )
    if matched:
        logger.info(
            "[MODE2_TELEMETRY] event=follow_button_semantic_fallback text=%r bounds=%s",
            n.get("text"), n.get("bounds")
        )
    return matched
```

- Áp dụng `_is_follow_button_node(n)` đồng bộ cho cả `button_nodes` trong `_cluster_follower_rows` và hàm lookup `_follow_button_for_row`.

## 4. Pitfall Kiểm thử & Closeout Gate
- **Pitfall timeout 120s trong Pytest:** Khi viết unit test giả lập nhiều vòng lặp (`run_mode2`, `_back_to_feed`), nếu không monkeypatch `flow.time.sleep`, các khoảng nghỉ tự nhiên (1.0s - 3.5s) sẽ tích lũy khiến toàn bộ suite vượt ngưỡng 120s và làm Closeout Gate đánh fail.
- **Quy tắc bắt buộc:** Mọi test giả lập mock boundaries BẮT BUỘC chèn:
  ```python
  monkeypatch.setattr(flow.time, "sleep", lambda seconds: None)
  ```
- **Hậu kiểm Numstat:** Luôn giữ bản vá O(1) <= 30 dòng theo đúng chuẩn Emergency Surgery.
