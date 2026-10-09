# TikTok 46.9.3 Follower Row Button Drift (id/u68)

## Bối cảnh
Trên TikTok version 46.9.3, id nút follow trong follower row (danh sách Follower của user) xuất hiện biến thể mới: `id/u68` (bên cạnh các id cũ như `tcj`, `thb`, `tvn`, `tum`, `u2f`).
Nếu không cập nhật selector, `_follow_button_for_row` không nhận diện được nút follow, dẫn đến lỗi "follower row không có nút follow semantic" và skip hàng sai lệch.

## Giải pháp Selector Patch
Trong `follow_runner/core/selectors.py`:
Cập nhật tuple `FOLLOWER_FOLLOW_BUTTON_RESOURCE_IDS` để thêm đầy đủ 3 dạng suffix/canonical:
```python
FOLLOWER_FOLLOW_BUTTON_RESOURCE_IDS = (
    "com.ss.android.ugc.trill:id/tcj", "com.ss.android.ugc.trill:id/thb", "com.ss.android.ugc.trill:id/tvn", "com.ss.android.ugc.trill:id/tum", "com.ss.android.ugc.trill:id/u2f", "com.ss.android.ugc.trill:id/u68",
    ":id/tcj", ":id/thb", ":id/tvn", ":id/tum", ":id/u2f", ":id/u68", "id/tcj", "id/thb", "id/tvn", "id/tum", "id/u2f", "id/u68",
)
```

## Unit Test Coverage
Trong `follow_runner/tests/test_mode2_follow_followers.py`:
Bổ sung tests cho cả 2 hàm cốt lõi:
1. `test_follow_button_for_row_supports_id_u68()`: Test unit trực tiếp hàm `_follow_button_for_row`.
2. `test_cluster_follower_rows_supports_id_u68()`: Test integration flow `_cluster_follower_rows` parse từ XML node cấu trúc chuẩn, xác minh gán đúng nút action cho cả "Follow" và "Follow lại/Bạn bè".

## Lưu ý môi trường kiểm thử
Khi chạy `pytest` từ MSYS shell / bash trên Windows:
Cần set `PYTHONPATH=.` hoặc dùng `python.exe -m pytest ...` để module `follow_runner` được import chính xác mà không gặp `ModuleNotFoundError`.
Ví dụ:
`PYTHONPATH=. D:/Taadaa/python-envs/automation/Scripts/pytest.exe follow_runner/tests/test_mode2_follow_followers.py -k "u68" -v`
hoặc
`D:/Taadaa/python-envs/automation/Scripts/python.exe -m pytest follow_runner/tests/test_mode2_follow_followers.py -k "u68" -v`
