# Mode 2 Follower/Following Tab Labels & Header Regex

## Pattern & Supported Labels
`mode2_follow_followers.py` phân loại bề mặt quan hệ follower/following bằng `_FOLLOWER_HEADER_RE` và `_FOLLOWER_EMPTY_LABELS`.

### Supported Labels
- **Tiếng Anh**: `follower`, `followers`, `following`
- **Tiếng Việt**: `người theo dõi`, `đã follow`, `đang follow`, `đang theo dõi`

### Regex Pattern
```python
_FOLLOWER_HEADER_RE = re.compile(
    r"^(follower|followers|người theo dõi|đã follow|đang follow|đang theo dõi|following)(?:\s+(\d+))?$",
    re.IGNORECASE,
)
_FOLLOWER_EMPTY_LABELS = {
    "follower",
    "followers",
    "người theo dõi",
    "đã follow",
    "đang follow",
    "đang theo dõi",
    "following",
}
```

### Tại sao cần bao quát cả "Đang follow" và "Đang theo dõi"?
- TikTok giao diện tiếng Việt qua các phiên bản / tài khoản khác nhau dịch tab following/follower thành "Đang follow", "Đang theo dõi", hoặc "Đã follow" / "Người theo dõi".
- Khi thiếu nhãn `"đang follow"` hoặc `"đang theo dõi"`, `_classify_follower_surface` phân loại sai thành `invalid`, khiến runner fail-closed hoặc dừng xử lý anchor/follower surface hợp lệ.
