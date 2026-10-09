# Bottom-nav Profile Tab Geometry & Selector Hierarchy (2026-09-13)

## Ngữ cảnh
Khi tap vào Profile/Hồ sơ tab ở bottom navigation của TikTok trong workflow upload / account switcher / feed / follow, TikTok có thể render:
1. Container node với resource-id `com.ss.android.ugc.trill:id/oly` (hoặc `profile_tab` cũ), content-desc `Hồ sơ` / `Profile`, bounds bao trùm cả icon lẫn label (vd: `[864,1794][1080,1920]`, center `(972, 1857)`).
2. Text node con bên trong với text `Hồ sơ` / `Profile`, bounds nhỏ hơn (vd: `[864,1864][1080,1903]`, center `(972, 1883)`).

## Thứ tự fallback chuẩn (Định vị Bottom-Nav Profile Tab)
Để tránh tap nhầm các node profile/hồ sơ khác ngoài feed hoặc trên header/drawer:
1. **Lọc theo vùng tọa độ Bottom-Nav**:
   - `visible_to_user == True` hoặc node `enabled == True`.
   - Trung tâm Y: `cy >= 0.8 * screen_height` (nằm ở đáy màn hình).
   - Trung tâm X: `cx >= 0.75 * screen_width` (nằm ở góc dưới cùng bên phải - tab thứ 5).
2. **Thứ tự ưu tiên selector**:
   - **Ưu tiên 1 (oly selector)**: Node có resource-id chứa `com.ss.android.ugc.trill:id/oly` thỏa mãn tọa độ bottom-nav.
   - **Ưu tiên 2 (profile_tab selector cũ)**: Node có resource-id chứa `profile_tab` thỏa mãn tọa độ bottom-nav.
   - **Ưu tiên 3 (Text node)**: Duyệt node có `text` khớp exact hoặc chứa "Hồ sơ" / "Profile" nằm trong vùng bottom-nav (`cy >= 0.8*H`, `cx >= 0.75*W`).
   - **Ưu tiên 4 (Content-desc exact)**: Node có `content-desc` khớp chính xác hoặc bắt đầu bằng "Hồ sơ" / "Profile" trong vùng bottom-nav.

## Assertion kiểm thử
Với layout Samsung chuẩn 1080x1920:
- Node text `Hồ sơ`: center xấp xỉ `(972, 1883)` (±30px).
- Cả 2 điểm tap `(972, 1857)` và `(972, 1883)` đều nằm trúng vùng nhận diện tab Hồ sơ.
