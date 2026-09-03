# TikTok Login Coordinates & Selectors (1080x1920)

Last verified: 2026-07-29 on TikTok 44.2.3 / 46.x

## Bottom Navigation (all versions)
| Tab | Center | Bounds |
|-----|--------|--------|
| Trang chủ | (108, 1857) | [0,1794][216,1920] |
| Cửa hàng | (324, 1857) | [216,1794][432,1920] |
| Hộp thư | (756, 1857) | [648,1794][864,1920] |
| Hồ sơ | (972, 1857) | [864,1794][1080,1920] |

## Profile Sticky Header (to open account switcher)
| Version | resource-id | Center |
|---------|-------------|--------|
| 46.x | `com.ss.android.ugc.trill:id/s6d` | (540, 552) |
| 44.2.3 | `com.ss.android.ugc.trill:id/s6d` | (540, 552) |

## Account Switcher - "Thêm tài khoản"
| Version | resource-id | Center |
|---------|-------------|--------|
| 46.x | `com.ss.android.ugc.trill:id/mqb` | (433, 1788) |
| 44.2.3 | `com.ss.android.ugc.trill:id/lvy` | (427, 1788) |

## Profile Tab Fallback (when image navigation fails)
If `navigator.tap_profile()` fails, use fixed coordinate tap:
- Center: (972, 1857)
- This works on all tested versions (46.x, 44.2.3, SM-G930F/W8)

## Signup Screen (44.2.3)
- "Bạn đã có tài khoản? Đăng nhập": bounds [0,1740][1080,1920], center (540, 1830)

## Login Screen
- "Sử dụng số điện thoại/email/tên người dùng": bounds [216,823][906,880], center (561, 851)
- "Email/tên người dùng" tab: bounds [472,260][954,317], center (713, 288)

## Continue Button (after entering credentials)
- resource-id varies: `com.ss.android.ugc.trill:id/fb6` (46.x) or `com.ss.android.ugc.trill:id/eta` (44.2.3)
- bounds: [96,1603][984,1759], center (540, 1681)

## Post-Login Popups
| Popup | Dismiss Action | Coordinates |
|-------|---------------|-------------|
| "Cho phép truy cập danh bạ" | Tap "TỪ CHỐI" | (557, 1134) |
| "Kiểm tra bảo mật" | Tap "Đóng" (top-right) | (996, 923) |
| Privacy Policy (SparkActivity) | Scroll down 10x, tap bottom | (540, 1750) |
| UniversalPopupActivity (consent) | Swipe up | swipe 540 1600 540 400 300 |

## AdbKeyboard Input (SM-G930W8 workaround)
On SM-G930W8, `am broadcast ADB_KEYBOARD_INPUT_TEXT` returns `result=-1` and
shell hangs. Text IS entered — use fire-and-forget with subprocess timeout=8s.
Verify with `uiautomator dump` after. Alternative: `adb shell input text <base64>`
only works with AdbKeyboard active; may leak special chars.

## Email Input Field (after tab selection)
- resource-id: varies
- bounds: [138,464][942,524], center (540, 494)

## Signup Screen Extra (44.2.3)
- "Tiếp tục với email" (signup link, NOT for login): center (540, 788)
- Phone number tab: center (693, 596)

## ADB Path
`C:\Program Files (x86)\xiaowei\tools\adb.exe`

## Workbook Paths
- Tracking: `D:\OneDrive\Tiktok_Reg\taikhoan_dat_v2_updated .xlsx`
- Proxy mapping: `D:\OneDrive\codex_gmail_debug\PROXYgandienthoai.xlsx`

## Workbook Columns
| Col | Header |
|-----|--------|
| 0 | Máy |
| 1 | Tik |
| 2 | ID |
| 3 | PASS |
| 4 | 2FA |
| 5 | GMAIL |
| 6 | PASS MAIL |
| 9 | device ID (serial) |
