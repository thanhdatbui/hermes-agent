r"""Multi-Cloud Backup Sync: D:\OneDrive -> Google Drive 5TB & iCloudDrive.

Designed for Hermes Cronjob (watchdog pattern: silent when no changes, reports summary on updates/errors).
"""

import os
import sys
import time
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple, Dict, Any

SRC = r"D:\OneDrive"
DST_GDRIVE = r"G:\Drive của tôi\Backup_OneDrive_5TB"
DST_ICLOUD = r"C:\Users\Kibe\iCloudDrive\Backup_OneDrive"

EXCLUDE_DIRS = {
    "node_modules",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".git",
    "desktop.ini",
}
EXCLUDE_FILES = {
    "desktop.ini",
    "thumbs.db",
}


def is_excluded_dir(dir_name: str) -> bool:
    return dir_name.lower() in EXCLUDE_DIRS


def is_excluded_file(file_name: str) -> bool:
    fn = file_name.lower()
    if fn in EXCLUDE_FILES or fn.startswith("~$") or fn.endswith(".tmp") or fn.startswith(".849c"):
        return True
    # Skip hidden/temp/lock files (dotfiles, .f* temp Excel files, lock files)
    if fn.startswith(".") and len(fn) > 1:
        return True
    return False


def copy_worker(item: Tuple[str, str, int]) -> Tuple[bool, str, int, str]:
    src_f, dst_f, sz = item
    try:
        os.makedirs(os.path.dirname(dst_f), exist_ok=True)
        shutil.copy2(src_f, dst_f)
        return True, src_f, sz, ""
    except Exception as e:
        return False, src_f, sz, str(e)


def sync_directory(src_root: str, dst_root: str, max_workers: int = 16) -> Dict[str, Any]:
    if not os.path.exists(dst_root):
        try:
            os.makedirs(dst_root, exist_ok=True)
        except Exception as e:
            return {"success": False, "error": f"Cannot create destination: {e}", "synced_files": 0, "synced_bytes": 0}

    to_copy: List[Tuple[str, str, int]] = []
    total_scanned = 0

    for root, dirs, files in os.walk(src_root):
        dirs[:] = [d for d in dirs if not is_excluded_dir(d)]
        rel = os.path.relpath(root, src_root)
        target_dir = os.path.join(dst_root, rel) if rel != "." else dst_root

        for f in files:
            if is_excluded_file(f):
                continue
            total_scanned += 1
            src_f = os.path.join(root, f)
            dst_f = os.path.join(target_dir, f)

            try:
                st_src = os.stat(src_f)
                if not os.path.exists(dst_f):
                    to_copy.append((src_f, dst_f, st_src.st_size))
                else:
                    st_dst = os.stat(dst_f)
                    # Tolerate up to 2 seconds delta for FAT/FUSE FS mtime differences
                    if abs(st_src.st_mtime - st_dst.st_mtime) > 2 or st_src.st_size != st_dst.st_size:
                        to_copy.append((src_f, dst_f, st_src.st_size))
            except Exception:
                pass

    if not to_copy:
        return {"success": True, "total_scanned": total_scanned, "synced_files": 0, "synced_bytes": 0, "errors": []}

    synced_files = 0
    synced_bytes = 0
    errors = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(copy_worker, item) for item in to_copy]
        for fut in as_completed(futures):
            ok, fpath, sz, err = fut.result()
            if ok:
                synced_files += 1
                synced_bytes += sz
            else:
                # Ignore transient locked files
                if "used by another process" not in err:
                    errors.append(f"{os.path.basename(fpath)}: {err}")

    return {
        "success": len(errors) == 0,
        "total_scanned": total_scanned,
        "synced_files": synced_files,
        "synced_bytes": synced_bytes,
        "errors": errors[:5],
    }


def main():
    t0 = time.time()
    results = {}

    # 1. Sync to Google Drive
    if os.path.exists(r"G:\Drive của tôi") or os.path.exists(DST_GDRIVE):
        results["Google Drive 5TB"] = sync_directory(SRC, DST_GDRIVE, max_workers=16)
    else:
        results["Google Drive 5TB"] = {"success": False, "error": r"Ổ G:\ (Google Drive) chưa được mount."}

    # 2. Sync to iCloud Drive
    if os.path.exists(r"C:\Users\Kibe\iCloudDrive"):
        results["iCloudDrive"] = sync_directory(SRC, DST_ICLOUD, max_workers=16)
    else:
        results["iCloudDrive"] = {"success": False, "error": "iCloudDrive không tồn tại."}

    elapsed = time.time() - t0

    # Check if there were any changes or errors
    has_changes = any(r.get("synced_files", 0) > 0 for r in results.values())
    has_errors = any(not r.get("success", False) for r in results.values())

    if has_changes or has_errors:
        print(f"[Multi-Cloud Sync Report - {time.strftime('%Y-%m-%d %H:%M:%S')}] (Elapsed: {elapsed:.1f}s)")
        for target, res in results.items():
            if res.get("success"):
                mb = res.get("synced_bytes", 0) / (1024 * 1024)
                print(f"  ✓ {target}: Synced {res.get('synced_files', 0)} files ({mb:.2f} MB)")
            else:
                print(f"  ✗ {target}: Failed - {res.get('error', res.get('errors', 'Unknown error'))}")
    else:
        # Silent watchdog mode when up to date
        pass


if __name__ == "__main__":
    main()
