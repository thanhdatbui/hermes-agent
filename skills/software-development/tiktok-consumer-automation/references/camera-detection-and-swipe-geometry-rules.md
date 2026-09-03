# TikTok Feed Camera Mode Detection & Gesture Safety Rules

## Key Pitfalls & Root Causes

### 1. False Positive Camera Detection from Feed Captions
- **Issue**: Feed videos with photo carousel ("Ảnh") or AI-generated disclosures ("Có chứa nội dung do AI tạo") were misclassified as Camera/Creation Mode (`manual-needed:popup`).
- **Fix**:
  - Do not use substring search on generic words like `ảnh`, `tạo`, `đăng`.
  - Check elements at `Y >= 1000` with exact text matching against camera mode terms: `{"10 phút", "60s", "15s", "văn bản", "10m", "templates", "photo", "camera"}`.
  - Require at least 2 distinct camera mode tokens on the screen.

### 2. Accidentally Tapping the Bottom '+' Button
- **Issue**: Notification shade dismiss or upward swipe starting from `Y=1800` hit the TikTok '+' create button centered at `(540, 1857)`, turning on the camera.
- **Fix**:
  - Safe upward swipe start coordinate: `Y <= 1600` (recommended: `(540, 1540)`).
  - Move fallback tap coordinates away from bottom margin to mid-screen (`Y=1200`).

### 3. 'Follow Friends' Popup Auto Follow-Back
- **Rule**: When encountering `Follow bạn bè của bạn` / `Follow your friends` modal, tap all "Follow lại" / "Follow back" buttons before dismissing with X / Back.

### 4. 9Router Independent Plan-Review Gate
- Every code fix must be verified with `pytest` + independent audit via 9Router `plan-review` model returning `{"passed": true, "verdict": "APPROVED"}` before `git commit` and `git push`.
