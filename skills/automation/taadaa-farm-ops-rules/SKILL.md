---
name: taadaa-farm-ops-rules
description: "Taadaa farm safety, close-session, and multi-machine operations."
---

# Taadaa Farm Ops Rules (ALL-repo automation)

## 🛑 BẮT BUỘC: QUY TRÌNH RECOVERY & XỬ LÝ ALERT [MÁY N] (User chốt 2026-09-02)

1. **CẤM CHỮA CHÁY TẠM THỜI QUA ADB:**
   - CẤM xem việc gõ lệnh `adb shell input` (vuốt màn hình, bấm nút) hay sửa `settings` bằng tay là "xong việc".
   - Mọi thao tác xử lý lỗi BẮT BUỘC phải dẫn đến **sửa code trong script (`python_runner` / `automation-core`)** để toàn bộ 80-160 máy tự động vượt qua khi chạy thật.
2. **LỆNH TRÍCH XUẤT HIỆN TRƯỜNG DUY NHẤT (CẤM GREP / CẤM QUÉT ĐĨA):**
   - Khi nhận alert `[MÁY N]`, chạy: `python D:/Taadaa/tools/inspect_machine.py <N>`.
   - CẤM TUYỆT ĐỐI dùng `os.walk`, `glob(recursive=True)`, `find`, `grep -rn` quét diện rộng codebase hay ổ đĩa để tìm chuỗi lỗi / file log.
3. **CHU TRÌNH 5 BƯỚC RECOVERY CHUẨN (PHÂN VAI COORDINATOR vs WORKER):**
   - **B1 (Inspect - Coordinator):** Chạy `python D:/Taadaa/tools/inspect_machine.py <N>` hoặc lệnh ADB trực tiếp theo serial máy để lấy hiện trường O(1) (XML + screencap).
   - **B2 (Root Cause & Dispatch - Coordinator):** Đọc log run & mở flow xác định phạm vi lỗi. BẮT BUỘC dispatch worker subagent qua `delegate_task(goal=..., context=...)` ngay lập tức. CẤM TUYỆT ĐỐI Coordinator tự viết script Python probe, test hàm hay reproduce thử nghiệm trong terminal session chính.
   - **B3 (Patch Script & Focused Test - Worker Subagent):** Subagent reproduce trong context riêng, sửa codebase xử lý tự động + viết focused test (<30s).
   - **B4 (Canary Test - Coordinator):** Chạy canary thực tế kiểm chứng script mới tự giải cứu được máy kẹt.
   - **B5 (Closeout - Coordinator):** Model Review (APPROVED) -> Commit -> Push master.
4. **QUY TẮC WORKER BUDGET & CHỐNG DÔNG DÀI (ANTI-OVERENGINEERING - BẮT BUỘC):**
   - **Giới hạn thời gian & tool call:** Mọi worker dispatch qua `delegate_task` BẮT BUỘC phải hoàn tất dưới 15 phút và tối đa <= 20 tool calls.
   - **Task Read-only / Inspect / OCR:** CẤM TUYỆT ĐỐI worker tự ý sửa code, CẤM chạy pytest test-suite, CẤM commit. Chỉ đọc log, inspect hiện trường, OCR và trả kết quả ngay trong <= 10 tool calls (< 10 phút).
   - **Task Fix Code:** Chỉ sửa ĐÚNG file flow/module chỉ định (Scope Lock), viết focused test <30s, CẤM chạy pytest trần toàn bộ repo, CẤM over-engineer viết test đồ sộ hay refactor lan man.


## STOP GATE — BẮT BUỘC

## CHUẨN ANTI-MINEFIELD TOÀN FARM

1. **Zero Silent Failures:** không nuốt exception; log lỗi kèm context và báo đúng trạng thái.
2. **Bounded Execution:** mọi ADB, HTTP, socket, OCR và subprocess phải có timeout tường minh và retry hữu hạn; thiếu timeout thì không chạy.
3. **Idempotency & Safe Resume:** batch phải kiểm tra lock/receipt/checkpoint trước khi tiếp tục, không lặp side-effect nguy hiểm.
4. **Fail-Closed:** gặp UI/state không nhận diện được thì chụp evidence tại hiện trường, giữ trạng thái an toàn và dừng; không tự đoán, không tự tap tay, không tự patch.

## Downloader & Cleanup
Downloader: [`references/dual-scope-downloader.md`](references/dual-scope-downloader.md).
Cleanup: [`references/account-cleanup-and-banned-handling.md`](references/account-cleanup-and-banned-handling.md).

## CHAINED NO_AGENT CRON — REPORT EXECUTION, NOT WRAPPER COMPLETION
Treat wrapper completion as unverified until exact run artifacts prove success. Classify each phase from summary counts, manifests, batch directories, and worker logs; if no fresh worker artifacts exist, report launcher/preflight failure, not UI/OTP failure. Quote exact signatures, separate hypotheses, include evidence/workbook-change evidence, and redact credentials. Procedures: `references/chained-cron-failure-evidence.md`, `references/gmail-chain.md`, `references/tiktok-cron-inventory-preflight.md`, `references/lock-aware-target-selection.md`, `references/locked-device-triage-and-shift-diagnostics.md`, `references/device-locks-watchdog.md`, `references/transparent-router-proxy-preflight.md`, and `references/uiautomator-case-fix-catalog-and-anti-patterns.md`.
1. Máy live + script chạy/lỗi → **KHÔNG tự sửa code, KHÔNG tự chạy lại, KHÔNG tự probe, KHÔNG tự thử tay**.
2. Mọi lỗi → screencap → **TỰ ĐỌC ẢNH bằng vision_analyze TRƯỚC khi gửi** (agent có mắt, KHÔNG được \"gửi ảnh cho user xử lý thay\" — user phạt 17/08 tối: \"mày k thể tự đọc hình r hỏi t cách xử lý thay vì chỉ gửi t cái hình k à\") → gửi ảnh thật (`MEDIA:` dòng riêng) + mô tả màn + **đề xuất hướng xử lý dựa trên ảnh đã đọc** → **DỪNG chờ user hướng dẫn**. Báo lỗi PHẢI kèm ảnh đúng lúc kẹt (không gửi ảnh sau khi script đã dừng hẳn và máy đã chuyển màn khác — chụp ngay lúc log dừng).
3. User hướng dẫn bước nào → **ENCODE bước đó vào script + test → mới chạy lại**. Bước chưa hướng dẫn = KHÔNG làm.
4. Nghi ngờ → **HỎI**. Tự làm/sửa khi chưa được yêu cầu = VI PHẠM, dù "chỉ 1 dòng" hay "cho nhanh".
5. **Ảnh màn hình PHẢI hiển thị được**: gửi file ảnh thật `MEDIA:<đường dẫn tuyệt đối>` ở **DÒNG RIÊNG**, KHÔNG bọc markdown (`**`/`` ` ``/`[..]`), kiểm tra file tồn tại trước khi gửi.
6. **CẤM TUYỆT ĐỐI gửi đường dẫn text** (`C:\\Users\\...` hay MEDIA: giữa đoạn văn) thay cho ảnh hiển thị — user chửi lỗi này nhiều lần (session khác 16:02 17/08 vẫn gửi `MEDIA:...` bọc `**` → Telegram nuốt thành text).
7. **CHẨN ĐOÁN ĐƯỢC ≠ ĐƯỢC PHÉP SỬA (vi phạm thật 17/08 tối — user: \"Tao cập nhật policy skill r nhé, kẹt lỗi chỗ nào phải gửi hình báo tao đéo đc tự ý tự sửa đâu\")**: tìm ra root cause (vd log chứng minh tap nick success nhưng notification shade VPN mở đè → verify fail; hoặc detect_add_phone_popup không match bottom-sheet close geometry) **KHÔNG cho phép tự patch code**. Thứ tự đúng: screencap + gửi ảnh + mô tả lỗi (kèm log/XML evidence) → DỪNG chờ user quyết hướng. User CHỈ giao quyền sửa khi hướng dẫn rõ ràng (\"chạy fix đi\" = ủy quyền fix theo HƯỚNG user chốt, vẫn phải test + chạy lại). Phân biệt: user nói \"sao k chọn đc profile?\" = câu HỎI chẩn đoán, không phải lệnh sửa — trả lời bằng evidence (ảnh + log), không tự patch 2 file rồi mới báo.

Quy tắc chung áp dụng cho MỌI repo automation (Tiktok_Reg, Hotmail, add mail khoi phuc, tiktok-video, automation-core, gan-proxy, feed/follow...), không riêng repo nào.

**Inventory 10 repo automation (chốt 2026-08-17, user: "9 repo consumer h lên 10"):** Tiktok_Reg, Hotmail, Tiktok-video, tiktok-log-in, tiktok-follow, tiktok-add-bao-mat-f2a, tiktok-luot nuoi acc, gan-proxy, register gmail + automation-core (lõi). Các repo khác có AGENTS.md (AI-Tools, Hermes, "open claw", "site ban hang clone"...) KHÔNG phải farm repo — đừng đụng khi sweep rule. Khi append rule all-repo: kiểm tra `[ -d "$d/.git" ]` + có AGENTS.md/PROJECT_RULES.md; repo chỉ có AGENTS.md (vd automation-core) phải `git add` từng file riêng (add 2 path khi 1 path thiếu → abort cả, xem `rule-file-append`).

## 1. Tuần tự vs song song (user rule 2026-08-16)

| Phạm vi | Chế độ |
|---|---|
| **Hotmail login** (repo `D:\Taadaa\Hotmail`) + **add mail khôi phục** (repo `D:\Taadaa\add mail khoi phuc`) | **TỪNG MÁY MỘT (tuần tự)** — bắt buộc |
| Mọi repo khác / mọi bước khác (detect, verify máy, đọc source, batch reg, feed...) | **Song song bình thường** |

**Lý do tuần tự bắt buộc:** recovery mailbox `thanhdatbui1995@gmail.com` dùng CHUNG cho mọi máy — Microsoft gửi OTP vào cùng 1 inbox. Chạy 2 máy song song → script đọc nhầm mã máy này nhập vào máy kia (OTP leak). Vì vậy:
- Start máy N → đợi OTP → nhập → verify inbox → CHỈ SAU ĐÓ mới start máy N+1.
- Không bao giờ chạy `login_outlook_app` / `read_otp_mail.py` cho 2 máy cùng lúc.
- Các máy đang chờ không bị treo — chúng chỉ chờ tuần tự ở bước login/add-mail; mọi thứ khác của chúng vẫn chạy song song.

**NGOẠI LỆ 2026-08-17 (hotmail loại 2 + Graph API):** mailbox mua từ boxtaikhoan dạng `mail|pass|refresh_token|client_id` đọc OTP qua **Graph API từ PC** (`hotmail_provider.read_tiktok_otp_from_graph_token`, Tiktok_Reg commit `8752c7b`, bật bằng env `HOTMAIL_TOKEN_LIST`) — mỗi mailbox có token RIÊNG, không dùng chung recovery inbox → đọc **SONG SONG bình thường**, không tuần tự. Tuần tự bắt buộc chỉ còn áp cho shared recovery mailbox / Outlook-app reader (giữ nguyên). Chi tiết: skill `tiktok-registration-ops` → `references/token-otp-graph-reader-20260817.md`.

## 2. Luật handle mọi thao tác tay (user rule 2026-08-16)

> "Bất kỳ thao tác tay nào khi làm việc (tap tay, fix tay, workaround) PHẢI lưu ngay vào skill cấp độ ALL repo automation — handle script lại trước khi báo xong."

Quy trình bắt buộc khi phát hiện màn hình/selector/flow mới hoặc làm tay thành công:
1. **Code hóa ngay** vào canonical script của repo tương ứng (handler + regression test + COMPAT entry nếu repo yêu cầu).
2. **Lưu skill** — skill liên quan repo (vd `hotmail-outlook-automation`, `tiktok-registration-ops`) HOẶC skill all-repo này nếu rule chung.
3. Chỉ sau đó mới coi bước đó "xong" và báo cáo.

Cấm: làm tay xong rồi quên, làm tay rồi báo "máy tự qua", workaround không encode.

## 3. NO-MANUAL-TAP (hard rule, thêm 2026-08-16 sau khi vi phạm lần nữa; CHỐT 2026-08-17)

**CẤM TUYỆT ĐỐI tap/swipe/keyevent bằng tay trên máy thật để "debug nhanh".** Khi gặp màn hình UI mới:
1. DỪNG — không tap gì bằng tay.
2. Chụp ảnh + dump XML (read-only).
3. Viết helper + test cho màn đó trong script.
4. CHẠY SCRIPT để thao tác — nếu script fail, sửa script, chạy lại.
5. Chỉ dùng tay khi thao tác đó đã được encode 100% trong script (script chạy thay tay).

**MỆNH ĐỀ CHỐT 2026-08-17 (user phạt "cái đm script bị lỗi mày fix hay mày đang tự kỉ ngồi làm tay"):**
- **CHỈ TỰ LÀM TAY KHI USER YÊU CẦU** — mọi thao tác adb tay (tap/gõ/broadcast/swipe) ngoài script trên máy thật = VI PHẠM, kể cả "test nhanh" hay "xem thử". User: "chỉ có thể tự làm khi t yêu cầu".
- **Script CHẠY ĐẾN HẾT** — không dừng giữa chừng để "kiểm tra" hay "sửa nhanh" rồi chạy lại vòng vòng. Gặp fail → để script tự chụp ảnh lỗi (guard dưới) → gửi user → DỪNG chờ hướng dẫn.
- **Script guard FAIL_STOPPED (Tiktok_Reg commit `d510afb`):** `except RuntimeError` → tự `screenshot(device, "FAIL_STOPPED_<stt>")` trước `sys.exit(1)` — agent đọc ảnh đó gửi user, KHÔNG tự bấm máy. Áp dụng pattern này cho mọi repo live automation.
- **KHI USER HƯỚNG DẪN = SCRIPT ĐANG LỖI → SỬA SCRIPT NGAY (user nhấn mạnh 2026-08-17):** user gửi ảnh + hướng dẫn ("bấm resend lấy OTP mới nhập lại", "vuốt cho qua"... ) nghĩa là script kẹt ở bước đó → ENCODE hướng dẫn vào canonical script (helper + regression test) TRƯỚC, rồi mới chạy script lại. TUYỆT ĐỐI KHÔNG chạy lại `--resume` hy vọng tự qua — nếu script xử lý đúng thì user đã không phải hướng dẫn. User: "khi t hướng dẫn nghĩa là script bị kẹt lỗi cần phải sửa".
- **USER-CHỤP-ẢNH-DRIVEN (user chốt 2026-08-17, "t chụp tới đâu thì code lại làm theo đúng ý t"):** user chụp ảnh màn hình hướng dẫn tới bước nào → agent code script làm ĐÚNG ý user bước đó → **qua được bước tiếp theo mới coi là handle script xong**; bước nào script không tự qua được → DỪNG, chụp ảnh gửi user chờ hướng dẫn tiếp. Không code vượt trước ý user, không tự chế bước user chưa duyệt.
- Khi user hướng dẫn xong → **encode hướng dẫn vào script** (helper + test) → chạy script, KHÔNG chạy tay theo lời user rồi bỏ.

Vi phạm pattern: "tap tay cho nhanh rồi code sau" = vi phạm rule dù sau đó có code. Thứ tự bắt buộc: CODE TRƯỚC, TAP QUA SCRIPT.

## 4. SEND-SCREENSHOT-ON-FAIL + từng bước duyệt (user rule 2026-08-16, thêm sau vi phạm)

**GỬI ẢNH = GỬI FILE ẢNH HIỂN THỊ (user phạt nhiều lần 2026-08-17, lần cuối yêu cầu "cập nhật skill rule để ép tuân thủ"):** mọi ảnh màn hình gửi user qua Telegram PHẢI là file ảnh thật dạng `MEDIA:<đường dẫn tuyệt đối>` — quy tắc TUYỆT ĐỐI:
1. **MEDIA: phải là DÒNG ĐẦU TIÊN CỦA MESSAGE — KHÔNG CÓ TEXT TRƯỚC** (không "Xin lỗi...", không mô tả, không tiêu đề trước MEDIA:).
2. **LUÔN KÈM TÊN / SỐ MÁY RÕ RÀNG (User rule 18/08)**: Trong phần mô tả ngay dưới dòng MEDIA:, PHẢI ghi rõ **[MÁY XX]** (STT thiết bị) đang gửi ảnh để user nhận diện chính xác máy nào gặp lỗi. Cấu trúc chuẩn của một message gửi ảnh lỗi:
   - Dòng 1: `MEDIA:<đường dẫn tuyệt đối dùng backslash>`
   - Dòng 2: `### [MÁY XX] - <Tên màn hình / Nhóm lỗi>`
   - Dòng 3+: Mô tả chi tiết từ kết quả đọc ảnh (vision_analyze), trạng thái thiết bị và đề xuất hướng xử lý.
3. **DÙNG BACKSLASH**: `MEDIA:C:\Users\Kibe\tmp\m75_stuck.png` — backslash hiện ảnh thật trên Telegram.
4. Trước khi gửi kiểm tra file tồn tại (`ls -la`) — file .png mới screencap, không gửi folder.
5. KHÔNG bao giờ viết "ảnh ở C:\..." thay cho MEDIA:; KHÔNG nhúng MEDIA: giữa đoạn văn.
5. Nếu đã đúng format (dòng đầu + **BACKSLASH** + file tồn tại) mà user vẫn báo thấy path → BÁO user là lỗi hệ thống render + HỎI cách nhận ảnh, KHÔNG lặp lại format cũ thêm lần nữa.
Ví dụ đúng (toàn bộ message = chỉ 1 dòng MEDIA:, BACKSLASH như đã verify 17/08 chiều):
```
MEDIA:C:\Users\Kibe\tmp\m75_stuck.png
```
7. **SCRIPT TREO (process còn sống nhưng log đứng yên ≥2-3 phút) = LỖI → KILL process ngay + chụp ảnh + gửi user** (user nhắc nhiều lần 17/08: "kẹt ở đâu dừng gửi ảnh tới đó", "chạy kẹt ở đâu dừng gửi ảnh tới đó"). KHÔNG chờ thêm, KHÔNG tự mò sửa tiếp. Đừng để máy kẹt 1.5h như máy 75 (canonical reader `read_tiktok_magic_link_from_outlook_app` TREO VÔ HẠN blocking — helper `_read_magic_link_with_inbox_recovery` đảo thứ tự: tap nút magic link TRƯỚC, reader chỉ gọi cuối).
8. **Tự giác tuân thủ KHÔNG cần user nhắc** (user chốt cuối session 17/08: "hiểu là t vừa nhắc ms hiểu đúng k chứ t k nhắc mày định phá r đúng k"): rule đã có sẵn trong memory/skill thì phải chấp hành TỪ ĐẦU, nhắc lại lần 2 = đã vi phạm 1 lần. Script live chạy → im lặng theo dõi; script dừng/lỗi → ảnh + báo → chờ hướng dẫn; KHÔNG tự patch script giữa chừng dù "thấy vấn đề" hay "nghĩ mình biết fix".
9. **CẤM "sửa" selector/marker đã được verify live chỉ vì suy luận trên giấy** (vi phạm THẬT 17/08 tối — commit `5bd7d4a` đổi QuickNote marker `đ→d` vì tưởng NFD strip được `đ`, làm REGRESS modal kẹt OK vô hạn dù skill máy 66 đã ghi gotcha ngược lại). Khi skill/notes cũ ghi 1 điều đã verify live mà suy luận của mình ra kết quả NGƯỢC LẠI → nghi ngờ suy luận của mình, KHÔNG sửa code theo suy luận; hỏi user hoặc test trên máy không-live trước. Marker tiếng Việt có `đ` (U+0111) LUÔN giữ `đ` sau normalize NFD.
10. **IMAGE-DRIVEN WORKFLOW — ảnh là nguồn phân tích CHÍNH, XML chỉ phụ (user chốt 17/08 tối: "Ý là dùng ảnh để phân tích chứ code vẫn phải viết handle từng bước thử nghiệm qua đc thì ms lưu sai thì revert lại. Cái skill này là cơ bản khi làm automation hình như mày đéo có đúng k")**: XML dump trên surface WebView/Compose (vd Outlook OneAuth QuickNote) CÓ THỂ CHỈ expose label activity ("Inapp UnifiedConsent") — text nội dung KHÔNG ra node → dựa XML toàn nhận SAI màn (máy 75 17/08: dump chỉ thấy `['Inapp UnifiedConsent','60%','19:16']` trong khi ảnh là QuickNote đầy đủ). Vòng lặp đúng cho mọi bước UI: (1) screencap → vision_analyze đọc ảnh (màn gì, nút ở tọa độ nào) → (2) gửi ảnh + mô tả + đề xuất → user duyệt → (3) ENCODE handler vào script (tọa độ/selector từ ẢNH, không từ XML trống) → (4) chạy test → **QUA được mới commit, FAIL thì REVERT** — không giữ code chưa verify. Kết hợp XML (khi có text node) + ảnh xác nhận chéo; ảnh là nguồn sự thật khi 2 nguồn mâu thuẫn. ⚠️ **MỌI ảnh capture dọc đường đều gửi user kiểm tra tiến độ (user 17/08: "Chụp ảnh tới đâu cũng gửi vào đây cho t kiểm tra tiến độ")** — KHÔNG chỉ gửi ảnh lỗi cuối; ảnh giữa chừng (màn vừa đổi sau mỗi tap) cũng phải gửi kèm mô tả màn hiện tại để user bám tiến độ. Khi user hỏi "trước màn này là màn gì? có chụp k?" → trace log timestamp + các ảnh script tự chụp (`screenshots_social/75_*.png`) để dựng chuỗi màn, gửi TẤT CẢ ảnh liên quan (không chỉ ảnh mới nhất).
11. **THAO TÁC TAY PHẢI KÈM HANDLE SCRIPT NGAY (17/08 đêm)**: Khi kiểm tra hoặc thử nghiệm một thao tác bằng tay (nhập text, tap button), PHẢI chuyển đổi và encode ngay thành code logic chuẩn trong canonical script/recovery helper, kiểm tra cú pháp và commit. CẤM để script bị thiếu handler dẫn đến phải lặp lại thao tác tay.
12. **Xử lý OTP lỗi & Ngày sinh (DOB) trên TikTok Reg (2026-08-17 máy 78):**
    - Khi TikTok overlay màn hình DatePicker đè lên lỗi *"Nhập đúng mã PIN"*, nút "Tiếp tục" của ngày sinh sẽ bị backend khóa logic -> phải bấm Back/tự động detect lỗi -> tap nút "Gửi lại mã" -> lấy OTP mới từ Graph API -> điền mã mới.
    - Nút "Tiếp tục" ở màn hình Ngày sinh: phải tap đúng tâm nút `(y1 + y2) // 2` (tọa độ y=1788) qua ATX JSON-RPC thay vì mép trên.
13. **Cơ chế Ticket Session của Magic-Link TikTok (2026-08-17 máy 75):**
    - TUYỆT ĐỐI CẤM force-stop / đóng app TikTok khi đang ở màn hình *"Kiểm tra hộp thư của bạn"*. Khi app bị đóng, Ticket phiên đăng ký lưu trong RAM của `SignUpOrLoginActivity` bị hủy -> khi deeplink kích hoạt, TikTok báo lỗi *"Đã xảy ra lỗi. Hãy đảm bảo sử dụng cùng thiết bị bạn đã sử dụng để gửi email xác minh."* App TikTok phải được giữ nguyên chạy nền trong suốt quá trình xác thực link.

User phản ứng rất mạnh khi agent tự đoán tọa độ/tự lòng vòng thay vì hỏi. Hai mệnh đề bắt buộc cho live device work (Hotmail/Outlook, reg, feed...):

1. **Bước nào bấm không qua được → GỬI ẢNH LIỀN** — không tự thử tọa độ lòng vòng. Ảnh = `screencap` + gửi MEDIA: kèm mô tả: màn gì, bước nào đang kẹt, đã thử gì. User nhìn ảnh là biết ngay (user am hiểu UI, nhìn 1 phát ra tọa độ đúng).
2. **Bước quan trọng → chờ user duyệt rồi mới chạy tiếp** — khi user yêu cầu "từng bước một", chạy 1 bước → gửi ảnh → dừng chờ "được/chạy tiếp" → mới làm bước sau. KHÔNG tự ý chạy tiếp chuỗi.
3. **CẤM bật auto-rotate / xoay màn** (user: "t căm thù cái đó vl") — xem NO-ROTATION GUARD trong `hotmail-outlook-automation`.

Pattern sai bị phạt: tap tay đoán nhiều tọa độ liên tiếp mà không gửi ảnh; lòng vòng 5-10 bước không hỏi; để máy rơi vào trạng thái xoay ngang.

Bổ sung 2026-08-16 (user phạt "mày cứ tự sửa gặp lỗi chỗ nào script k qua đc ms đc gọi tao"):
- **KHÔNG tự sửa script giữa live run.** Script đã build/duyệt thì chạy nguyên trạng; lỗi mới phát sinh trên máy → gửi ảnh + báo user, user hướng dẫn cách đúng, SAU ĐÓ mới handle vào script (code + test + skill). Không tự "sửa nhanh cho qua" rồi chạy tiếp.
- **Fail giữa chừng → resume từ màn hiện tại** (`--resume` nếu script hỗ trợ, vd `social_reg_v1.py <stt> --resume --email <mail>`), KHÔNG chạy lại từ đầu — chạy lại từ đầu phá state đã đi qua (OTP đã dùng, màn đã qua) và tốn thời gian.
- Máy kẹt ở màn giữa flow (vd màn đặt password TikTok sau DOB) → gọi đúng hàm xử lý bước đó (`fill_birthday`/`fill_password_and_login`...) ở trạng thái hiện tại, không reset.
- **Batch reg chạy SONG SONG bình thường** (chỉ login/add-mail hotmail mới tuần tự) — sau khi login hotmail xong hết, chạy `_run_all_targets.py --full-scope-takeover` một lần; máy nào FAILED thì xem log riêng từng STT (`/d/Taadaa/runtime/kibe/artifacts/runs/social-batch-all/<ts>/batch_1/stt_<n>/stdout.log`) rồi mới gọi user nếu cần.
- **Quy tắc về Trạng thái Màn hình khi Thành công / Thất bại (User chốt 19/08 & 20/08):**
  - **SUCCESS:** Script tự động dọn dẹp, đóng app và đưa thiết bị về màn hình chính (Home).
  - **FAIL / Kẹt lỗi (Giữ hiện trường có thời hạn 15 phút):** Ban đầu GIỮ NGUYÊN HIỆN TRƯỜNG trên thiết bị để phục vụ AI Auto-Recovery đọc ảnh/XML xử lý. **TIMEOUT 15 PHÚT (900s):** Nếu sau 15 phút không ai can thiệp hoặc AI không giải phóng được màn hình lỗi, script/watchdog BẮT BUỘC tự động `am force-stop` đóng app và gửi phím `KEYCODE_HOME` đưa máy về Home an toàn để tránh ngâm màn hình/sáng máy gây checkpoint/chai pin.
  - **Follow Hook Timeout/Fail:** Timeout 15p hoặc bị nhả follow -> Dừng ngay + Cooldown riêng nick + Force-stop TikTok + Về Home.
  - **Không chế thêm bước dọn dẹp riêng trước ca nuôi:** Ca nuôi acc (TikTok feed) vốn đã có sẵn bước preflight tự động dọn app rác và đưa máy về Home trước khi swipe.
  - **Lọc nguồn Gmail sạch (`gmail_clean_v2.xlsx`):** Mail chỉ được ghi vào `gmail_clean_v2.xlsx` khi đã reg thành công và xác thực xong -> `_detect_clean.py` chỉ việc so khớp bốc mail chưa có trong `taikhoan_dat_v2_updated .xlsx`, không cần kiểm tra Inbox rườm rà.
  - **Không tự chế cơ chế lock/unlock thiết bị:** Tuân thủ triệt để rule Lock CHỈ KHI USER RA LỆNH; cron schedule và automation scripts không tự ý tạo device lock chặn ca nuôi.
  - **Chống lỗi Quoting trong PowerShell launcher:** Tránh dùng PowerShell multi-line here-string (`@'...'@`) khi nhúng script Python trong `.ps1`, dùng one-liner dạng `python -c "import sys, ...; (cond or sys.exit('msg')); ..."` để tránh lỗi parse cú pháp.

## 3. Rule Lock — lock/unlock CHỈ khi user ra lệnh (user rule 2026-08-16, áp dụng ALL repo D:\Taadaa)

> "T ra lệnh ms đc lock hoặc unlock. Còn cấm auto lock, chỉ đc auto unlock khi success"

Ba mệnh đề bắt buộc ở MỌI repo automation (automation-core, Tiktok-video, Tiktok_Reg,
tiktok-log-in, register gmail, tiktok-follow, gan-proxy, tiktok-add-bao-mat-f2a, feed...):

1. **Lock/Unlock CHỈ khi user ra lệnh** — không bao giờ tự động.
2. **CẤM auto lock** — mọi `acquire_device_lock` mặc định `user_authorized=False`
   (no-op lease, KHÔNG tạo lock file; không lock tồn tại → chạy không lock).
3. **Auto-unlock CHỈ khi success** — fail/manual-review/abnormal exit GIỮ lock
   (status `handoff`) chặn re-run; chỉ success (DONE) mới release. Cơ chế có sẵn:
   success → `_release_leases()`; không DONE → `_hold_leases_for_recovery()`.

Cách user bật lock cho 1 batch: set env `CODEX_DEVICE_LOCK_DIR` (default
`C:\Users\Kibe\.codex\device-locks`) hoặc param `-LockRoot` → runner pass
`--lock-root` → nhưng vì `user_authorized=False` nên vẫn KHÔNG tạo lock mới — nó
chỉ tôn trọng lock user đã tạo (từ chối nếu bị khóa). Lock thật chỉ tồn tại khi
user chủ động tạo (vd qua script release/acquire tay hoặc `DEVICE_LOCK_ENABLED=1`
cho bản Tiktok_Reg cũ).

**Bổ sung 16/08 (máy 4 mất data + user phạt):** trong `tiktok-luot nuoi acc`
multi-machine feed, toàn bộ cơ chế device-lock/prior-evidence đã bị **XOÁ HẸT**
(agent không được tự ý thêm lại `device_lock_paths` import hay hàm prior-evidence
— `NameError: device_lock_paths` khi chạy thật là do code cũ dùng hàm không
import; user chọn xoá cả cơ chế thay vì fix). Hệ quả: máy fail lần trước tự chạy
lại mỗi lần cron, không còn `recovery_lock_handoff.json` skip. Chi tiết ở
`tiktok-feed-session` references/2026-08-16-swipe-recovery-3session.md.

Quét "all repo đã nhận rule chưa" (đã chạy 2026-08-16): xem recipe đầy đủ ở
skill `automation-core-consumer` mục Device Lock Policy (phân loại wrapper-vs-bản
riêng, grep `user_authorized`, commit `5891817` Tiktok_Reg default True→False,
`6fa3d13` tiktok-add-bao-mat-f2a +user_authorized=False ×4).

**16/08 tối — user CHỐT đổi rule lock (đã plan-audit, đang implement):** lock = **mutex thuần** cho scheduler run-lock — chạy thì lock, xong gỡ hết (success/fail/block/crash đều gỡ). Tránh lock chết ăn lần chạy sau. Bảo vệ "1 máy 1 script 1 lúc" vẫn nguyên trong lúc chạy. Nguồn lock-death THẬT = scheduler-level lock (`automation-core scheduler/base.py:298` default `user_authorized=True`); consumer repos đã `user_authorized=False` (unlocked). Triển khai: kwarg `release_on_terminal` (default **False** opt-in) + CHỈ scheduler truyền True; recovery FAILED_LOCKED retention GIỮ NGUYÊN; retry hôm sau = intentional. Chi tiết thiết kế + test map: skill `automation-core-development` Phase 5 + `references/release-on-terminal-lock-2026-08-16.md`.

**IMPLEMENTED 2026-08-16** (commits `ded3e9b`/`c000af7`/`c12519d` trên branch `codex/release-always-lock`): scheduler run lock giờ tự gỡ trên MỌI outcome kể cả FAILED_LOCKED — state.json giữ `failed-locked` làm report trail, máy fail sẽ retry slot kế tiếp (retry daily vô hạn là intentional; muốn ngừng thì gỡ device khỏi roster). Lock do operator tạo (CLI lock open/inspect/list) và recovery FAILED_LOCKED retention KHÔNG đổi. Full suite 574 pass + 1 pre-existing fail.

## 5. VPN GATE — máy mapped bắt buộc VPN, không VPN = KHÔNG chạy (user chốt 2026-08-17, bổ sung 2026-08-18)

> User (17/08): "Tóm lại k bật vpn thì k đc chạy, phải reboot để cho gan proxy thử bật vpn cho máy đó (reboot 1-2 lần tránh loop lỗi do gan proxy) r ms cho chạy"
> User (18/08): "Gate yêu cầu vpn là đúng nhưng nếu máy đó k có quy định vpn trong ganproxy thì thoải mái chạy vì k proxy = k bắt buộc có vpn"

**Rule farm-wide (mọi repo automation dưới `D:\Taadaa`):**
1. **Máy có proxy được gán trong mapping workbook host (cột proXy có giá trị hợp lệ)** → BẮT BUỘC VPN (`tun0` UP) trước khi chạy bất kỳ flow nào (feed/follow/login/reg/2FA...). Không VPN = không chạy.
2. **Máy không có proxy trong workbook (cột proXy trống / None / rỗng, ví dụ Máy 77, 78, 79)** → Cho phép chạy trực tiếp (Direct IP / unmapped bypass), `vpn_required = False`, KHÔNG bắt buộc có VPN.
3. **So khớp VPN Status case-insensitive**: Hàm core `require_android_vpn` trả về `result = 'connected'` (chữ thường). Consumer scripts PHẢI chuẩn hóa `status_res.upper()` trước khi so khớp `in ("OK", "PASSED", "CONNECTED", "BYPASSED_UNMAPPED")` để tránh bị chặn nhầm.
4. **Popup Vi Changer ("No LSPosed access !!!") là BÌNH THƯỜNG (User chốt 18/08)**: Khi mở Vi Changer hoặc gán proxy, popup *"No LSPosed access !!!"* hiển thị là hành vi bình thường của app, KHÔNG PHẢI LỖI. Tuyệt đối không phán đoán lỗi do popup này.
5. **Dọn stale lock khi tiến trình watcher/gan-proxy bị kẹt (MemoryError)**: Khi tiến trình ngầm (như `gan_proxy_fleet.py`) bị crash/leak RAM bỏ dở lock file (`machine_<N>.lock.json`) ở trạng thái running/blocked mà owner PID không còn hoạt động, dọn dẹp đích danh lock file của máy để mở đường cho cron runner (feed/follow).
5. **VPN fail khi đang chạy (với máy có proxy)** → recovery ladder: GanProxy reassign → chờ watcher bật VPN → soft-reboot 1 lần → verify lại VPN → vẫn fail mới BLOCK.
3. **Mapping workbook PHẢI resolve theo host config** — `DEFAULT_PROXY_MAPPING` KHÔNG được
   hardcode `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx` (bug 17/08: admin host 200+
   resolve mapping kibe → serial admin không có trong mapping → `required=False` → **bỏ qua check
   VPN → máy không VPN vẫn chạy**). Dùng `automation_core.preflight.resolve_proxy_mapping_path()`
   (theo `TAADAA_HOST_CONFIG` workbook_root) + **fail-closed** (thiếu file mapping host → raise,
   không fallback kibe, không exempt nhầm).
- Core: `automation_core 0.4.46+` có `resolve_proxy_mapping_path()`;
  consumer: `require_vichanger_connected(..., recover=True)` gọi `recover_missing_android_vpn`.
- Commit pattern đã dùng 17/08: `fix(vpn): host-aware proxy-mapping resolution (fail-closed)` —
  áp cho core + từng consumer repo (tiktok-luot nuoi acc, tiktok-log-in, add-bao-mat,
  add mail khoi phuc, register gmail, Hotmail, gan-proxy). Scan hết repo:
  `grep -rln "PROXYgandienthoai.xlsx" --include=*.py .` (loại venv/site-packages/.git).
- CHÚ Ý: `resolve_proxy_mapping_path` trong core KHÔNG thể import taadaa_host (core không biết
  consumer) — nó tự parse `TAADAA_HOST_CONFIG` YAML đơn giản (đọc key `workbook_root`) giống
  `taadaa_host._load_yaml_simple`, fail-closed nếu thiếu host config/file.
- **FAIL-OPEN TRAP — gate bọc `except Exception` + log "non-fatal" = gate TẮT NGẦM (verified 18/08, commit c465eb9):** cherry-pick VPN gate vào `preflight_concurrency_gate` thiếu 2 constant definition (`VICHANGER_PROXY_MAPPING_PATH`, `VICHANGER_SERIAL_HEADERS`) mà upstream 5057f8b định nghĩa kèm → `NameError` giữa chạy → dính nhánh `except Exception as exc: log("vpn preflight check skipped (non-fatal)")` → **toàn batch chạy KHÔNG có VPN gate, log chỉ 1 dòng "skipped"** — đúng failure mode §5 cấm. Luật: mọi gate an toàn (VPN/proxy/lock/workbook) PHẢI fail-closed — lỗi check = BLOCK + raise, CẤM except-generic-skip quanh gate. Khi review/patch code gate: scan `except Exception` quanh call site + grep định nghĩa constant được dùng (`grep -n "<NAME>\s*=" file` — 0 assignment = NameError chắc chắn).
- **Cherry-pick commit cũ = mang pattern CŨ đã bị rule thay thế (18/08):** upstream 5057f8b (27/07) có TRƯỚC fix §5 fail-closed (17/08) → hardcode mapping path cũ thay vì `resolve_proxy_mapping_path()`; file fallback cũ không còn tồn tại trên host. Cherry-pick code gate từ commit cũ PHẢI verify theo rule HIỆN TẠI, không theo commit gốc. Procedure review đầy đủ: skill `cherry-pick-review` + `references/2026-08-18-cherry-pick-vpn-gate.md`.

## 5b. VPN GATE — GET_IP broadcast false-positive & chẩn đoán chéo trước khi kết luận "proxy dead" (21/08)
- **Retry 3 lần (commit `3a715bb` automation-core):** `am broadcast -a vn.vichanger.app.GET_IP -n vn.vichanger.app/.AdbCaller` ĐÔI KHI trả `result=0` hoặc ADB timeout dù proxy thật vẫn sống (ViChanger bận / app bị kill / broadcast không kịp phản hồi). `check_android_vpn` (`preflight.py`) giờ thử tối đa 3 lần cách nhau 2s — CHỈ `allowed=False`/block khi cả 3 fail. Bản 1 retry (bắt buộc thêm `import time` — thiếu import = NameError).
- **CẤM kết luận "proxy chết" từ 1 broadcast fail** (máy 4 từng bị dừng oan 17:36 dù proxy mobi4 sống). Chẩn đoán chéo bắt buộc:
  1. Test proxy từ PC qua `requests` với cred **URL-encode bắt buộc** (`#`→`%23`, `!`→`%21`; raw `http://mobi4:TaadaaMobi#2026!@test.taadaa.click:5104` chết vì `#` = fragment → `InvalidURL`). Gọi `http://api.ipify.org`, timeout 12s.
  2. Device: `am start -a android.intent.action.VIEW -d 'https://api.ipify.org'` + screencap + vision đọc IP public.
  3. IP proxy PC == IP device → proxy SỐNG; lỗi nằm ở broadcast/ADB timeout, không phải proxy.
- **Đọc IP qua broadcast đúng cách:** `am broadcast -a vn.vichanger.app.GET_IP -n vn.vichanger.app/.AdbCaller` (có `-n` component) trả `result=200, data="<ip>"` — KHÔNG dùng dạng thiếu `-n` (trả `result=0` không có data).

## 6. CẤM tự ý sửa code/flag/lệnh ngoài scope (user rule 16/08 — phạt nặng 2 lần trong 1 session)

> ⚠️ **SKILL.md ĐÃ ĐẠT TRẦN 100k KÝ TỰ — nội dung mới từ session 20-21/08/2026 (AI-Recovery Step-0 Guards, Ad = Swipe-Up, Device-Lock Guard, GET_IP retry, Revert handler nhiễu) được lưu tại `references/vichanger-get-ip-retry-and-proxy-verification-20260821.md`. Bắt buộc đọc reference này khi làm việc liên quan AI Auto-Recovery / VPN hardening / proxy verify.**
> "T đéo hề yêu cầu mày làm device lock" / "script nó đã hoàn chỉnh chỉ việc làm lại cái cron" / "đéo mượn mày tự chế prepare"

Ba lỗi pattern bị phạt trong session canary máy 4/6 (16/08) — CẤM lặp lại:

1. **CẤM tự sửa code để "fix lỗi" khi chạy thật** — canary chạy gặp `NameError: device_lock_paths` → agent tự thêm import vào `core/device_lock.py` + `multi_machine_feed_session.py` mà KHÔNG hỏi. User: "t đéo hề yêu cầu mày làm device lock". Kể cả "fix 1 dòng import" cũng phải HỎI TRƯỚC — vì user có thể chọn hướng khác (ở đây: xoá hết cơ chế lock).
2. **CẤM tự thêm flag/đổi lệnh chạy** — agent tự thêm `--prepare-tiktok` vào lệnh canary (script chuẩn đã có bước prepare qua automation-core). Chạy canary PHẢI giống hệt lệnh đã chạy OK trước đó, chỉ thêm flag khi user yêu cầu.
- **CẤM tự chạy lệnh phá hoại trên máy thật** — `pm clear --cache-only` / `pm clear` (xem reference feed — CẤM TUYỆT ĐỐI, làm mất data nick).
- **CẤM force-stop / close recent app đang trong luồng xác thực magic-link / OAuth token** (Finding 17/08 máy 75): force-stop app TikTok khi đang chờ magic link làm hủy session RAM nội bộ -> mở link lên bị lỗi bảo mật thiết bị *"Hãy đảm bảo sử dụng cùng thiết bị bạn đã sử dụng để gửi email xác minh."*
- **CẤM tự ý XÓA dữ liệu/output/file render** (16/08 — user phạt "Lại tự ý xoá mà đéo hỏi mày giỡn mặt hả") — agent xóa 40 mp4 đã render của folder 363 mà KHÔNG hỏi → mất công render lại. **batch_render.py tự SKIP video đã có output** (`task.output.exists() && !overwrite → skip`) — gặp folder dang dở: chạy LẠI là nó tự skip phần xong, KHÔNG cần xóa gì. Mọi hành động xóa (mp4, avatar, folder, data) phải hỏi user trước.

Nguyên tắc chung: **code/script/lệnh nào user chưa yêu cầu sửa → mặc định KHÔNG sửa.** Lỗi chạy thật → gửi ảnh/log + báo user + hỏi hướng xử lý (fix hay xoá hay bỏ qua) → CHỈ làm sau khi user quyết. Không "sửa nhanh cho chạy tiếp".

## 7. ATX-primary là chuẩn đọc UI toàn farm (16/08)

- **`capture_ui_xml` (automation_core.ui, atx-agent port 7912) là PRIMARY** đọc UI trên máy yếu — shell `uiautomator dump`/`dumpsys window` chỉ là fallback (xem skill `atx-agent-primary-ui-xml`).
- **`dumpsys window mCurrentFocus` KHÔNG đáng tin để quyết "kẹt splash"**: TikTok giữ splash activity window trong khi feed đã render → `get_focused_activity` phải ATX-primary (đọc package từ XML) rồi mới dumpsys. Luôn đối chiếu screencap thật trước khi kết luận màn hình.
- **Popup TikTok phân loại (Xử lý ở cấp độ CORE `automation-core`):**
  - **Popup quyền Vị trí hệ thống (PackageInstaller):** Phải tick chọn checkbox *"Không hỏi lại"* (`do_not_ask_checkbox`) rồi bấm nút *"TỪ CHỐI"*. Handle ở cấp `automation-core` (`benign_popup.py`) với marker `access this device's location` / `truy cập vị trí`.
  - **Popup quyền Danh bạ / Bạn bè trong app TikTok** (*"Để kết nối với những người bạn biết..."*): Bấm *"Không cho phép"* (handle ở cấp `automation-core` `tiktok_popup.py`).
  - Cả 2 popup này đều là popup chung cấp độ core (`automation_core/tiktok/benign_popup.py`), KHÔNG viết xử lý riêng lẻ ở tầng feed runner.
  - Cấp quyền/add số điện thoại → dismiss ở automation-core (`tiktok_popup.py`, `tiktok/benign_popup.py`); CTA mua hàng ("Mua ngay") → pass ở repo consumer (`feed_swipe_smoke.py` shop_cta_close). Tên `gemphonefarm_blind_popup` là tên cũ — để im.
- **Lệch Cột Serial trong Workbook Nguồn (taikhoan_dat_v2_updated.xlsx):** Khi nhập nhầm ngày tháng vào cột 10 (cột Serial) đẩy Serial thật sang cột 11 → script sync `sync-safe-workbook.py` đọc nhầm ngày tháng vào `taikhoan_run_safe.xlsx` gây `invalid ADB serial` → Sửa file gốc `taikhoan_dat_v2_updated .xlsx` rồi chạy lại sync để cập nhật `taikhoan_run_safe.xlsx`.
- **Cơ chế Fallback Swipe khi gặp màn hình lạ lúc nuôi acc:** Khi đang trong vòng lặp lướt feed mà gặp màn hình không xác định (không phải login/challenge), script thực hiện vuốt lướt qua thử 2 lần như thao tác nuôi bình thường để tự thoát màn hình lạ.
- **Xử lý Bàn phím ảo ảo giác (Keyboard Ghost Detection):** Khi `dumpsys input_method` báo bàn phím mở nhưng trên UI thực tế không có bàn phím (đang xem video feed bình thường), gửi phím Back không làm mất trạng thái bàn phím trên system service -> script phải kiểm tra lại UI XML và screencap trước khi đánh giá `keyboard cleanup command failed`.
- **Tap nút popup chính xác:** screencap có thể scale khác màn thật (720×1280 vs 1080×1920) → tọa độ vision scale SAI. Dùng `capture_ui_xml` (ATX) parse `bounds` node theo text → tap trung tâm bounds (verified 16/08 popup contacts máy 6). Chi tiết: `tiktok-feed-session` references/2026-08-16-swipe-recovery-3session.md.
- **Popup contacts permission text đa dạng:** text thật "Để kết nối với những người bạn biết trên TikTok, hãy cho phép truy cập vào danh bạ..." KHÔNG chứa marker cũ `"cho phép tiktok truy cập vào danh bạ"` (thiếu "tiktok") → core rule miss. Marker linh hoạt: `("cho phép truy cập vào danh bạ", "kết nối với những người bạn biết")`.
- **Popup "Follow bạn" / Thẻ "Người bạn có thể biết" trên Feed — BẤM "Follow lại" (User chốt 19/08)**: Khi lướt feed gặp thẻ đề xuất tài khoản / người bạn có thể biết kèm nút `Follow lại`, user chốt: **bấm nút "Follow lại"** (`follow_back_suggestion`), không bấm "Không quan tâm". Encode vào `GEMPHONEFARM_BLIND_POPUP_RULES` (feed_swipe_smoke.py) dạng: detect `//node[contains(@text, "Người mà bạn có thể biết") or contains(@text, "Follow lại")]` → tap `//node[@text="Follow lại" or @content-desc="Follow lại"]` (loop=True).
- ⚠️ **Hiểu nhầm nguy hiểm — user nói "bấm follow lại" trên ảnh popup = TAP button trên máy, KHÔNG phải chạy follow script**: session 17/08 agent hiểu nhầm thành chạy `run_follow.py --machine 33` (follow script) → CONFIG_ERROR vô nghĩa. Quy tắc: user nhắc hành động kèm ngữ cảnh ảnh popup đang gửi ("bấm follow lại", "bấm không quan tâm") → thao tác TAY theo hướng dẫn trên màn hình ĐÓ, encode action đó vào handler popup; KHÔNG kết nối với script follow riêng.

## 8. CẤU TRÚC FOLDER TikN.xlsx (16/08 — agent lú 2 lần, user phạt "mày bị lú quá")

> "Folder video chính là tương đương folder videotiktok nuoi acc. Còn video gốc = video goc trong folder"

- **`Folder Video` (cột) = folder OUTPUT** — nằm trong `D:\TIKTOK-videonuoinick` (kết quả render).
- **`video gốc` (cột) = folder NGUỒN** — nằm trong `D:\video goc` (video download để render + tạo avatar).
- **Mỗi Tik (Tik1/Tik2/Tik3) có DẢI output RIÊNG trong TV** — số folder có thể TRÙNG giữa các Tik (vd Tik3 máy 1-20 → Folder Video 3..155 nhìn giống Tik1/Tik2). ĐÓ KHÔNG PHẢI CONFLICT, không đè dữ liệu — mỗi Tik là dải riêng. Luôn đọc cặp (Folder Video ↔ video gốc) từ chính workbook, KHÔNG suy luận từ số.
- Tik3 máy N: Folder Video = 8N−5, video gốc = 160+N.
- `D:\video goc` folder ≥305 có thể KHÔNG có video (chỉ avatar.jpg) — đó là folder OUTPUT Tik3; video thật của chúng nằm trong TV.
- Hashtag/Keyword của TikN phải lấy từ nguồn (sheet "Hashtag theo Folder" theo folder nguồn), KHÔNG bê từ Tik khác — đã verify Tik3 80/80 khớp nguồn.
- Đã commit vào PROJECT_RULES.md (Tiktok-video) `72cc9a7` + memory.

## 9. Pipeline render Tik3/TikN (16/08 — `scripts/tik3_multi_batch.py`)

- **Lệnh chuẩn:** `python -m tik3_multi_batch --workbook <TikN.xlsx> --start-output <folder đầu> --start-source <nguồn đầu> --count <N> --min-videos 45 --parallel 1 --allow-existing-output --resume-complete --execute` (chạy từ `D:\Taadaa\Tiktok-video` + `PYTHONPATH=scripts`).
- **`--min-videos`:** folder nguồn phải ≥45 video mới render (folder đã chuẩn bị từ khâu tải → không cần bận tâm).
- **`--resume-complete`:** folder output đã đủ 45 mp4 → chỉ ghi workbook, KHÔNG render lại.
- **`--allow-existing-output`:** folder có mp4 dang dở (<45) → batch_render tự SKIP video đã có, chỉ render phần thiếu. **Bắt buộc dùng khi folder còn file** — không dùng thì script chặn ("Output folder da co N mp4, khong ghi de").
- **`--parallel 1`:** user yêu cầu render chạy worker 1 thôi.
- **Báo cáo:** user yêu cầu "xong 10 folder thì báo 1 lần" — chạy `--count 10` mỗi lần, xong batch mới báo, không spam giữa chừng.
- Script cần cột `sttvideo` nhưng Tik3.xlsx có `Folder Video` → đã thêm fallback trong `find_headers` (nếu thiếu sttvideo thì dùng folder video).
- `source_map_workbook` KHÔNG dùng được cho Tik3 (map theo output−1 nhưng dải folder không liên tục do +8/máy) — cứ để script tự tăng source từ `--start-source`.
- Render copy avatar từ video goc → output ("COPY avatar: avatar.jpg"). Tạo avatar mới ở video goc TRƯỚC render để output tự nhận avatar mới; avatar output đã render thì tạo lại bằng `avatar-tv-fallback` (gọi make_representative_avatar trực tiếp trên TV folder).

**Download video gốc — THỨ TỰ CHỐT 16/08 (user đảo quyết định giữa session):** discovery song song tải BỊ user chặn — "V cứ discovery trc tải sau t sợ discovery nhanh quá bị chặn k". Thứ tự bắt buộc: **discovery xong (đủ 480 sources, ~80 niche) → mới chạy download**. Cơ chế tăng dần "làm tới đâu down tới đó" VẪN hợp lệ khi user xác nhận lại muốn chạy sớm (không mặc định tự chạy song song): `source_pool_builder.py --auto-discover --resume-discovery` ghi checkpoint `<rt>/sources.partial.json` SAU MỖI NICHE (đã đủ 80 niche sau ~10/80). Extract `sources` list → `sources.json` → chạy `download_by_niche.py --start-folder <folder thiếu đầu> --total-folders 480 --sources sources.json --state-db state.db`; `state.db` nhớ folder đã xử lý → chạy lại khi discovery bổ sung sẽ tự skip. Giai đoạn đầu download im lặng (tải whisper model/probe source, có thể 3-5 phút không output) — kiểm tra process + whisper_models/ thay vì kill vội.

**Download chi tiết (16/08 — đã verify chạy thật):**
- **`--min-videos 45` là chuẩn user** (đã giảm từ 50; docs/download-manager.md còn ghi ">=50" là CŨ — đừng theo). Script default 42. User: "folder nguồn đã đủ video từ khâu tải nên cứ render/không cần bận tâm min".
- **Dependencies bắt buộc trong venv:** `ddgs` (autodiscover TikTok/IG), `faster-whisper` (audio gate tiếng Việt — model "small" tự tải lần đầu ~460MB vào `<rt>/whisper_models/`), `instaloader` (IG followers). Thiếu → cài: `pip install -U ddgs faster-whisper instaloader`.
- **YouTube 403 rải rác (HTTP Error 403: Forbidden) = bot-check theo IP**, không phải lỗi code — folder chỉ đạt ~41/50 video → INSUFFICIENT_POOL. yt-dlp retry sau có thể qua (transient).
- **PITFALL state.db giữ platform cũ (16/08):** folder fail `INSUFFICIENT_POOL` để lại row trong state.db với `platform=instagram` (hoặc platform cũ). Sửa `sources.json` (bỏ IG) rồi chạy lại mà chỉ reset `status='pending'` → script dòng `platform = folder_row["platform"] if ... in PLATFORMS` dùng LẠI platform cũ → fail y hệt. Reset SẠCH: `UPDATE folders SET status='pending', platform='pending', source_channel=NULL, video_count=0 WHERE folder_num=<N>`.
- **Dẹp nguồn theo quyết định user:** IG bị 403 (Instagram chặn API, không phải lỗi yt-dlp — bản 2026.07.04 là mới nhất) → lọc `platform != 'instagram'` khỏi sources; kênh nhà nước (vd @vtv24) → user yêu cầu bỏ, lọc theo URL.
- **Cookies browser:** Chrome/Edge KHÔNG đọc được (Chromium App-Bound/DPAPI — yt-dlp issue #7271). Firefox đọc được nhưng cần profile có log-in YouTube (default-release này không có youtube cookies → vô dụng).
- **yt-dlp 2026.07.04 = bản mới nhất (PyPI + official); TikTok extractor bị "marked as broken":** `tiktok.com/search?q=` → `Unsupported URL`, `tiktok.com/tag/` → `No working app info` — chỉ tải được TikTok channel URL đã biết (3 sources hoạt động). IG 403 cố định là Instagram chặn API (không có bản fix) → user: "k có thì dẹp". YouTube 403 = transient rate-limit, retry sau qua.
- **Auto-discover thiên YouTube nặng:** ddgs tìm YT ra nhiều (120), TikTok/IG ít (3/16) — tỉ lệ 1:40. PLATFORM_TARGET 50:50 nhưng discovery thực tế lệch; user: "K quan trọng miễn đủ nguồn là đc". Nếu dẹp 1 platform phải sửa CẢ `PLATFORMS`/`PLATFORM_TARGET` trong download_by_niche.py (không chỉ sources.json) vì `choose_platform` chọn theo ratio — IG chưa đạt target sẽ bị chọn dù không có source.
- **PLATFORM_TARGET bản CUỐI (16/08 đêm, commit `241424f`):** `PLATFORMS=("youtube",)`, `PLATFORM_TARGET={"youtube": 1.0}` — **TikTok dẹp hẳn khỏi PLATFORMS**. Lý do: kể cả target 0.15, TikTok có ratio 0 (chưa đạt 15%) vẫn được `choose_platform` (chọn theo ratio count/target) lựa cho tới khi đủ chỉ tiêu → mọi folder gán TikTok fail vì chỉ 3-5 TikTok sources (yt-dlp TikTok extractor broken). YouTube 67 kênh qualified = nguồn chạy thật.
- **`--continue-on-insufficient` (flag MỚI, commit `241424f`):** mặc định INSUFFICIENT_POOL → `run_folder` return False → toàn batch `return 2` DỪNG HẲN. Flag này skip folder thiếu nguồn và chạy tiếp folder kế — đúng ý user "kênh nào đủ điều kiện thì down luôn". Bắt buộc thêm vào mọi lệnh download batch dài.
- **Discovery PHẢI chạy `--qualify-videos` (user: "Tưởng discovery nó đã kiểm tra kênh đủ điều kiện r chứ"):** `--auto-discover` thiếu flag này ghi source KHÔNG có `qualified_video_count` (0/176!) → kênh 4-video lọt pool → download fail đủ loại niche. Bước qualify chuẩn: copy `sources.partial.json` → JSONL manifest → `source_pool_builder --source-manifest <jsonl> --qualify-videos --qualification-parallel 4 --min-videos 45 --max-videos 65 --max-candidates-per-source 200 --min-sources-per-platform 0 --output sources.qualified.json`. **`--min-sources-per-platform 0` BẮT BUỘC** (nếu không → exit 2 `INSUFFICIENT_SOURCE_POOL: thieu platform ['instagram']` dù đã dẹp IG). Kết quả 70/70 sources qualified ≥45 video (YT 67 + TT 3) → **download CHỈ nhận `sources.qualified.json`**.
- **`qualify_videos` probe từng video qua YouTube → chậm + rate-limit** ("not available" hàng loạt = chặn tạm, không phải video chết) — chạy nền kiên nhẫn. **Sau khi sửa code phải KILL + restart loop** (process giữ module cũ — patch không có hiệu lực trên process đang chạy).
- **Chạy song song discovery+qualify+download (user quyết định cuối "Sao k làm song song"):** loop scripts `qualify-loop-20260816.py` / `download-loop-20260816.py` tại `D:\CodexRuntime\tiktok-video\` — copy partial → qualify/download → sleep 120s → lặp tới khi discovery xong; state.db skip folder đã xử lý nên nhiều vòng an toàn. Không tăng worker (spam IP).
- **INSUFFICIENT_POOL `best_candidates` nhỏ (vd 4) = NGUỒN NICHE CHƯA ĐỦ, không phải bug** — folder 299 (dongluc) fail vì niche chỉ có 1 channel YouTube nhỏ (4 video pass) dù đã sửa hết logic. Chẩn đoán: best_candidates nhỏ + sources_checked thấp → chờ discovery thêm sources rồi chạy lại, đừng sửa script tiếp (vòng lặp vô ích). Folder có nguồn lớn (vd 298/khcc → @vtv24) pass 65/65 cùng lúc đó.
- **CẤM tăng worker download/discovery** — user từ chối 2 lần vì sợ spam IP: "Tăng lên rủi ro spam ip à thế thì thôi" / "Download cũng k đc tăng worker sợ dính spam ip à". Giữ default: discovery `--audience-parallel 4`, download `--parallel 1`, render `--parallel 1`.
- **Thứ tự CHỐT CUỐI (16/08 đêm, user đảo quyết định 3 lần trong session — mệnh đề cuối thắng):** discovery + qualify + download **CHẠY SONG SONG** ("Ủa phải discovery xong ms down à, tưởng làm tới đâu down tới đó" → "Sao k làm song song"). KHÔNG chờ discovery xong. Cơ chế: checkpoint `sources.partial.json` ghi sau mỗi niche → qualify-loop refresh qualified.json → download-loop tải (cả 2 loop ở `D:\CodexRuntime\tiktok-video\`); state.db skip folder đã xử lý. User từng chặn song song vì sợ bị chặn IP, sau đó đổi ý — nếu phân vân, HỎI user, đừng tự chốt.
**Proxy pool DÙNG ĐƯỢC cho download (user đảo 16/08 đêm: "đụ mẹ nuôi tiktok liên quan cặc gì youtube")** — IP mobile farm proxy cho download YouTube KHÔNG đụng farming TikTok. File: `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx` (76 proxy, cột 'proXy'). **PITFALL format:** xlsx ghi `host:port:user:pass` (vd `test.taadaa.click:5101:mobi1:admin@1`) — URL đúng là `http://user:pass@host:port` = `http://mobi1:admin@1@test.taadaa.click:5101`; prefix `http://` thẳng vào raw → "Failed to resolve '1'". `next_proxy()` trong download_by_niche.py đã xử lý format này. **PITFALL test song song:** proxy panel giới hạn kết nối đồng thời — test 8 worker → 407 auth giả (proxy vẫn sống, user chụp dashboard MobiProxy status xanh). Test proxy PHẢI đơn lẻ. **PITFALL video test:** dùng video nước ngoài phổ biến (Rick Astley) → "other"/NA vì IP di động VN bị chặn — test bằng video/channel VN (vd `@vuadaubepvietnam`) mới đại diện.
- **Camoufox cookies = GIẢI PHÁP bot-check YouTube cuối cùng (16/08 đêm, commit `810cf96`, VERIFIED tải thật):** "Sign in to confirm you're not a bot" là chặn theo CLIENT (thiếu fingerprint + không giải JS challenge) — đổi IP/proxy KHÔNG hết. Fix: `pip install camoufox[geoip]` + `python -m camoufox fetch` → mở `https://www.youtube.com` headless (fingerprint thật) → export cookies Netscape → `download_by_niche.py --cookies-file youtube-cookies-netscape.txt` (cookies tươi qua được; video Numb + channel flat OK). **Cookies sống vài giờ** — download bắt đầu fail "Sign in" lại → chạy lại script Camoufox lấy cookies mới. Chi tiết + script: `references/youtube-botcheck-camoufox-cookies.md`.
- **Dead-end đã thử (đừng mất công lại):** deno + `--js-runtimes` + `youtube:jsc=deno` vẫn "n challenge solving failed" (thiếu solver đầy đủ); Chrome/Edge cookies bị App-Bound chặn; Firefox đọc được nhưng profile không có YouTube session; **Camoufox bắt googlevideo URL trực tiếp = dead end** (`sabr.malformed_config` — SABR segment cần Range headers đặc biệt, tải qua requests/ffmpeg fail; module `scripts/browser_download.py` đã viết nhưng đường ăn chắc là cookies→yt-dlp).
- **`target_counts` trong `source_pool_builder.py` cứng 50/25/25 — phải sửa cùng lúc dẹp platform (commit `3f2ad84`):** nếu không, discovery dừng khi YT đạt target 120 dù cần 480. Sửa → `{"tiktok":0,"instagram":0,"youtube":total}` + `--min-sources-per-platform 0`. Kết quả: 514 sources (454 YT).
- **`youtube_profile` regex handle Unicode (commit `241424f`):** `@[A-Za-z0-9._-]+` fail với handle tiếng Việt có dấu (`@KhámPháBếpViệt` → None → manifest dòng 1 "source phai la URL profile/channel public"). Sửa thành `@[\w.-]+`.
- **PITFALL patch fuzzy làm lệch indent file dài** (download_by_niche.py/source_pool_builder.py trúng nhiều lần 16/08): khi block >20 dòng thay bằng python script sửa theo index dòng thay vì patch fuzzy — verify `py_compile` sau mỗi lần.

**Báo cáo batch dài (16/08 preference):** "gặp lỗi thì báo còn k cứ silent đi" — chạy nền im lặng, CHỈ nhắn khi lỗi thật / cần user / milestone được yêu cầu (vd "xong 10 folder báo 1 lần"). Dùng `notify_on_complete` cho mọi batch dài, không poll progress spam giữa chừng.

## 10. Rule avatar folder (16/08 — user: "đưa rule này lên ưu tiên cao nhất")

1. **Người** (face detect Haar) → 2. **Động vật** (YOLO theo niche animal: yeuthucung/xemeo/chocanh/thucung) → 3. **Frame sáng** crop 512×512. **Avatar kênh thật KHÔNG dùng nữa** (bỏ khỏi bước 1 trong `make_avatar_for_folder`; commit `662ff58`).
- `_make_avatar.py` dùng `subject_type="auto"` + `subject_model=yolov8n.pt` (commit `0b2fc7d`) — auto cho phép người → động vật → fallback.
- **CẤM đụng avatar đã tạo** — user: "những cái đã sửa r thì đừng đụng tới nữa" (chỉ áp rule mới cho folder CHƯA tạo).
- `D:\video goc` folder ≥298 thường KHÔNG có video (chỉ avatar.jpg cũ) → tạo avatar bằng TV-fallback scripts (`avatar-tv-fallback-20260816.py` gọi make_representative_avatar lên TV folder).

## 11. User yêu cầu "áp rule mọi session mọi repo" — chèn 3 tầng (2026-08-17)

Khi user nói "làm sao bất kỳ session nào bất kỳ repo nào từ h phải nhận đúng rule/skill t yêu cầu" (sau khi phạt nhiều lần vì agent không tuân thủ STOP GATE), KHÔNG chỉ patch skill — phải chèn 3 tầng:

1. **Cấp repo (bắt buộc, mạnh nhất)**: chèn block rule (STOP GATE) vào **AGENTS.md + PROJECT_RULES.md của MỌI farm repo** (10 repo: Tiktok_Reg, Hotmail, Tiktok-video, tiktok-log-in, tiktok-follow, tiktok-add-bao-mat-f2a, tiktok-luot nuoi acc, gan-proxy, register gmail, automation-core). AGENTS.md được Hermes/Codex/Claude đọc ở cwd → mọi session mở trong repo đều nhận rule, KHÔNG phụ thuộc skill library. Dùng skill `rule-file-append` (EOL-preserving + baseline + backup + verify). Chèn SAU heading đầu, giữ EOL từng file.
2. **Cấp skill**: chèn STOP GATE vào skill liên quan + skill all-repo (`taadaa-farm-ops-rules`) — agent load skill đúng là có rule.
3. **Cấp memory**: dòng STOP GATE rút gọn trong memory → nhét thẳng vào context mỗi lượt.
4. **CẦN THÊM "BẮT BUỘC LOAD SKILL" vào AGENTS.md** (đã làm 17/08): khối `## 🧑💻 BẮT BUỘC LOAD SKILL` liệt kê skill repo nào phải load trước khi làm việc — đảm bảo session không chỉ có rule mà còn biết phải nạp skill chứa selector/flow/canary.
5. **Commit + push từng repo** (user duyệt "commit đi"): commit message tiếng Việt, push mọi repo có upstream; repo non-fast-forward (`tiktok-luot nuoi acc`) → stash WIP workstream khác + rebase + resolve conflict + pop stash (xem `git-worktree-merge-reconciliation` §30).
6. **Inject-verify**: mở session Hermes mới trong repo (`hermes chat -q "STOP GATE điều 5,6 nói gì?"`) — agent trả lời đúng block = rule đã vào system prompt. (Lưu ý: session mới có thể quét toàn `/d/Taadaa` chậm — prompt phải bảo đọc AGENTS.md ở cwd.)

## 12. Cấu trúc thư mục gốc D:\Taadaa & Cơ chế đồng bộ đa máy (Kibe ↔ Admin qua OneDrive Junction)

Thư mục gốc `D:\Taadaa` là thư mục cha chứa toàn bộ hạ tầng farm Taadaa:
- **Các repo con:** `automation-core`, `Hotmail`, `register gmail`, `Tiktok_Reg`, `tiktok-add-bao-mat-f2a`, `tiktok-follow`, `tiktok-log-in`, `tiktok-luot nuoi acc`, `Tiktok-video`, `add mail khoi phuc`, `open claw`, `site ban hang clone`, `AI-Tools`, `Hermes`, `gan-proxy`.
- **Hạ tầng dùng chung:**
  - `machine-config/`: chứa `kibe.yaml` (dải 1–80) và `admin.yaml` (dải 200–999).
  - `python-envs/automation/`: venv Python dùng chung cho mọi repo consumer.
  - `runtime/<host>/`: chứa runtime state, lock mutex, screenshots lỗi (tuyệt đối không để trong repo Git).
  - `tools/`: các script điều phối chung (`taadaa_host.py`).
  - `BACKUP_ALL/`: nơi gom các file rác, file tạm, worktrees cũ (giữ root `D:\Taadaa` sạch sẽ).

**Cơ chế đồng bộ Realtime máy Kibe ↔ Admin (`D:\OneDrive\Taadaa_Sync_Shared`):**
1. Trên máy Kibe: `D:\OneDrive\Taadaa_Sync_Shared` dùng Windows Directory Junction (`mklink /J`) trỏ thẳng vào `D:\Taadaa\machine-config` và `D:\Taadaa\tools` + chứa các file rules gốc (`AGENTS.md`, `HANDOFF.md`, `HERMES_SUBAGENT_RULES.md`).
2. Trên máy Admin (chỉ cần chạy 1 lần):
   - Mở OneDrive: `D:\OneDrive\Taadaa_Sync_Shared\link_shared_to_admin.bat` → tự động tạo Junction Link 2 chiều vào `D:\Taadaa` của Admin và set `TAADAA_HOST_CONFIG="D:\Taadaa\machine-config\admin.yaml"`.
   - Chạy `clone_all_repos.bat` → tự động clone 15 repo với đúng branch chuẩn về `D:\Taadaa`.
3. Bất kỳ thay đổi nào về rule, config, tool trên Kibe sẽ được OneDrive sync tức thì sang Admin. Code repo cập nhật độc lập qua `git pull`.
- Chi tiết hướng dẫn & script bootstrap: `references/multi-host-onedrive-junction-sync.md`.

## 16. PREFLIGHT DEVICE LOCK GATE & WATCHDOG NHẮC LOCK (20/08/2026)
1. **Thứ tự Preflight bắt buộc toàn farm (Device Lock Gate -> VPN Gate -> Lock Portrait)**:
   - Trước khi bất kỳ tiến trình nào chạy trên máy (nuôi acc, follow, reg TikTok, Hotmail, 2FA...):
     - Bước 1: **Device Lock Gate** (`acquire_device_lock(user_authorized=False)`): Nếu máy có lock active do User tạo (`machine_<N>.lock.json`) $\rightarrow$ BẮT BUỘC KHÔNG CAN THIỆP, Safe-Skip máy đó ngay lập tức kèm thông báo rõ ràng.
     - Bước 2: **VPN Gate** (`check_android_vpn(verify_live_ip=True)`): Máy có proxy bắt buộc VPN `tun0` UP và IP thật hợp lệ.
     - Bước 3: **Lock Portrait**: Khóa kép màn hình dọc.
2. **Watchdog nhắc nhở chống quên (2 tiếng/lần)**:
   - Hermes cron `device-locks-watchdog` chạy script `watch_device_locks.py` mỗi 2 tiếng (`every 2h`).
   - Quét thư mục `~/.codex/device-locks/`, nếu có máy đang lock $\ge 2$ tiếng $\rightarrow$ Gửi báo cáo tổng hợp danh sách máy đang lock về nhóm Telegram riêng **Report máy lock** (`-5518578446`) để nhắc mở khóa kịp thời.
3. **Quy tắc Git Sync Đa Máy (Pull Rebase Trước -> Push Sau)**:
   - Vì farm chạy đa máy (Kibe ↔ Admin), trước khi push bất kỳ code nào (kể cả Auto-Recovery): BẮT BUỘC `git fetch origin` $\rightarrow$ `git pull --rebase origin <branch>` $\rightarrow$ mới `git push origin <branch>` để chống reject non-fast-forward.
- Chi tiết toàn bộ kiến trúc & implementation trên 11 repo: `references/all-repo-preflight-lock-vpn-enforcement-20260820.md`.
   - Quét `~/.codex/device-locks/`; **GỬI BÁO CÁO KHI CÓ BẤT KỲ LOCK NÀO** (`if locks: send_telegram_alert(...)`), KHÔNG chờ quá hạn — user chốt 21/08 ("Thấy sai sai r đó"): máy đang lock phải được nhắc mỗi chu kỳ; threshold 120 phút chỉ gắn nhãn ⚠️ QUÁ HẠN.
   - Nhóm riêng **Report Lock Device** (`-5518578446`) — không spam Farm Alerts (bị trôi).
3. **ROLLOUT lock+VPN gate TOÀN BỘ repo (21/08 — user: "Cả yêu cầu vpn thông ms đc chạy ... làm ở all script đi")**:
   - **Chuẩn 2 gate bắt buộc mọi entrypoint đụng máy**: (1) `acquire_device_lock(user_authorized=False)` → bắt `DeviceLockNeedsUserDecision` → BLOCK + báo rõ owner/project/PID, KHÔNG can thiệp; (2) `require_android_vpn(required=serial_is_mapped_in_workbook(resolve_proxy_mapping_path(), serial, serial_headers=("phoneId","deviceId","serial")))` fail-closed.
   - **Audit nhanh mọi repo**: `git grep -lE 'acquire_device_lock|DeviceLockNeedsUserDecision' -- '*.py' ':!runs/**'` và `git grep -lE 'require_vichanger_connected|require_android_vpn|verify_live_ip' -- '*.py' ':!runs/**'` (git grep tôn trọng .gitignore, tránh `.ai-runs/`/`build/`/venv rác).
   - **Gap thật đã vá 21/08**: `tiktok-follow/run_follow.py` trước đó KHÔNG có gate nào trong source (chỉ trong test) — thêm cả 2; `tiktok-log-in` thêm VPN vào `account_inventory.py`/`password_change.py`/`collect_apk_evidence.py`; `tiktok-add-bao-mat-f2a` thêm VPN phase_a/b/pilot; `Tiktok_Reg` thêm VPN `tiktok_login_v1`/`tiktok_login_live_email_v1`/`tiktok_reg_live_email_v1`. **TODO còn thiếu VPN**: `Tiktok_Reg/calibrate.py`, `gmail_machine_audit.py`, `_run_all_targets.py`, `scripts/run_social_batch_deferred.py` (lock có, VPN chưa).
   - **PITFALL chèn gate vào file lớn**: patch fuzzy nhiều lần làm HỎNG INDENT file 800+ dòng (`account_inventory.py`, `password_change.py` 21/08, lỗi `IndentationError` chồng nhau) → đúng cách: `git checkout -- <file>` rồi chèn 1 lần bằng python script anchor chính xác (hoặc patch duy nhất có context độc nhất), luôn `py_compile` sau mỗi bước.
   - **PITFALL biến trùng tên**: gate mới dùng `mapping`/`adb` tràn ra đè biến `mapping` hợp lệ trong `main()` (test CLI fail vì mapping thành `WindowsPath`) → đặt tên `preflight_mapping`/`preflight_adb` riêng.
   - **PITFALL test pre-existing fail**: sau khi sửa code, stash thay đổi (`git stash push -- <files>`) rồi chạy lại test → chứng minh fail có sẵn trên HEAD trước khi đụng test; chỉ cập nhật expectation sau khi xác nhận và khớp chuẩn hiện hành (vd `test_follow_engine` assert 90.0 trong khi chuẩn farm đã `feed_timeout_seconds=900`).
   - Canonical gate block + bảng trạng thái từng repo: `references/preflight-lock-vpn-gates-rollout-20260821.md`.
1. **Quy trình gỡ tài khoản Google Die khỏi máy & Workbook**:
   - Khi tài khoản dính checkpoint *"Xác minh danh tính của bạn"* (Gmail ngắt sync không nhận OTP TikTok), gọi `remove_blocked_google_account_from_device(serial, gmail)` từ `add mail khoi phuc/run_add_recovery.py` để vào `Settings -> Accounts -> Xóa tài khoản` và đồng thời xóa row khỏi `gmail_clean_v2.xlsx`.
   - **QUY TẮC AN TOÀN TUYỆT ĐỐI**: Chỉ xóa đúng tài khoản die theo chuỗi email cụ thể (tài khoản vừa tạo bị checkpoint), **TUYỆT ĐỐI CẤM đụng chạm hay xóa nhầm các tài khoản nuôi / tài khoản Google cũ khác** trên thiết bị và trong workbook.
   - Chi tiết: `references/google-account-cleanup-and-antiban-20260818.md`.
2. **Các yếu tố Anti-Ban đã nâng cấp trong `gmail_reg_v10.py`**:
   - **Nâng jitter tọa độ tap**: Tăng từ $\pm4..6$px lên $\pm8..20$px để mô phỏng chính xác phân bố ngón tay người dùng thật, phá vỡ footprint tọa độ cơ học.
   - **Khử quy luật Username (Random Salt & Variations)**: Bổ sung 3 chế độ đảo Họ/Tên + chèn chuỗi ký tự ngẫu nhiên (salt 2-3 ký tự) $\rightarrow$ chấm dứt hoàn toàn pattern cố định `Họ+Tên+ddmmyy+STT` bị Google AI gom nhóm.
   - **Tăng độ trễ gõ phím người thật (`human_type`)**: Điều chỉnh khoảng trễ giữa các ký tự lên 60–220ms ngẫu nhiên + nghỉ sau khi gõ 0.4–0.8s.
   - **Tăng khoảng nghỉ suy nghĩ (Thinking Delay)**: Nâng `rand_short` lên 1.8–3.5s, `rand_medium` lên 3.2–5.8s, `rand_long` lên 5.0–9.0s.
3. **Quy tắc gửi ảnh lỗi (BẮT BUỘC số máy [MÁY XX])**:
   - Dòng 1: `MEDIA:<đường dẫn tuyệt đối dùng backslash>`
   - Dòng 2: `### [MÁY XX] - <Tên màn hình / Nhóm lỗi>`
   - Bắt buộc kiểm tra avatar/hòm thư đúng email trước khi kết luận kẹt OTP.
4. **Kiểm tra Targets TikTok Reg**:
   - Trước khi đưa máy vào batch TikTok Reg, phải kiểm tra kỹ dòng dữ liệu nguồn xem máy đó thực sự có mail mới reg hay không (tránh kéo nhầm các dòng Hotmail/rác cũ ở cuối file `gmail_clean_v2.xlsx`).

## 21. QUY TẮC CẶP PROXY CHIA SẺ & LỰA CHỌN MÁY CHẠY BATCH (18/08)
1. **Phát hiện cấu trúc Proxy Pairs trên Farm (80 máy)**:
   - Các cổng proxy mobi được map dùng chung theo từng cặp máy (khoảng cách lệch 38 máy): `[1, 39]`, `[2, 40]`, `[3, 41]`, `[4, 42]`, ..., `[38, 76]`.
   - Chi tiết toàn bộ danh sách cặp: `references/farm-shared-proxy-pairs-and-batch-selection.md`.
2. **Quy tắc Anti-Overlap Batch Selection**:
   - **TUYỆT ĐỐI CẤM chọn 2 máy cùng cặp proxy trong cùng 1 batch chạy reg**.
   - Khi chọn N máy cho batch reg Gmail / TikTok: Phải nhóm theo proxy và chỉ lấy tối đa 1 máy cho mỗi cổng proxy trong cùng một lượt chạy để tránh tình trạng trùng IP làm Google gắn cờ spam và khóa tài khoản hàng loạt.

## 30. WORKFLOW CRON NUÔI ACC TOÀN DIỆN & UPLOAD HOOK PHIÊN CUỐI (User chốt 19/08)
1. **Chu Kỳ 3 Ca Nuôi Acc Mỗi Ngày**:
   - Ca sáng: `06:00 – 10:00`
   - Ca trưa/chiều: `12:30 – 16:30`
   - Ca tối: `19:00 – 23:00`
   - Mỗi ca gồm **3 phiên lướt nuôi (`session_index` = 1, 2, 3)**.
2. **Quy Trình 4 Bước Khép Kín Trong 1 Phiên**:
   - **Bước 1 (Preflight & Prepare)**: Check VPN `tun0`, mở TikTok, vào Account Switcher chọn đúng Nick theo Row của ca (`account_row_index`), tự xử lý quyền hệ thống (tick không hỏi lại + từ chối).
   - **Bước 2 (Feed Session Smoke)**: Lướt 3 Tab (FYP 85%, Following 8%, Friends 7%) + Watch delay + Tự vượt popup in-app tự nhiên (Live 6-14s tap X, Shop 3-7s tap X, Repost 2-4s tap X, CTA vuốt lướt, Thẻ gợi ý bấm Follow lại) + Verify profile chỉ khớp username Excel.
   - **Bước 3 (Follow Hook & Cơ chế Timeout 15 Phút)**:
     - Sau khi lướt feed thành công $\rightarrow$ Kiểm tra cooldown nếu nick chưa bị nhả follow hôm nay thì chạy follow.
     - **CƠ CHẾ TIMEOUT 15 PHÚT (900s) -> FORCE-STOP VỀ HOME (Commit `c022fac`)**: Subprocess follow hook được bọc timeout cứng 900s (15 phút). Khi quá thời gian (`TimeoutExpired`), hệ thống tự động:
       1. Kill subprocess python đang chạy để tránh treo tiến trình ngầm / leak tài nguyên.
       2. Gọi ADB: `am force-stop com.ss.android.ugc.trill` để tắt ứng dụng TikTok.
       3. Gửi phím `KEYCODE_HOME` (key 3) đưa máy về màn hình chính sạch sẽ, tránh ngâm máy lâu bị TikTok gắn cờ bot.
       4. Cách ly cooldown riêng nick đó trong ngày (`follow_failed = True`).
     - Nếu phát hiện bị nhả follow sau vuốt $\rightarrow$ Dừng ngay, cách ly dừng follow cả ngày cho **RIÊNG nick đó** (`follow_state_<m>_row_<r>.json`), các nick khác trên máy vẫn chạy bình thường.
   - **Bước 4 (Upload Hook — ĐĂNG VIDEO PHIÊN CUỐI CA)**:
     - Tự động kích hoạt ở **Phiên cuối cùng của ca (`session_index == 3`)**.
     - Đọc workbook tương ứng (`Tik1.xlsx`, `Tik2.xlsx`, `tik3.xlsx`... theo Row), lấy thư mục video (`folder_video`), tính số video tiếp theo (`posted_count + 1`).
     - Kiểm tra file video đã render sẵn (`D:\TIKTOK-videonuoinick\<folder>\<next>.mp4`). Nếu file hợp lệ $\rightarrow$ chạy `tiktok-video` đăng bài; nếu chưa có $\rightarrow$ Safe-skip không nghẽn luồng.
     - Dọn dẹp ứng dụng chạy ngầm và đưa máy về Home an toàn.
3. **Phân Biệt Rõ Trạng Thái Giữ Hiện Trường vs Timeout Về Home**:
   - **Lỗi UI / Popup lạ trong lúc lướt Feed**: Giữ nguyên hiện trường (`preserve_blocker_screen = True`) để AI Auto-Recovery đọc ảnh/XML phân tích và vá code.
   - **Quá hạn Timeout (15 phút) ở Follow / Upload Hook hoặc bị Nhả Follow**: Bắt buộc force-stop TikTok và về Home ngay lập tức để giải phóng máy.
- Chi tiết: `references/full-tiktok-feed-and-upload-workflow-20260819.md`.

## 31. TIẾP TỤC PHIÊN "LÀM TIẾP" & PREFLIGHT CA SÁNG 06:00 (chốt 20/08)
Khi user nhắn **"Làm tiếp"** (hoặc "tiếp tục") **không kèm ngữ cảnh** trong nhóm Farm Alerts / chat điều hành:
1. **KHÔNG hỏi lại user — tự khôi phục ngữ cảnh bằng `session_search`** (user bực khi hỏi điều tự check được): `session_search(sort="newest")` → tìm session Farm Alerts + session điều hành gần nhất → đọc bookend cuối (5-6 tin cuối) để biết việc đang dở / kết luận cuối / commit cuối.
2. **Verify 3 repo** (automation-core, tiktok-luot nuoi acc, tiktok-follow): `git status -s` sạch (bỏ qua untracked `.hermes/plans/*`, `HANDOFF*.md` — là file bình thường), `git log --oneline -3` khớp commit cuối session trước = đã push xong.
3. **Preflight ca sáng 06:00 trước khi báo "sẵn sàng":**
   - `adb devices` đủ 80/80 `device`; thư mục device-locks không có `machine_<N>.lock.json` active.
   - `cronjob list` — 10 job `last_status: ok`, runner tick mới nhất (< 15 phút). **Cron output silent (empty output) = healthy theo thiết kế** (silent watchdog), KHÔNG phải lỗi.
   - follow_state: file mới dạng `follow_state_<m>_row_<r>.json` (per-nick); `grep -l '"follow_failed": true' runs/state/*.json` → nick nào dính hôm nay; `follow_failed_date` cũ tự reset theo `_roll_day` sang ngày mới. File cũ không hậu tố `_row_` là di sản migration, bỏ qua.
   - LANES đúng ngày: `blocks.py` — **ngày chẵn = Lane A (2,4,2) → Row 2/4/6, ngày lẻ = Lane B (1,3,1) → Row 1/3/5**; jitter ±25 phút. Nick Row 1 dính follow_failed từ test tối qua KHÔNG ảnh hưởng ca sáng ngày chẵn (chạy Row 2).
   - Picker `phase9-staging-picker` (`0 6 * * *`) đã scheduled 06:00.
4. **PITFALL cron-state report.jsonl stale:** `D:\Taadaa\runtime\kibe\cron-state\report.jsonl` có thể chứa entry `FAILED_LOCKED`/`FEED_FAIL` CŨ (mtime nhiều ngày trước) — **CẤM đọc tail rồi kết luận máy đang lỗi**. Kiểm tra `ls -l --time-style='+%Y-%m-%d %H:%M:%S'` mtime file TRƯỚC khi tin nội dung. Nguồn alert thật: cron output dir `~/AppData/Local/hermes/cron/output/` hoặc nhóm Farm Alerts.
- Chi tiết quy trình + lệnh đầy đủ: `references/session-continuation-and-morning-preflight-20260820.md`.

## Pitfalls

- OTP dùng chung = KHÔNG BAO GIỜ song song login/add-mail; cảnh báo này nằm cả trong skill `hotmail-outlook-automation`.
## 13. PREFLIGHT SCHEDULE CHECK (Bắt buộc trước mọi batch chạy tay/live — user chốt 2026-08-18)
Trước khi chạy bất kỳ batch tác vụ nào trên farm (Reg TikTok, Hotmail login, Add mail khôi phục, Register Gmail, Upload video, Reconcile...):
1. **TỰ ĐỘNG KIỂM TRA LỊCH CRON NUÔI ACC:** Agent BẮT BUỘC tự động kiểm tra manifest nuôi acc (`D:\Taadaa\runtime\kibe\cron-state\manifests\<ngày>\active_manifest.json` qua skill `farm-schedule-preflight-check`) TRƯỚC KHI KHỞI CHẠY.
2. **KHOẢNG ĐỆM AN TOÀN ≥ 1 TIẾNG:** Chỉ được chọn và chạy trên các máy hoàn toàn rảnh trong suốt thời gian chạy batch và **cách ca nuôi acc kế tiếp tối thiểu 60 phút**.
3. **CẤM CHẠY TRÙNG MÁY:** Tuyệt đối không khởi chạy batch trên các máy đang trong ca nuôi hoặc sắp vào ca < 60 phút.
4. **USER CHỈ CẦN BẢO "CHẠY SCRIPT XXX" / "CHỌN N MÁY CHẠY XXX" → AGENT TỰ CHECK LỊCH RỒI CHẠY NGAY:** User không cần phải nhắc "kiểm tra lịch", agent tự động check máy rảnh $\rightarrow$ lọc danh sách máy an toàn $\rightarrow$ KHỞI CHẠY NGAY (background, stagger ngẫu nhiên theo machine_launch). Tuyệt đối KHÔNG dừng lại ở bước chuẩn bị/hỏi "có chạy không" làm chậm trễ. Khi gặp lỗi máy nào $\rightarrow$ dừng máy đó, chụp ảnh gửi user, chỉ lock khi user yêu cầu để debug sau.

## 14. NO-ROTATION / LOCK PORTRAIT MỌI THIẾT BỊ TRƯỚC KHI AUTOMATION
1. **TUYỆT ĐỐI CẤM TỰ ĐỘNG XOAY MÀN HÌNH / LANDSCAPE TRÊN TOÀN BỘ MÁY FARM:**
   - Mọi máy trước khi khởi chạy bất kỳ script nào (Gmail, TikTok, Hotmail,...) PHẢI được khóa cứng ở chế độ dọc (Portrait).
   - **CƠ CHẾ KHÓA KÉP (Dual-layer lock)**: Trên các dòng Samsung TouchWiz/OneUI cũ, `settings put` có thể bị hệ điều hành reset về 1 khi WebView/Onboarding activity khởi tạo. Do đó, hàm `lock_portrait_rotation` trong `automation-core` và mọi script PHẢI chạy cả `settings put` lẫn `content insert`:
     - `settings put system accelerometer_rotation 0` (tắt tự động xoay)
     - `settings put system user_rotation 0` (khóa góc xoay về 0 độ portrait)
     - `content insert --uri content://settings/system --bind name:s:accelerometer_rotation --bind value:i:0`
     - `content insert --uri content://settings/system --bind name:s:user_rotation --bind value:i:0`
   - Tuyệt đối không để bất kỳ bước UI nào làm lật xoay ngang màn hình thiết bị.

## 15. BÁO CÁO LỖI BATCH, DEVICE LOCK & TEST-RESUME WORKFLOW
1. **Khóa máy lỗi ngay lập tức (Lock retention — Bắt buộc khi có lệnh/phát hiện lỗi)**:
   - Khi phát hiện lỗi hoặc user yêu cầu kiểm tra/khoá máy, BẮT BUỘC thực hiện acquire device lock (`status='blocked'`, `user_authorized=True`) cho TẤT CẢ các máy bị lỗi để cô lập hiện trường, ngăn chặn các cron tick kế tiếp nhảy vào chạy đè làm mất vết lỗi.
2. **Quy tắc Test Resume trước khi Unlock (CẤM mở khóa trước khi test pass — User phạt 18/08 & 19/08)**:
   - Khi fix handler/logic cho một nhóm lỗi: **TUYỆT ĐỐI CẤM TỰ Ý MỞ KHÓA HÀNG LOẠT**.
   - Fix chỗ nào $\rightarrow$ BẮT BUỘC chạy test resume / re-run ngay trên chính máy bị lỗi tại hiện trường đang đứng để kiểm chứng thực tế script có vượt qua được màn hình lỗi đó hay không.
   - **BẮT BUỘC CHẠY TIẾP HOÀN THÀNH TOÀN BỘ SCRIPT (User phạt 19/08: "đáng lẽ fix máy lỗi thì khi fix xong qua đc chỗ lỗi phải chạy lại trạng thái hiện tại của nó cho hoàn thành toàn bộ script")**: Sau khi test qua được bước vừa sửa, PHẢI kích hoạt chạy tiếp tục phần còn lại của flow trên máy đó từ trạng thái hiện trường cho đến khi phiên chạy kết thúc trọn vẹn (SUCCESS), tuyệt đối không dừng lại giữa chừng chỉ ở bước test function đơn lẻ rồi bỏ lửng máy.
   - **CHỈ mở khóa máy khi script chạy test THỰC SỰ PASS và hoàn thành phiên thành công**. Nếu test chưa pass hoặc máy chuyển sang kẹt ở màn khác $\rightarrow$ TIẾP TỤC GIỮ LOCK vĩnh viễn cho tới khi xử lý xong.
   - Khi user ra lệnh mở khóa máy cụ thể (vd "Máy 4 mở khoá") $\rightarrow$ chỉ mở khóa duy nhất máy đó.
4. **CẤM tự thoát về Home / đóng app khi lỗi (Giữ nguyên màn hình lỗi — User phạt 18/08)**:
   - Khối `finally / cleanup` của mọi runner (feed, follow, reg,...) khi kết thúc với trạng thái lỗi (`MANUAL_REVIEW`, `FAIL`, `CONFIG_ERROR`) **TUYỆT ĐỐI CẤM tự ý bấm Home hoặc gọi close_all_recent_apps()** làm mất màn hình lỗi; CHỈ ĐƯỢC PHÉP dọn dẹp về Home khi `status == "OK"`.
4. **Reconcile Safety Check giữa Focused Package & UI XML (SystemUI overlay)**:
   - Khi `focused_package` đọc về `com.android.systemui` (do thanh thông báo/overlay) nhưng UI XML dump được đầy đủ và phân loại chính xác là màn hình in-app (`for-you`, `following`, `friends`, `home`, `profile`), `safety_check` phải chấp nhận là TikTok focused thay vì báo `TikTok focus lost`.
5. **Gom nhóm lỗi rõ ràng & Bắt buộc kèm đề xuất hướng xử lý**:
   - Phân loại toàn bộ lỗi theo signature/nhóm màn hình.
   - Gửi ảnh đại diện cho từng nhóm lỗi bằng format `MEDIA:<đường dẫn tuyệt đối>` ở dòng đầu tiên.
   - **BẮT BUỘC KÈM SỐ MÁY [MÁY XX] & ĐỀ XUẤT FIX**: Dòng 2 ghi rõ `[MÁY XX]` (STT thiết bị). Mô tả màn hình từ `vision_analyze` và **bắt buộc kèm đề xuất hướng fix cụ thể** cho từng nhóm để user duyệt trước khi thực thi.
6. **Xử lý Clear Input & Chống gõ sai ký tự trên ô Tìm kiếm UID**:
   - Trước khi gửi lệnh `type_text`, script phải focus vào ô nhập liệu và xóa sạch chuỗi text cũ còn vướng (`KEYCODE_MOVE_END` + phím DEL x N) để tránh dính chữ thừa.
   - Dùng bàn phím hệ thống hoặc cơ chế chèn text an toàn, tránh để bộ gõ tiếng Việt / bàn phím ảo can thiệp làm đảo chữ/nhảy số.
   - Bộ so khớp danh tính sau tìm kiếm (`_exact_search_result_from_xml` & `_classify_exact_profile_action`) phải luôn fail-safe bỏ qua UID không khớp chính xác, không được tap bậy vào profile người lạ.

## 17. XỬ LÝ LỖI & WORKAROUND GMAIL REG VÀ GMS SETUP WIZARD (18/08)
1. **Dọn dẹp sau khi đăng ký thành công (Cleanup to Home):**
   - Khi đăng ký Gmail thành công (cả khi vào thẳng Gmail Home lẫn khi confirm account trong Account List): BẮT BUỘC tự động gọi `close_all_recent_apps` và gửi phím `KEYCODE_HOME` để đóng sạch ứng dụng đang mở, đưa thiết bị về màn hình chính sạch sẽ trước khi kết thúc worker.
   - Toàn bộ tài khoản tạo thành công PHẢI được ghi lập tức vào workbook nguồn `gmail_clean_v2.xlsx` kèm đầy đủ STT, email, password chuẩn `@Ks`, mail khôi phục và DOB.
2. **Màn hình "Tạo một địa chỉ email" (Google Username selection):**
   - Khi Google hiển thị các địa chỉ gợi ý (`user@gmail.com` có sẵn) kèm tùy chọn thứ 3 *"Tạo địa chỉ Gmail của riêng bạn"*:
   - Script phải tick chọn vào RadioButton *"Tạo địa chỉ Gmail của riêng bạn"* $\rightarrow$ chờ ô nhập `username` xuất hiện $\rightarrow$ nhập đúng username theo cấu hình tài khoản $\rightarrow$ bấm nút *"TIẾP THEO"*.
3. **Màn hình Welcome Tour Gmail / Thêm ít nhất một địa chỉ email (Máy 73):**
   - Khi Gmail hiện popup cảnh báo *"Vui lòng thêm ít nhất một địa chỉ email"*:
   - Bước 1: Tap nút **OK** trên popup để đóng dialog.
   - Bước 2: Tap nút *"Thêm địa chỉ email"* (hoặc nút *"ĐƯA TÔI TỚI GMAIL"* ở chính giữa dưới cùng nếu đã có tài khoản).
   - Bước 3: Ở màn hình *"Thiết lập email"*, chọn nhà cung cấp **Google** để vào luồng đăng ký tài khoản.
4. **Màn hình "Phiên của bạn đã kết thúc vì không có hoạt động" (Google Session Timeout - Máy 70):**
   - Tap nút **"THỬ LẠI"** (tọa độ góc dưới bên phải) để reload lại trang đăng nhập/tạo tài khoản của Google và tiếp tục luồng.
5. **Màn hình "Xác minh số điện thoại của bạn" (Google Phone Verification - Máy 41, 56, 60):**
   - Đây là cơ chế chặn xác minh SMS của Google theo IP/thiết bị $\rightarrow$ Skip bỏ qua tài khoản trên máy đó, để cooldown IP hoặc đổi proxy gán mới rồi chạy lại sau.
6. **Mảng `ACCOUNTS` trong script `gmail_reg_v10.py`:**
   - Cần đảm bảo khai báo đầy đủ các slot STT cho toàn bộ dải máy farm (1–80), tránh lỗi crash do thiếu định nghĩa STT 75–80.
7. **Khóa máy đang fix / chạy lại theo lệnh User:**
   - Khi user ra lệnh *"Lock hết máy đang fix đang chạy lại"*: Tạo lock file `machine_<STT>.lock.json` và `serial_<SERIAL>.lock.json` tại `C:\Users\Kibe\.codex\device-locks\` với `user_authorized=True` và `status=running` để bảo vệ tài nguyên tuyệt đối.

## 18. TIKTOK REG PREFLIGHT, FLOW TRANSITIONS & OTP RETRIEVAL (18/08)
1. **So khớp VPN Status hoa-thường & Bỏ qua máy không Proxy**:
   - `require_android_vpn` trả về `result = 'connected'` (viết thường). Script consumer (như `social_reg_v1.py`) phải chuẩn hóa `.upper()` trước khi kiểm tra `in ("OK", "PASSED", "CONNECTED", "BYPASSED_UNMAPPED")` để tránh bị chặn nhầm.
   - Máy có cột proxy trống/None trong workbook mapping (`PROXYgandienthoai.xlsx`) thì `vpn_required = False` (Direct IP unmapped bypass), không bị gate chặn.
2. **Nhận diện Home Feed TikTok vs Trang Profile & Bypass Signup**:
   - Khi mở TikTok ra màn hình Feed video (có tab `Trang chủ`, `Đề xuất`, nút Thả tim, Bình luận,...): Hàm `_is_home_feed_xml` phải nhận diện đúng bằng tổ hợp các marker feed (`trang chu`, `de xuat`, `ban be`, `binh luan`, `chia se`, `viewpager`,...).
   - Ở Bước 2 của `social_reg_v1.py`: Nếu màn hình có tab *Hồ sơ* (`has_profile_tab = True` hoặc `_profile_tab_node` tìm thấy), PHẢI đi luồng chuẩn: `go_to_profile` $\rightarrow$ `open_account_dropdown` $\rightarrow$ `tap_add_account`. Chỉ bypass khi máy đang ở màn login/signup thuần không có tab Hồ sơ.
   - Bước 6 `wait_for_text` phải nhận diện đầy đủ các nhãn popup mới: *"Tiếp tục với email"*, *"Đăng ký TikTok"*, *"Sign up"*.
3. **Màn hình One-tap Login & Popup Điều khoản Onboarding (18/08)**:
   - Khi gặp màn hình *"Tiếp tục với tên @username"* $\rightarrow$ tap link text *"Sử dụng tài khoản khác"* ở dưới cùng để mở form chọn phương thức.
   - Khi gặp popup *"Đồng ý và tiếp tục"* (Terms Onboarding) $\rightarrow$ tap *"Đồng ý và tiếp tục"* để vào app.
   - Chi tiết: `references/tiktok-one-tap-and-onboarding-popups-20260818.md`.
4. **Đồng bộ Serial Workbook `taikhoan_run_safe.xlsx`**:
   - Cột serial trong `taikhoan_run_safe.xlsx` phải luôn khớp 100% với `PROXYgandienthoai.xlsx`. Khi phát hiện dòng ghi nhầm ngày tháng vào cột serial gây `TARGET_INVENTORY_CONFLICT`, phải đồng bộ lại toàn bộ 80 máy ngay.
5. **Xử lý hòm thư Gmail khi lấy mã OTP TikTok Reg**:
   - Khi chuyển sang app Gmail để đọc mã OTP TikTok (`search_tiktok` / `search_verification`), một số máy có thể bị tắt tính năng Auto-Sync hoặc báo *"Không có kết nối"* / *"Tính năng tự động đồng bộ hóa đang tắt"*.
   - **Chẩn đoán Checkpoint Google Identity**: Kiểm tra hòm thư có đúng tài khoản chưa (tap Avatar kiểm tra active email). Nếu Gmail bị tạm ngắt đồng bộ thư, dùng `run_google_live_check` (từ repo `add mail khoi phuc`) để kiểm tra xem tài khoản có bị Google gắn cờ *"Xác minh danh tính của bạn"* (relogin gate) hay không.
   - Khi cần đồng bộ: Thực hiện swipe pull-down từ đỉnh hòm thư hoặc bấm vào thông báo để kích hoạt đồng bộ thư mới về máy.

## 23. CHUỖI TỰ ĐỘNG BAN ĐÊM (REG GMAIL ➔ REG TIKTOK) & ANTI-BOT JITTER (19/08)
1. **Chuỗi Tự Động Ban Đêm (Night Chained Pipeline)**:
   - **Lịch chạy**: Đúng `00:00` hàng ngày qua Hermes Cron `night-chain-reg-gmail-tiktok` (`no_agent: true`, 0 token LLM).
   - **Đích gửi báo cáo**: Nhóm Telegram `Gmai reg` (`-5139245637`).
   - **Luồng tuần tự**: 
     1. `00:00`: Gọi canonical `run_all.ps1` (lọc máy đủ cooldown 5 ngày để reg Gmail).
     2. Xong Gmail: Tự động gọi tiếp `_run_all_targets.py` (tự bốc mail vừa tạo từ `gmail_clean_v2.xlsx` để reg TikTok cho máy còn thiếu).
     3. Gửi **1 báo cáo tổng kết duy nhất** về Telegram khi chuỗi hoàn tất.
2. **Quy tắc Trạng Thái Thiết Bị (Success vs Fail)**:
   - **SUCCESS**: Script tự đóng app, dọn dẹp và đưa máy về Home.
   - **FAIL / LỖI**: GIỮ NGUYÊN HIỆN TRƯỜNG trên thiết bị (không tự ý bấm Home, không tự ý đóng app) để phục vụ kiểm tra và debug.
   - **Không tự ý Lock máy**: Tuyệt đối không tự động tạo device lock chặn ca nuôi 06:00.
3. **Chuẩn Hóa Mặc Định Jitter & Watch Delay (Anti-Bot Farm)**:
   - `DEFAULT_SWIPE_JITTER_PX = 15`: Toạ độ vuốt luôn tự động lệch ngẫu nhiên $\pm 15$px quanh trục chuẩn `(540, 1540) ➔ (540, 620)`.
   - `DEFAULT_MIN_WATCH_SECONDS = 3.0s` & `DEFAULT_MAX_WATCH_SECONDS = 8.0s`: Mỗi video dừng ngẫu nhiên 3–8 giây trước khi vuốt tiếp.
   - `DEFAULT_SWIPE_DURATION_MIN/MAX_MS = 550..750ms`: Tốc độ vuốt ngón tay biến thiên tự nhiên.
4. **Cơ Chế Silent Watchdog của Cron Nuôi Acc**:
   - Các cron runner (`phase9-runner-tiktok-feed`) và watcher (`phase9-watcher-tiktok-feed`) hoạt động ở chế độ `silent (empty output)` khi hệ thống chạy mượt mà, chỉ gửi alert khi có lỗi kẹt máy hoặc crash.

## 24. PHÂN TÍCH LỖI FEED/FOLLOW & BÁO CÁO REALTIME TỪNG MÁY (19/08)
1. **Báo Cáo Lỗi Realtime Từng Máy & Trạng Thái Mở/Khóa (User chốt 19/08)**:
   - Nhóm Telegram báo lỗi chuyên trách: Nhóm **"Farm Alerts"** (`-5373649734`). Chi tiết: `references/farm-alerts-and-realtime-debug-protocol.md`.
   - Khi phát hiện máy lỗi/kẹt trong mọi luồng chạy: Tự động chụp màn hình qua ADB, dùng Pillow vẽ banner đỏ đóng dấu số máy `[MAY XX] - HH:MM DD/MM` ở đỉnh ảnh, và gửi alert ngay về nhóm Farm Alerts kèm caption chi tiết (Script, Acc, Lý do lỗi, Trạng thái: ĐANG MỞ hay ĐANG LOCK).
   - **Quy tắc máy lỗi vẫn chạy tiếp phiên kế tiếp (User chốt 19/08)**: Hết phiên lỗi, sang phiên kế tiếp cùng máy **VẪN TỰ ĐỘNG CHẠY TIẾP BÌNH THƯỜNG** (không tự động skip ngầm theo prior handoff). Chỉ dừng máy khi user ra lệnh LOCK rõ ràng.
2. **Quy Trình Fix Lỗi Máy Thật — Bắt Buộc Chạy Hoàn Thành Toàn Bộ Script (User phạt 19/08: "đáng lẽ fix máy lỗi thì khi fix xong qua đc chỗ lỗi phải chạy lại trạng thái hiện tại của nó cho hoàn thành toàn bộ script")**:
   - Khi debug/fix lỗi trên máy thật: Sau khi sửa code và test qua được bước lỗi, **PHẢI kích hoạt chạy tiếp tục toàn bộ flow từ hiện trường cho đến khi phiên chạy kết thúc trọn vẹn (SUCCESS)**, tuyệt đối không được dừng lại ở bước test function đơn lẻ rồi bỏ lửng máy.
3. **Xử Lý Mất Focus Giả `com.android.systemui` trên Samsung S7**:
   - **Hiện tượng**: TikTok đang mở trọn vẹn ở màn hình Profile/Feed, nhưng `get_focused_activity()` hoặc UI dump đọc trúng node SystemUI trên thanh trạng thái `[0,0][1080,72]` ➔ script báo `TikTok focus lost` và kích hoạt `preserve_blocker_screen` dừng oan.
   - **Xử lý**: Hàm kiểm tra package phải lọc bỏ các node `com.android.systemui`, chỉ xác định focus dựa trên dominant package của app chính (`com.ss.android.ugc.trill`).
4. **Chống Bấm Nhầm Icon "Lượt Xem Hồ Sơ" (`id/ic7`) Khi Tìm Account Switcher**:
   - **Hiện tượng**: Trên giao diện TikTok mới, icon hình 2 người (Lượt xem hồ sơ `id/ic7`, `tv_number`, bounds `[720, 90][840, 210]`) nằm sát cạnh tên hiển thị profile `[366, 72][720, 228]` ➔ Hàm tìm anchor đổi nick `_find_sticky_profile_header` bấm nhầm vào icon này khiến máy đi vào trang *"Số lượt xem hồ sơ"*.
   - **Xử lý**: Loại trừ rõ ràng `id/ic7`, `tv_number`, content-desc *"Số lượt xem hồ sơ"* khi resolve anchor đổi nick. Nếu máy lỡ đang ở trang subpage này, tự động gửi phím Back để thoát về Profile root.
5. **Cơ Chế Pull-to-Refresh Xác Nhận Follow Không Bị Nhả & Thời Gian Đợi Load (User chốt 19/08)**:
   - Động tác vuốt để reload profile sau khi tap Follow trong `verify_follow.py` PHẢI là kéo từ trên xuống (`pull-to-refresh`, $y_1 = 35\%h \rightarrow y_2 = 80\%h$, duration 600ms).
   - **Độ trễ chờ load mạng**: Sau khi vuốt kéo xuống, bắt buộc đợi `sleep_after >= 3.5s` để server TikTok và UI load xong trạng thái nút mới trước khi dump XML xác nhận (tránh đọc vội khi nút chưa kịp cập nhật).
6. **Xử Lý Nick Chưa Có Tên (`+ Thêm tên`) Khi Cần Chuyển Acc & Chế Tên Tiếng Việt (User chốt 19/08)**:
   - Nick mới reg chưa đặt Display Name hiển thị `+ Thêm tên` / `Add name` ở header profile (`id/se2`).
   - CẤM tap vào `@username` để chuyển đổi tài khoản vì bấm `@username` trên TikTok sẽ kích hoạt copy username vào clipboard chứ không mở Account Switcher.
   - Giải pháp chuẩn: Tự động gọi module đặt tên `fill_name(device_id, email)` từ `D:\Taadaa\Tiktok_Reg\social_reg_v1.py` để đặt biệt danh hoàn tất hồ sơ cho nick đó trước (tự tap Thêm tên ➔ nhập name theo quy tắc Việt hóa ➔ Lưu ➔ Xác nhận). Sau khi có Display Name, quay lại trang Profile sẽ có header chuẩn để mở menu Account Switcher chuyển nick bình thường.
   - **Quy tắc tạo tên Việt có dấu gần âm username (`make_tiktok_name`)**: Tự động chuyển đổi prefix username sang tên tiếng Việt có dấu tự nhiên (`kylar` ➔ *Kỳ La*, `kyle` ➔ *Khải*, `lilyan` ➔ *Linh*, `ancil` ➔ *An*, `steven` ➔ *Thịnh*, `alicia` ➔ *Ái*...). Truyền chuỗi tiếng Việt UTF-8 qua Base64 Broadcast của `com.github.uiautomator/.AdbKeyboard` để đảm bảo không mất dấu.
   - **Tương tác trả lời User**: Phải giải thích/tóm tắt bằng tiếng Việt dân dã, trực diện, dễ hiểu (tránh output/trích dẫn toàn tiếng Anh kỹ thuật dài dòng gây khó theo dõi).
   - **Tự động đặt tên Việt khi thiếu display name**: Nick hiện `+ Thêm tên` / `Add name` ➔ tự gọi `fill_name` đặt biệt danh tiếng Việt có dấu (`Kỳ La`, `Linh`, `Thịnh`...) qua ADB Keyboard Base64 trước khi mở Account Switcher (tránh tap nhầm `@username` gây copy text).
   - **Xác thực follow bằng Pull-to-Refresh**: Sau khi tap Follow ➔ kéo từ trên xuống ($y_1 = 35\%h \rightarrow y_2 = 80\%h$) + chờ đủ $\ge 3.5s$ để TikTok load lại trạng thái nút trước khi kiểm tra nhả follow.
   - **Tự động tắt popup "Follow bạn bè của bạn"**: Tự phát hiện và bấm đóng X (`id/e63`) ngay ở cấp độ core (`benign_popup.py`).
7. **Tự Động Tắt Popup "Follow bạn bè của bạn" Ở Cấp Độ Automation-Core (User chốt 19/08)**:
   - Popup *"Follow bạn bè của bạn"* (`id/yhd`, `id/thm`, `id/thb`) PHẢI được xử lý tập trung trong `automation_core/tiktok/benign_popup.py` (`detect_contact_follow_suggestion`).
   - Tự động nhận diện và tap nút đóng `X` (`id/e63`) hoặc nút *"Không quan tâm"* ngay khi xuất hiện, không để popup che khuất trang profile/feed.
8. **Cấu Hình Claude Code CLI Reasoning Max**:
   - Tham số reasoning kịch trần của Claude Code CLI là `--effort max` (hỗ trợ `low`, `medium`, `high`, `xhigh`, `max`), không dùng `high`.

## 25. TỌA ĐỘ VUỐT AN TOÀN & XỬ LÝ CÁC MODAL/POPUP FEED ĐẶC BIỆT (19/08)
1. **Tọa Độ Trục Vuốt An Toàn (Chống chạm nhầm Comment / Shop / Repost)**:
   - **Trục X (Ngang)**: Vuốt ở dải an toàn $X = 400 \rightarrow 480$ (nửa trái màn hình, lệch về bên trái trục giữa) để tránh hoàn toàn cụm nút tương tác bên phải (Like, Bookmark, Repost, Shop card) và avatar.
   - **Trục Y (Dọc)**: Vuốt từ $Y = 1400 \rightarrow 600$ (tránh vùng đáy $Y > 1700$ có ô nhập bình luận/thanh bài đăng lại).
2. **Cơ Chế 2 Lớp Cho CTA Ad & Popup Lạ (User chốt 19/08)**:
   - **Lớp 1 (CTA Matcher)**: Nhận diện tất cả các biến thể CTA (`TIKTOK_CTA_TERMS`: *"Mua ngay", "Tìm hiểu thêm", "Xem ngay", "Cài đặt ngay", "Tải ngay", "Trải nghiệm ngay", "Nhận ngay"*) $\rightarrow$ Tự động swipe lướt qua video tiếp theo.
   - **Lớp 2 (Fallback 2-lượt vuốt)**: Mọi popup lạ / dialog không xác định (`manual-needed:popup`) hoặc blocker không dismiss được $\rightarrow$ Tự động gọi `_swipe_recovery_on_stuck` vuốt lướt 1–2 lần để thoát trước khi báo manual.
3. **Phân Tầng Xử Lý Popup Chuẩn (Core vs In-App)**:
   - **Cấp Core (`automation-core`)**: Quyền hệ thống (Vị trí, Danh bạ, PackageInstaller) $\rightarrow$ **TẮT LIỀN (< 0.5s)**: Tick "Không hỏi lại" + Bấm "TỪ CHỐI".
   - **Cấp Repo (`tiktok-luot nuoi acc`)**: In-app popups/screens $\rightarrow$ **DỪNG XEM TỰ NHIÊN RỒI MỚI THOÁT**:
     - Phòng Live (`live_room_exit`): Dừng xem **6.0 – 14.0 giây** rồi bấm nút **✕** (`id/close`, `id/e63`, `id/e6n`).
     - Trang chi tiết TikTok Shop (`shop_product_detail_close`): Dừng xem **3.0 – 7.0 giây** rồi bấm **✕** (`id/gnl`, `id/e5w`).
     - Bảng "Bài đăng lại" (`repost_sheet_close`): Dừng **2.0 – 4.0 giây** rồi bấm **✕** (`id/e55`).
     - Màn hình "Số lượt xem hồ sơ" (`profile_views_back` - Máy 58): Bấm `Quay lại màn hình trước` (`←`) hoặc `Đóng` (`id/llm`).
     - Màn hình Tìm kiếm / Search page (`search_screen_back` - Máy 6): Gửi phím `BACK` để hạ bàn phím và đóng trang tìm kiếm về Feed.
     - Lưới sản phẩm thương hiệu (`brand_product_grid_back` - Máy 16, 48): Gửi phím `BACK` để thoát về Feed.
     - Thẻ gợi ý kết bạn trên Feed (`follow_back_suggestion` - Máy 21): Bấm nút **"Follow lại"**.
4. **Xử Lý Quyền Vị Trí Ở Đầu Phiên (`before_swipe` - Máy 41)**:
   - Đưa `_maybe_dismiss_packageinstaller_after_swipe` vào ngay đầu chuỗi kiểm tra `before_swipe` $\rightarrow$ Tự động tick *"Không hỏi lại"* + bấm *"TỪ CHỐI"*.
5. **Khắc Phục So Khớp Profile Cuối Phiên (`verify_profile` - Máy 52)**:
   - **CHỈ ĐỐI SOÁT THEO ID / USERNAME TRONG EXCEL (`ctx.account`)**: Cột account trong Excel chỉ chứa Username/ID TikTok, không chứa biệt danh (Display Name). Hàm `verify_profile` chỉ so sánh `ctx.account` với username trên màn hình (node chứa `@<username>`), TUYỆT ĐỐI KHÔNG so sánh với Display Name để tránh sai lệch dữ liệu.
6. **Xử Lý Quyền Hệ Thống PackageInstaller (Vị trí / Danh bạ)**:
   - Hộp thoại quyền hệ điều hành Android (`packageinstaller/system-dialog`) KHÔNG thể tắt bằng phím Back.
   - BẮT BUỘC thực hiện đúng 2 bước ở cấp `automation-core`: Tick chọn checkbox *"Không hỏi lại"* (`id/do_not_ask_checkbox`) ➔ Bấm nút *"TỪ CHỐI"* (`id/permission_deny_button`).
   - `feed_swipe_smoke.py` phải gọi `_maybe_dismiss_packageinstaller_after_swipe` ở cả đầu phiên (`before_swipe`) lẫn sau từng swipe để tự động dọn sạch quyền hệ thống.
7. **Whitelist Package Hệ Thống Sau Dismiss (Máy 29)**:
   - Whitelist các package `packageinstaller`, `permissioncontroller`, `systemui` trong `_blocked_after_close_reason` để không bị kết luận nhầm là mất focus TikTok.
8. **Xử Lý Màn Hình Recent Apps Rỗng (Máy 64)**:
   - Khi Recents rỗng hiển thị *"Không có ứng dụng đã dùng gần đây"*, script xác nhận sạch nền và gửi phím `Home` tiếp tục thay vì báo lỗi.
9. **Cơ Chế Phục Hồi Khi Văng Ra Launcher (`_recover_launcher_focus_lost`)**:
   - Khi máy bị crash hoặc rớt về màn hình chính (`com.sec.android.app.launcher`): Script tự động gọi `force_stop_and_relaunch_tiktok`, chờ 3s nạp lại app, chụp lại màn hình xác nhận Feed và cho phép chạy tiếp trọn vẹn số video còn lại của phiên.
- Chi tiết: `references/feed-popups-live-shop-and-recents-20260819.md`.

## 26. GIẢ LẬP MỨC PIN NGẪU NHIÊN >50% (ANTI-PATTERN FARM)
1. **Mức Pin Giả Lập Mặc Định**:
   - Thay vì set cứng mức pin 80% đều tăm tắp trên toàn bộ 80 máy (dễ lộ footprint automation), hàm `set_battery_level` trong `automation_core/device.py` và `startup.py` mặc định chọn ngẫu nhiên trong khoảng **55% đến 95%** (`random.randint(55, 95)`).
   - Thiết lập qua 3 lệnh ADB:
     - `dumpsys battery set level <random_55_95>`
     - `dumpsys battery set status 2` (Đang sạc)
     - `dumpsys battery set ac 1` (Cắm nguồn AC)
   - Đảm bảo vừa chống triệt để popup cảnh báo pin yếu của Samsung vừa tạo trạng thái pin tự nhiên riêng biệt cho từng máy.

## 22. QUY TRÌNH KHI USER HỎI "CHỐT PHIÊN ĐƯỢC CHƯA" & PRE-COMMIT REVIEW (BẮT BUỘC TOÀN BỘ REPO - 18/08)
1. **BẮT BUỘC GỌI SUBAGENT CODE REVIEW TRƯỚC COMMIT/PUSH (User phạt 18/08)**:
   - Tuyệt đối CẤM `git commit` hoặc `git push` trực tiếp khi chưa qua bước review độc lập.
   - Bất kỳ code fix/patch nào trước khi commit PHẢI:
     - 1. Chạy static security scan (secrets, dangerous eval/exec).
     - 2. Chạy test suite liên quan (`pytest`).
     - 3. **Gọi Review độc lập qua 9Router HTTP API** (model `plan-review` / `plan-review-hard`, CẤM dùng `delegate_task`) theo skill `requesting-code-review`.
     - 4. Nhận verdict `passed: true` / `APPROVED` từ reviewer 9Router mới được thực hiện `git commit` và `git push`.

     2. **Khi user hỏi bất kỳ câu nào dạng: *"chốt phiên được chưa"*, *"xong phiên chưa"*, *"kết thúc phiên được chưa"***:
     Agent BẮT BUỘC tự động thực hiện tuần tự và hoàn tất chuỗi 4 bước sau:
     1. **Tự động gọi Agent Review (Code Audit)**:
     - Gọi độc lập qua 9Router HTTP API combo `plan-review` (model `plan-review`, stream: false, tool_choice: none, CẤM dùng `delegate_task`) để audit toàn bộ `git diff` các thay đổi trong phiên. Bắt buộc nhận verdict `APPROVED` mới đi tiếp.
2. **Kiểm tra Merge Conflict & Trạng thái Worktree**:
   - Rà soát `git status` và branch của toàn bộ các repo liên quan, đảm bảo không có merge conflict dở dang.
3. **Dọn sạch các Worktree / File rác tạm**:
   - Dọn sạch các file tạm/untracked thừa sinh ra trong phiên debug/test, đưa worktree về trạng thái sạch sẽ chuẩn mực.
4. **Commit & Push Main / Master**:
   - Tự động `git add` các file code/rule đã chỉnh sửa, commit với message tiếng Việt rõ ràng, và `git push` về branch chính (`main` hoặc `master` / branch đang active có remote) của repo.
5. **Báo cáo kết quả chốt phiên**:
   - Chỉ trả lời báo cáo ngắn gọn khi toàn bộ 4 bước trên đã hoàn tất thành công.

## 27. CƠ CHẾ BÁO LỖI 2 BƯỚC & GIÁM SÁT THỤ ĐỘNG VÀO FARM ALERTS (User chốt 19/08)
1. **Mô hình Báo Cáo 2 Bước Chuẩn Xác (User yêu cầu: không chụp banner xanh đè, gửi báo cáo gãy gọn)**:
   - **Tin nhắn 1 (Ảnh hiện trường lỗi nguyên trạng)**:
     - Chụp ảnh màn hình ngay lúc kẹt, vẽ **Banner Đỏ `[MAY XX] - HH:MM DD/MM`** ở đỉnh ảnh.
     - Caption báo lỗi chuẩn: `🚨 [MÁY XX] DỪNG PHIÊN` | Script | Tài khoản | Lý do lỗi | Trạng thái: `🟢 ĐANG MỞ (Tự động chạy tiếp phiên sau)`.
   - **Tin nhắn 2 (Do Não AI của Bot Hermes trong nhóm Farm Alerts tự xử lý & báo cáo)**:
     - **BẮT BUỘC TRÍCH XUẤT ĐÍCH DANH LÝ DO KỸ THUẬT GỐC** (ví dụ: *Không tìm thấy tài khoản @username trong Account Switcher*, *Kẹt popup quyền vị trí*, *Kẹt phòng Live*, *Lỗi mất focus*...). **TUYỆT ĐỐI CẤM dùng các từ ngữ chung chung, mơ hồ như "Dừng phiên bất thường" hay logic if/else rập khuôn, và CẤM đưa ra các đề nghị lý thuyết suông**.
     - **QUY TRÌNH TỰ ĐỘNG KHÉP KÍN 5 BƯỚC (BẮT BUỘC TUÂN THỦ)**:
       1. **Gửi lỗi & Giữ nguyên hiện trường**: Máy kẹt lỗi nào thì giữ nguyên màn hình và XML tại thời điểm kẹt (ví dụ: thiếu nick thì giữ nguyên bảng Account Switcher, kẹt popup thì giữ nguyên popup), CẤM tự ý dọn app về Home hoặc reset app làm mất dấu vết trước khi phân tích.
       2. **AI phân tích lỗi thật & Vá Script TRƯỚC**: AI của session đọc ảnh/XML tại hiện trường $\rightarrow$ Tự động vào file repo sửa code / bổ sung rule vào repo tương ứng ngay lập tức.
       3. **Test trực tiếp hàm vừa code tại hiện trường lỗi**: Nạp đoạn code vừa sửa chạy thử **ngay tại trạng thái đang bị kẹt** để xem code mới có vượt qua được lỗi không (TUYỆT ĐỐI KHÔNG CHẠY LẠI TỪ ĐẦU).
       4. **Gọi Model Plan-Review Độc Lập**: Sau khi test pass, bắt buộc xuất diff gọi Model Plan-Review / Claude CLI `--effort max` kiểm tra an toàn và nhận `VERDICT: APPROVED` $\rightarrow$ Commit & Push Git đồng bộ 80 máy.
       5. **Báo cáo hoàn tất vào nhóm Farm Alerts**: Nhắn tin báo cáo xử lý vào nhóm Farm Alerts (gồm đủ **Hướng sửa** & **Kết quả**).
     - Mẫu báo cáo xử lý tóm gọn:
       ```
       🛠️ [AI AUTO-RECOVERY - MÁY XX]
       • Hướng sửa: <Giải thích lỗi kỹ thuật & hành động đã vá vào script>
       • Kết quả: <Kết quả test thực tế máy đã vượt qua bước kẹt về Feed/Hoàn thành>
       • (Nếu đúng ý bạn im lặng bỏ qua, cần sửa cách khác hãy nhắn lại)
       ```
   - **Cơ chế duyệt thụ động**: User thấy xử lý đúng ý ➔ **im lặng bỏ qua**; nếu thấy cần chỉnh cách khác ➔ reply tin nhắn cảnh báo để ra lệnh.
   - **Bật `TELEGRAM_ALLOW_BOTS=all` và `require_mention: false`**: Để Bot Hermes trong nhóm Farm Alerts tự động tiếp nhận tin nhắn alert bắn từ script qua Bot API mà không bị chặn quyền hoặc đòi hỏi mention.
   - **Dọn sạch RAM khi nạp code mới**: Luôn kiểm tra và kill sạch các tiến trình cũ (`run_tiktok.py`, `run_follow.py`) đang chạy ngầm trong RAM để tránh bị dính bytecode cũ tiếp tục gửi tin nhắn rác/mẫu cũ.
   - Chi tiết quy trình: `references/ai-autonomous-recovery-and-zero-hardcode-alerts-20260819.md`.

## 28. CHUẨN HÓA TỈ LỆ PHÂN BỔ 3 TAB & TƯƠNG TÁC TỰ NHIÊN (19/08)
1. **Phân Bổ Lướt 3 Tab (`DEFAULT_FEED_DISTRIBUTION`)**:
   - **Dành cho bạn (For You - FYP)**: **`85%`** (khám phá video đề xuất).
   - **Đang theo dõi (Following)**: **`8%`** (xem video kênh yêu thích).
   - **Bạn bè (Friends)**: **`7%`** (xem video/story của bạn bè/acc trong farm, kích hoạt lại sau thời gian tắt).
2. **Tỉ Lệ Like & Follow Từng Tab Chuẩn Hóa**:
   - **Like Rate**:
     - *For You*: **`8%`** (người lạ, like chọn lọc).
     - *Following*: **`15%`** (kênh đã thích, like cao hơn bình thường).
     - *Friends*: **`25%`** (bạn bè/nội bộ farm, like nhiệt tình 1/4 số video tạo tương tác chéo mạnh).
   - **Follow Rate (Organic FYP)**: **`6%`** trên For You (`0%` trên Following/Friends vì đã follow từ trước).
     - *Lý do*: 1 ngày nick lướt ~150 video For You ➔ tạo ~9-10 organic follows tự nhiên. Khi đối chiếu với 20-30 targeted follow chéo/ngày của farm, tỉ lệ đạt **~1 tự nhiên : 2.5 - 3 follow chéo** (lớp đệm tự nhiên chiếm ~30%), bảo vệ tài khoản tuyệt đối không bị TikTok gắn cờ "Dedicated Follow Bot".
3. **Độ Trễ Dừng Xem Tự Nhiên Giữa Các Tab (Watch Ranges)**:
   - Phải tuân theo thứ tự tự nhiên của người thật: `Friends (5.0 - 15.0s)` > `Following (4.0 - 12.0s)` > `For You (3.0 - 10.0s)`.
4. **Xử Lý Màn Hình Khảo Sát Quảng Cáo (Pepsi / Brand Ad Feedback)**:
   - Gặp câu hỏi khảo sát quảng cáo (*"Bạn có quan tâm đến quảng cáo này không?"*) ➔ Không dừng phiên, tự động vuốt trượt mạnh sang video kế tiếp để bỏ qua quảng cáo và tiếp tục lướt feed.

- Lưu ý Password TikTok: TikTok có thể nhảy thẳng vào màn chính mà không yêu cầu tạo mật khẩu (flow OTP/Email-only). Khi đó script **bắt buộc để trống cột Pass TikTok (`None`/`""`)** trong tracking workbook, không được tự động ghi password giả định để sau này các luồng khác biết acc chưa có mật khẩu và chủ động tạo lại.
- Toàn farm 80 máy gán proxy theo từng cặp dùng chung port (khoảng cách 38 máy: [1, 39], [2, 40], [3, 41], [4, 42]... [38, 76]).
- **Khi chọn batch máy chạy register Gmail**: BẮT BUỘC chỉ chọn tối đa **1 máy trong mỗi cặp proxy** trong cùng một đợt chạy (tối đa 38 máy unique IP).
- Tuyệt đối KHÔNG chạy đồng thời hoặc chạy tiếp máy cùng cặp proxy khi máy kia vừa tạo tài khoản Google để tránh bị Google AI gắn cờ spam registration trùng IP.
- KHÔNG gọi lệnh xoay IP proxy (chỉ lọc duy nhất 1 máy / cặp proxy).
- **Preflight `pm clear` trước khi reg**: `pm clear com.google.android.gm` để xóa sạch cache rác/session cũ, sau đó handle màn hình chào mừng ("ĐƯA TÔI TỚI GMAIL" / "Thêm địa chỉ email").
- **Dọn mail die xong**: BẮT BUỘC close recent apps (`keyevent 187` -> tap Đóng tất cả -> `keyevent 3` về HOME) và gỡ device-lock ngay.
