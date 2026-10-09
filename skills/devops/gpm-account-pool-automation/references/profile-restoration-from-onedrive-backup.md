# Quy trình Khôi phục Profile GPM Gốc Từ OneDrive Backup (3.5GB) & DB Nguyên Bản

## 1. Khi nào sử dụng
- Khi Profile GPM bị văng session Google hàng loạt do lệch Fingerprint (`JsonData` bị sửa đổi hoặc clone sai lệch so với cookie jar vật lý).
- Khi cần phục hồi 16 profile gốc Kibe Farm S7 (`01_Rua` → `15` + `AMZ_Main`) về trạng thái cookie/session Google hoạt động nguyên bản ngày 01/09/2026.

---

## 2. Tài nguyên Backup Chuẩn

1. **File Zip Thư mục Chrome vật lý (3.53 GB):**
   - Đường dẫn: `D:\OneDrive\backup\GPM\gpm_active_16profiles_20260901.zip`
   - Chứa đầy đủ 16 thư mục Profile Chrome nguyên bản:
     * `x_rua_jidbq` (Profile 01 / Máy 01)
     * `2_r7clp` (Profile 02 / Máy 02)
     * `3_s5w5k` (Profile 03 / Máy 03)
     * `4_hmmy5` (Profile 04 / Máy 04)
     * `5_vqxmk` (Profile 05 / Máy 05)
     * `6_r7psc` (Profile 06 / Máy 06)
     * `7_tspsb` (Profile 07 / Máy 07)
     * `8_vuchy` (Profile 08 / Máy 08)
     * `9_bk115` (Profile 09 / Máy 09)
     * `10_p5cej` (Profile 10 / Máy 10)
     * `11-8801315697361_84lp9` (Profile 11 / Máy 11)
     * `12-8801320930664_zhqmw` (Profile 12 / Máy 12)
     * `13-88001324341907_llkjy` (Profile 13 / Máy 13)
     * `14-8801332045494_lkylv` (Profile 14 / Máy 14)
     * `15-8801300413451_qdx5n` (Profile 15 / Máy 15)
     * `amz_main_5cuml` (Profile AMZ_Main)

2. **Database SQLite Gốc:**
   - Đường dẫn: `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\_backup\profile_data_backup.db`
   - Chứa chuỗi `JsonData` có đúng 100% các thông số vân tay gốc (`AudioNoise`, `CanvasNoiseToken`, `WebGLRenderer`, `WebGLVendor`, `MacAddress`, `UserAgent`) khớp hoàn toàn với cookie jar trong file zip.

---

## 3. Quy tắc Bất Biến Khi Khôi Phục (Invariants)

1. **Check First — Kiểm tra làm tay trước khi đụng:**
   - Khởi động profile trên GPM -> Kiểm tra `https://myaccount.google.com/`.
   - Nếu phát hiện **đã có Gmail login sẵn (do User tự đăng nhập thủ công)** -> **GIỮ NGUYÊN BẢN 100%, BỎ QUA NGAY LẬP TỨC**.
2. **Khớp 1:1 Giữa Dữ Liệu Chrome và Database:**
   - Tuyệt đối không chỉ copy file cookie mà để `JsonData` mới, cũng không được copy `JsonData` mà giữ thư mục Chrome bị sửa đổi.
   - BẮT BUỘC khôi phục đồng thời cả thư mục profile từ zip VÀ chuỗi `JsonData` từ `profile_data_backup.db`.
3. **Chỉ Cập Nhật Proxy — Giữ Nguyên Fingerprint:**
   - Trong chuỗi `JsonData` phục hồi, **CHỈ ĐƯỢC PHÉP** cập nhật trường proxy (`raw_proxy`, `proxy_*`) theo đúng proxy Farm S7 (`test.taadaa.click:5101..5118` / Singbox `192.168.110.2:20001..20016`).
   - Tuyệt đối **KHÔNG randomize, KHÔNG thay đổi** bất kỳ thông số noise hay hardware nào.
4. **Quy trình Pilot Thử Nghiệm Trước (1-3 Profiles):**
   - Luôn khôi phục thử nghiệm 1-3 profiles trước (ví dụ: Profile 03, 04, 05).
   - Mở Playwright CDP verify truy cập `myaccount.google.com` và `mail.google.com/mail/u/0/#inbox`.
   - Chỉ khi pilot PASS 100% vào thẳng inbox mới được tiến hành khôi phục toàn bộ các profile còn lại.

---

## 4. Script Mẫu Khôi Phục Từng Profile Chuẩn Xác

```python
import zipfile
import os
import sqlite3
import json

ZIP_PATH = r"D:\OneDrive\backup\GPM\gpm_active_16profiles_20260901.zip"
DB_BACKUP_PATH = r"C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\_backup\profile_data_backup.db"
ACTIVE_PROFILE_DIR = r"C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile"
ACTIVE_DB_PATH = r"C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\profile_data.db"

def restore_single_profile(profile_path_folder: str, machine_num: int):
    # 1. Giải nén thư mục profile từ zip
    with zipfile.ZipFile(ZIP_PATH, 'r') as z:
        for member in z.infolist():
            if member.filename.startswith(f"{profile_path_folder}/"):
                z.extract(member, ACTIVE_PROFILE_DIR)
    print(f"[*] Đã giải nén folder: {profile_path_folder}")

    # 2. Đọc JsonData gốc từ DB backup
    conn_bak = sqlite3.connect(DB_BACKUP_PATH)
    cur_bak = conn_bak.cursor()
    cur_bak.execute("SELECT JsonData, Name FROM Profiles WHERE ProfilePath = ?", (profile_path_folder,))
    row = cur_bak.fetchone()
    conn_bak.close()

    if not row:
        raise ValueError(f"Không tìm thấy ProfilePath {profile_path_folder} trong DB backup!")

    raw_json_str, orig_name = row
    json_data = json.loads(raw_json_str)

    # 3. Chỉ cập nhật proxy theo đúng máy S7 Farm
    singbox_proxy = f"http://192.168.110.2:{20000 + machine_num}"
    raw_proxy = f"test.taadaa.click:{5100 + machine_num}:mobi{machine_num}:TaadaaMobi#2026!"
    
    json_data["raw_proxy"] = raw_proxy
    json_data["proxy_host"] = "192.168.110.2"
    json_data["proxy_port"] = str(20000 + machine_num)
    json_data["proxy_user"] = ""
    json_data["proxy_pass"] = ""

    # 4. Ghi đè JsonData chuẩn vào Active DB
    conn_act = sqlite3.connect(ACTIVE_DB_PATH)
    cur_act = conn_act.cursor()
    cur_act.execute(
        "UPDATE Profiles SET JsonData = ?, RawProxy = ? WHERE ProfilePath = ?",
        (json.dumps(json_data), raw_proxy, profile_path_folder)
    )
    conn_act.commit()
    conn_act.close()
    print(f"[+] Khôi phục thành công DB & Fingerprint cho Profile {profile_path_folder}")
```
