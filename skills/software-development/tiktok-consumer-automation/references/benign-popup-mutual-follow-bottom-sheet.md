# TikTok Benign Popup: Mutual Follow ("Đã follow chung") Bottom Sheet

## Overview
When browsing feeds or interacting with profiles, TikTok presents a bottom sheet suggesting mutual follow accounts ("Đã follow chung" / "Follow chung"). Unlike standard full-screen dialogs or alert modals, this bottom sheet has specific characteristics:

1. **Title / Header Text**:
   - `Đã follow chung`, `Follow chung` (may have prefix variations like `Đã follow chung ...`).
   - Must be registered in both `flows/benign_popup_registry.py` and `flows/benign_popup.py`.

2. **Close Button Detection (`_find_follow_friends_semantic_close_control`)**:
   - Standard close controls look for text/desc in `{"đóng", "close", "✕", "x"}` or resource IDs ending in `:id/c3t`, `:id/e63`, `:id/e8c`.
   - In mutual follow bottom sheets, the close icon is often an unnamed `ImageView` or `ImageButton` located at the header's upper-right corner:
     ```python
     is_sheet_header_close = (
         el.attrib.get("class") in {"android.widget.ImageView", "android.widget.ImageButton"}
         and t_bounds is not None
     )
     if (
         text in {"đóng", "close", "✕", "x"}
         or desc in {"đóng", "close", "✕", "x"}
         or any(rid.endswith(s) for s in (":id/c3t", ":id/e63", ":id/e8c"))
         or is_sheet_header_close
     ) and clickable:
         b = parse_bounds(el.attrib.get("bounds", ""))
         if not b:
             continue
         width = b[2] - b[0]
         height = b[3] - b[1]
         if is_sheet_header_close and b[0] >= 800 and t_bounds is not None and abs(b[1] - t_bounds[1]) <= 150:
             return el
         if b[0] >= 50 and width >= 30 and height >= 30:
             if t_bounds is not None:
                 if abs(b[1] - t_bounds[1]) <= 600 and b[0] >= t_bounds[0] - 100:
                     return el
             else:
                 return el
     ```

3. **Title Node Resolution**:
   - When resolving `title_node`, ensure matchers inspect both exact set matches and prefix matches:
     ```python
     title_node = next(
         (
             el for el in elements
             if (el.attrib.get("text") or "").strip().casefold() in {
                 "follow bạn bè của bạn", "follow your friends", "gợi ý follow",
                 "follow bạn", "bạn bè với", "người bạn có thể biết", "gợi ý tài khoản",
                 "bạn bè của bạn", "kết nối với bạn bè",
             }
             or (el.attrib.get("text") or "").strip().casefold().startswith(("đã follow chung", "follow chung"))
             or (el.attrib.get("content-desc") or "").strip().casefold().startswith(("đã follow chung", "follow chung"))
         ),
         None,
     )
     ```
