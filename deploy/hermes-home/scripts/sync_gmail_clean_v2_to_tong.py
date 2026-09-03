import os
import sys
import hashlib
import openpyxl

GMAIL_CLEAN_V2 = r"D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx"
DEST_DIR = r"D:\OneDrive\TaadaaData\kibe"
HASH_CACHE = r"C:\Users\Kibe\AppData\Local\hermes\scripts\checkmail_results\gmail_clean_v2_hash.txt"

LIVE_FILE = os.path.join(DEST_DIR, "gmail_live_tong.txt")

def get_file_hash(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def sync(force=False):
    if not os.path.exists(GMAIL_CLEAN_V2):
        return 0

    current_hash = get_file_hash(GMAIL_CLEAN_V2)
    last_hash = ""
    if os.path.exists(HASH_CACHE):
        with open(HASH_CACHE, "r", encoding="utf-8") as f:
            last_hash = f.read().strip()

    if not force and current_hash == last_hash:
        # Im lặng khi không có thay đổi
        return 0

    # Đọc danh sách live hiện tại
    live_emails = set()
    if os.path.exists(LIVE_FILE):
        with open(LIVE_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip().lower()
                if line and "@gmail.com" in line:
                    live_emails.add(line)

    # Đọc CHỈ ĐỂ LẤY MAIL (READ-ONLY) từ gmail_clean_v2.xlsx, tuyệt đối KHÔNG sửa/ghi đè file này
    wb = openpyxl.load_workbook(GMAIL_CLEAN_V2, data_only=True, read_only=True)
    ws = wb.active

    added = 0
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0 or not row:
            continue
        mail = row[1]
        if not mail:
            continue

        cstr = str(mail).strip().lower()
        em = cstr if "@" in cstr else cstr + "@gmail.com"
        if "@gmail.com" not in em:
            continue

        # Chỉ thêm nếu chưa có trong list tổng
        if em not in live_emails:
            live_emails.add(em)
            added += 1

    # Lưu lại file gmail_live_tong.txt (duy nhất 1 file tổng)
    all_live = sorted(list(live_emails))
    with open(LIVE_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(all_live) + "\n")

    with open(HASH_CACHE, "w", encoding="utf-8") as f:
        f.write(current_hash)

    print(f"[Sync Gmail Live Tong] Tong cong: {len(all_live)} Gmail Live (+{added} mail moi tu gmail_clean_v2)")
    return 0

if __name__ == "__main__":
    force_run = "--force" in sys.argv
    sys.exit(sync(force=force_run))
