# Triage Quy Trình: [ACCOUNT_SWITCHER_FAILED] ACCOUNT_MISSING vs Mất Phiên / Văng Account (False Alarm Triage)

**Ngày ghi nhận:** 11/10/2026  
**Ngữ cảnh áp dụng:** Khi nhận Farm Alert P0 dạng:
`⚠️ [P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]: Máy Mxx: UploadHook/FeedSession: [ACCOUNT_SWITCHER_FAILED] select account failed: ACCOUNT_MISSING: expected account was not found.`

---

## 1. Cơ Chế Lỗi & Nguyên Nhân Gốc Rễ (False Alarm Mechanism)

### Bản chất:
- Khi một máy nuôi nhiều tài khoản TikTok (theo các ca / slot Tik 1 -> Tik 8):
  - Máy đang mở ở nick của ca trước (ví dụ slot Tik 6 `@julesuqi6h4`).
  - Ca mới (ví dụ Ca 1 - Tik 1 `muyduyen4589`) yêu cầu chuyển đổi tài khoản (Account Switcher).
- Runner thực hiện tap vào tiêu đề profile (Header anchor, ví dụ tọa độ `(240, 322)` tương ứng với `bounds="[36,280][444,364]"`).
- **Lỗi xảy ra tại UI anchor tap:**
  - Trên TikTok (đặc biệt v47.x Samsung S7), menu bottom-sheet/dropdown danh sách tài khoản **không bung ra** (`stop_reason: manual-needed:account-switcher-not-open: profile screen remained after switch-anchor tap`).
  - Màn hình vẫn ở nguyên trang Profile cá nhân của nick hiện tại.
- **Dây chuyền phán đoán sai:**
  - Script chuyển sang bước vuốt tìm tên tài khoản mục tiêu (`muyduyen4589`).
  - Do bottom-sheet chưa mở, UI không có danh sách tài khoản -> Sau 3 lần swipe, script văng `ACCOUNT_MISSING: expected account was not found`.
  - Watchdog bắt chuỗi lỗi `ACCOUNT_MISSING` và lập tức kích hoạt cảnh báo `P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT`.
- **Thực tế:** Nick không hề bị văng, không bị logout, không bị checkpoint hay ban. Phiên đăng nhập của tài khoản hiện tại và các tài khoản trong máy vẫn hoàn toàn nguyên vẹn.

---

## 2. Quy Trình Khảo Sát T0 Bắt Buộc (Evidence-First Verification)

1. **Kiểm tra thông số máy O(1):**
   ```bash
   python D:/Taadaa/tools/inspect_machine.py <N>
   ```
   Xác nhận serial máy, trạng thái pin, màn hình awake và Wi-Fi.

2. **Truy vết Artifact & Run Directory O(1):**
   - Đọc kết quả trong `D:/Taadaa/runtime/kibe/live/<YYYY-MM-DD>/row-X-xxxxxx/<run_id>/machines/machine_<N>/<run_id>/upload_result.json` hoặc `summary.txt`.
   - Tìm thư mục run chi tiết trong `D:/CodexRuntime/tiktok-video/runs/run_<serial>_<timestamp>/`.
   - Tìm file ảnh snapshot hiện trường lúc cố gắng switch: `account-switcher-profile.png` hoặc `artifacts/.../screen.png`.

3. **Soi mắt kiểm chứng (Invariant Vision Mandatory):**
   - Mở ảnh qua `browser_vision` (hoặc WinRT OCR) để xác nhận màn hình:
     - Nếu màn hình là **Tab Hồ sơ có avatar, username, video, follower** -> **100% FALSE ALARM**, nick vẫn sống và đang đăng nhập bình thường.
     - Nếu màn hình là **Guest Profile** (nút "Đăng ký / Đăng nhập"), màn hình đen, hoặc thông báo vi phạm/bị khóa -> Mới là mất phiên thật sự.

---

## 3. Kỷ Luật Điều Phối & Phục Hồi (Recovery & Governance)

1. **Tuyệt đối cấm thao tác mù:**
   - CẤM bấm tay ADB (`input tap`, `input keyevent`) để chữa cháy tạm bợ.
   - CẤM vội vàng xóa tài khoản, đổi password, đổi mail hay chuyển nick sang trạng thái DIE.
2. **Device Lock Invariant:**
   - Mọi lệnh tương tác ADB với thiết bị bắt buộc bọc qua device lock:
     ```bash
     python D:/Taadaa/tools/with_device_lock.py --machine <N> -- <adb_cmd>
     ```
3. **Phân loại lỗi & Xử lý (4 Nhánh Chính — Chống dừng lại ở khảo sát suông):**
   - **Nhánh A — UI Switcher Anchor Glitch:** Bottom-sheet chưa mở được (`stop_reason: manual-needed:account-switcher-not-open`). Tọa độ tap anchor tiêu đề trượt (ví dụ: thiếu resource suffix `t_3`, `_PROFILE_HEADER_X_RATIO` chưa bao quát vùng x=240). Bắt buộc chuyển ngay sang hành động sửa code (T1 O(1) hoặc dispatch Worker) và chạy focused test.
   - **Nhánh B — Nick Ký Sinh (Parasite Account) chiếm slot:** Bottom sheet ĐÃ mở được (ví dụ kiểm tra `soft-reboot-account_switcher-before.png`), nhưng máy chỉ chứa tối đa 8 nick và có 1 nick cũ ("nick ký sinh", ví dụ `samnga2403`) từng bị xóa/thay thế trên DB/Excel nhưng chưa được logout vật lý trên điện thoại.
     * Hậu quả: Nick ký sinh chiếm mất 1 slot khiến nick mới của Ca (ví dụ Tik 1 `muyduyen4589`) không thể login hoặc bị thiếu -> Runner vuốt tìm không thấy ném `ACCOUNT_MISSING`.
     * Quy trình xử lý dứt điểm Nick Ký Sinh:
       1. Đối soát 8 nick trong Switcher với 8 dòng của máy trong `taikhoan_run_safe.xlsx` để tìm ra tên nick lạ/ký sinh.
       2. Chạy công cụ logout chính quy để trục xuất nick ký sinh:
          `python D:/Taadaa/tools/do_logout_account.py <M> <parasite_username> <serial>`
       3. Sau khi máy nhả slot, tiến hành login tài khoản chính chủ còn thiếu vào máy.
   - **Nhánh C — Bottom-Sheet Đã Mở & Nick Mục Tiêu ĐÃ CÓ Trong Danh Sách (Classifier Loop, Touch Offset & Anti-Báo-Cáo-Suông):**
     * Hiện tượng: Bottom sheet mở thành công, trích xuất OCR/XML thấy đủ 8 nick và nick mục tiêu của Ca (ví dụ `trinhgiang7694` ở vị trí 7) nằm sờ sờ trên UI. Tuy nhiên, khi runner tap vào nick mục tiêu, giao diện chưa kịp chuyển đổi (UI lag hoặc tap lệch) hoặc runner phân loại màn hình là `manual-needed:account-switcher`, khiến bước lặp kế tiếp không thấy nick hoặc kẹt pre-tap guard và kết luận sai `ACCOUNT_MISSING`.
     * Triage: 100% False Alarm cho mất phiên. Tài khoản hoàn toàn nguyên vẹn trên máy. CẤM xóa nick/đổi mail/đổi pass.
     * KỶ LUẬT PHẢN HỒI CHỐNG BÁO CÁO SUÔNG (User Invariant: "Ủa chứ sao báo động giả fix đi chứ"):
       - **CẤM TUYỆT ĐỐI** chỉ dừng lại ở việc tuyên bố "100% false alarm" rồi để đó / đóng băng task. Báo động giả thì PHẢI LẬP KẾ HOẠCH FIX DỨT ĐIỂM.
       - Khi máy đang nằm trong cụm kẹt transport phần cứng (DEVICE_OFFLINE do USB 2.0 EHCI micro-spike nghẽn bus): Bắt buộc giải thích rõ ràng thiết bị đang kẹt socket ADB nên không thể tap hay sửa tức thời, đồng thời cam kết lộ trình phục hồi 2 bước cụ thể:
         1. *Bước 1 (11:35 trưa):* Chờ Task `Taadaa_Farm_Daily_Reboot_1135` kích hoạt System Bus Reset từ BIOS (có TFT Game Guard bảo vệ ván cờ) để kéo toàn bộ 80 máy lên xanh.
         2. *Bước 2 (11:36 - Trước ca trưa 12:00):* Ngay khi máy online lại, chủ động chạy inspect O(1) và canary test chuyển tài khoản trực tiếp trên máy; kiểm tra token thực tế của nick trong Switcher: nếu nick còn nguyên vẹn thì thực hiện switch, nếu token thực sự hết hạn thì kích hoạt auto-login recovery từ kho credential, chụp ảnh in-app gửi User nghiệm thu.
     * Lưu ý thẩm định ảnh hiện trường cũ: Khi chạy `evidence_gate_verifier.py` để verify artifact của các run trước đó (>10 phút), bắt buộc thêm cờ `--max-age 86400` để tránh bị chặn bởi `ANTI_REPLAY_VIOLATION: Pre-submit image is stale/replayed`.
   - **Nhánh D — Dấu Chấm Than Wi-Fi ("Không Có Internet") & Bẫy Domain Hostname Proxy (Ref: `references/wifi-exclamation-mark-and-pppoe-uptime-vs-502-switcher-triage-20261017.md`):**
     * Hiện tượng: Icon Wi-Fi trên thanh status bar có dấu chấm than (`wifi_combo` có `content-desc="...Không có Internet"`), giữa màn hình có vòng xoay `com.ss.android.ugc.trill:id/tux_loading_hud`. Runner tap chọn nick trong Switcher nhưng TikTok không thể kết nối server để cấp token mới -> tự hủy thao tác chuyển tài khoản, giữ nguyên nick cũ -> Verify ném `ACCOUNT_VERIFY_MISMATCH`.
     * Triage:
       1. Phân biệt Layer 3 PPPoE trên web quản trị `kibe:2310` (Uptime > 7 ngày) với Layer 7 Sing-box container (`192.168.110.2:200xx` -> MobiProxy 4G `51xx`).
       2. Bẫy Tên Miền Hostname (`mirotik1.taadaa.click:1000x`): Kiểm tra `adb shell settings get global http_proxy`. Nếu thấy gán domain ngoài thay vì IP LAN `192.168.110.2`, điện thoại phân giải DNS ra IP WAN và bị firewall MikroTik chặn (Hairpin NAT drop), gây mất mạng hoàn toàn.
     * Kỷ luật & Khắc phục:
       1. CẤM gán domain vào Android http_proxy; BẮT BUỘC dùng IP LAN `192.168.110.2:200xx` (Kibe) hoặc `192.168.110.2:100xx` (Admin) kèm `captive_portal_mode 0`.
       2. Sửa code runner: Kiểm tra UI nếu có "Không có Internet" thì fast-fail ngay, cấm loop tap mù; chờ tối đa 5s cho loading spinner biến mất trước khi đọc Profile.
       3. Kiểm tra va chạm device lock trước khi can thiệp thiết bị. Sau khi khôi phục IP LAN và hết dấu chấm than mới mở lại fleet.

---

## 4. Kỷ Luật Hook Tránh Bị Evidence First Gate Chặn Gây Spam
- **Nguyên nhân Gate chặn:** Con hook `Evidence First Gate` tự động quét output: nếu agent báo hoàn thành mà thiếu `MEDIA:`, hoặc gửi `MEDIA:<path>` mà đường dẫn đó CHƯA được nạp qua `evidence_gate_verifier.py` (hoặc WinRT OCR) ghi nhận vào audit ledger, hook sẽ lập tức chặn tin nhắn và thay bằng thông báo vi phạm (`[FAIL-CLOSED VIOLATION]` hoặc `[UNVERIFIED MEDIA]`).
- **Kỷ luật:** BẮT BUỘC chạy `python D:/Taadaa/tools/evidence_gate_verifier.py --pre-image <path> --allow-single-inspection` trước khi đính kèm `MEDIA:<path>` trong câu trả lời. Tuyệt đối không để xảy ra tình trạng tin nhắn gate rác đè lên câu trả lời của agent và gửi đến User.
