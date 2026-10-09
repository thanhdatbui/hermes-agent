# TikTok Obfuscated Video Grid & UI Drift (Case TikTok v46.8+)

## Hiện tượng
- User quan sát màn hình thấy bot search account, bấm vào profile, cuộn xuống thấy lưới video rõ ràng nhưng không bấm vào video nào mà back ra thoát app.
- File `follow_result.json` báo: `"reason": "anchor @<username> không có video — back ra bỏ qua"`.
- Trạng thái trả về `MANUAL_REVIEW`.

## Nguyên nhân gốc rễ
- TikTok v46.8.3+ đổi resource-id và layout của lưới video trên Profile.
- Bộ lọc `video_covers` trong `mode2_follow_followers.py` kiểm tra keyword cũ:
  ```python
  any(k in str(n.get("resource_id", "")).lower() for k in ("cover", "tv_play_count", "exx", "aweme"))
  ```
- Khi TikTok obfuscate hoặc đổi ID, danh sách `video_covers` trả về rỗng (`[]`).
- Video Gate kích hoạt cơ chế Safe-Skip: do không có video để mở xem an toàn (8-15s, tim 50-70%) nên không follow bừa ngoài profile, back ra và force-stop app.

## Bài học & Giải pháp kỹ thuật
1. Không phụ thuộc hoàn toàn vào keyword tĩnh trong `resource-id`.
2. Bổ sung fallback nhận diện thumbnail qua node cấu trúc lưới (`RecyclerView` con, tỷ lệ bounds khung hình video dạng 3 cột).
3. Giao tiếp khi user hỏi log: BẮT BUỘC trả lời bằng **tiếng Việt**, ngắn gọn, nêu rõ Máy N, Row N, Ca N, Acc nào và chỉ ra chính xác đoạn code bị drift selector.
