# TIKTOK-FLOW-TÌM-KIẾM (follow qua tìm kiếm) — phân tích đã verify (2026-08-11)

Nguồn: `D:\Taadaa\tiktok-follow\data\TIKTOK-FLOW-TÌM-KIẾM-Thành-đạt_decrypted.json`
(389 nodes / 709 edges). Các line ref dưới đây được Claude CLI audit r4/r5
xác nhận bằng grep/read TRONG file decrypted — đáng tin, không phải suy đoán.

## Cấu trúc node (label counts)

```
trigger 1 | insert-data 4 | press-key-phone 1 | element-exists 78 | press-home 10
touch 79 | start-app 1 | delay 99 | repeat-task 36 | swipe-scroll 29 | press-back 9
random 9 | conditions 17 | note 3 | type-text 1 | read-file-text 1 | loop-data 1
loop-breakpoint 1 | excel 1 | javascript-code 2 | get-attribute 5 | end 1
```

- Block name nằm ở node.**label** (data.name rỗng).
- Notes: "Lướt ban đầu", "Tìm kiếm và truy cập uid", "Nhả flow" (chỉ là kết
  thúc loop — KHÔNG phải verify/unfollow).

## Key selectors (đã verify line ref)

| Mục đích | Selector | Line ref |
|---|---|---|
| Mở app | package `com.ss.android.ugc.trill` | start-app |
| Search icon | `//node[@content-desc="Tìm kiếm" or @content-desc="Search"]` | 2654, 2693 |
| Input search | `//node[@content-desc="Tìm kiếm"]` + type `{{variables.UID.0}}` | 2654 |
| Kết quả tìm kiếm | `//node[@text="{{variables.UID.0}}" and @index="1"]` | 2742, 2766 |
| Nút follow | `//node[@text="Follow" or @text="Follow lại"]` | 2959, 3339 |
| Đã follow | `//node[@text="Đã follow"]` | 6205 |
| Profile/Hồ sơ | `//node[@content-desc="Hồ sơ" or @content-desc="Profile"]` | — |
| Close-X đơn | `//node[@content-desc="Đóng"]` (dùng NHIỀU NHẤT, dismiss chính) | 720, 820, 932... |
| Chuyển đổi tài khoản | `//node[@content-desc="Chuyển đổi tài khoản"]` (switch step) | 1646 |
| UID file | `D:\tik1va2.txt`, delimiter `;`, randomEnable | 51 |
| Loop | `1..Số_tài_khoản_cần_Flow` (trigger default 2) | 59, 2814 |

## Semantics quan trọng (đã verify — dùng khi port sang consumer)

- **Trạng thái nút follow: `Follow` / `Follow lại` / `Đã follow`** — "Follow
  lại" (follow-back) là CHƯA follow, KHÔNG được coi là success trong verify
  gate (Claude r4 P1). Set NOT-FOLLOWED = Follow|Follow lại (+ VN Theo dõi
  needs-calibration); SUCCESS = Đã follow|Đang theo dõi.
- **Identity: handle KHÔNG có `@` trong dữ liệu**, flow prepend `@` lúc check:
  line 1447/1531 `//node[@text="{{...taiKhoan}}"]` (không @) vs line 4261
  `//node[@text="@{{...taiKhoan}}"]`. So sánh identity phải strip-and-compare.
  Core `profile_identity_from_xml` lấy username `startswith("@")` — on-screen
  có @, workbook bare handle.
- **`@index="1"` ≠ XPath position `[1]`**: @index là index trong parent
  (node THỨ HAI trong sibling — thường bỏ row echo/suggestion ở index 0).
  Port giữ nguyên `and @index="1"` làm primary, không đổi sang `[1]` mù.
- **Mapping máy→tài khoản**: excel `TaiKhoan!B1:E9999`, `primaryKey "phoneId"`
  (= serial/deviceId) → JS `taiKhoanGanChoPhoneDuocChay = taiKhoan[deviceId]`
  → check profile `@{{...taiKhoan}}` (4154, 4211, 4261).
- **Tab Follower: 0 matches** trong flow (`Follower`/`Người theo dõi` = 0) —
  mode "follow follower của seed" là design USER THÊM, phải calibrate máy
  thật. Dòng 4886 "Khi người dùng này bắt đầu Follow mọi người..." = empty
  state của tab FOLLOWING trên acc đang chạy, không phải follower list seed.
- **Random/delay**: `Random1` 1..5 (delay), random index `{{variables.Random4}}`
  cho resource-id cover rows (chọn video ngẫu nhiên khi lướt).
- **JS hết hạn**: `new Date("2026-11-28")` throw — bản mua có hạn, bản tự
  build không cần.
- Resource-id ngắn (`rfm/str/sxc/szk/tcq/te2/tpu` + `[n]/node[2]`) — dễ vỡ
  theo bản TikTok; port ưu tiên selector semantic + core popup handler.

## Bao nhiêu thứ KHÔNG có trong flow gốc (user-added — attribution)

- Nhả-follow verify (reload → FOLLOW_BLOCKED) — KHÔNG có (reload/verify = 0).
- Ghi state kết quả về workbook — KHÔNG có ("Nhả flow" chỉ là kết loop).
- Mode 2 / tab Follower — KHÔNG có (0 matches).
→ Khi audit/viết plan: attribution đúng "user requirement" cho các thứ trên,
  không gắn nhãn "từ flow gốc" (Claude r2 P2 provenance).