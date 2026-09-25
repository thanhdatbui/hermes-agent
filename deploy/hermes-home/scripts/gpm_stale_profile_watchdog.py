#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gpm_stale_profile_watchdog.py
Watchdog dọn dẹp các profile GPMLogin bị treo > 1 giờ:
1. Quét toàn bộ tiến trình hệ thống qua psutil.
2. Nhận diện các tiến trình Chrome thuộc GPMLogin (dựa trên --user-data-dir chứa 'gpmlogin/profile').
3. BẢO VỆ TUYỆT ĐỐI Chrome cá nhân (Google\\Chrome\\User Data) và các tiến trình khác.
4. Nếu age >= threshold (mặc định 3600s = 1 giờ):
   - Trích xuất ProfilePath từ --user-data-dir.
   - Tra cứu profile_data.db (SQLite) để lấy Id và Name.
   - Gọi GPM Local API /profiles/stop/{id} nếu API đang chạy.
   - Graceful terminate (chờ 1s) -> Force kill process và child processes.
   - Ghi telemetry metric [TELEMETRY_METRIC] ra stderr và telemetry log file.
5. Silent watchdog discipline:
   - Nếu không có profile nào bị dọn: Không in gì ra stdout (empty stdout), exit 0.
   - Nếu có profile bị dọn: In báo cáo tổng kết ra stdout để cron auto-deliver.
"""

from __future__ import annotations

import os
import re
import sys
import json
import time
import sqlite3
import logging
import argparse
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

try:
    import psutil
except ImportError:
    psutil = None

DEFAULT_THRESHOLD_SECONDS = 3600
DEFAULT_GPM_API_BASE = "http://127.0.0.1:19995/api/v3"
DEFAULT_GPM_DB_PATH = Path.home() / "AppData" / "Local" / "Programs" / "GPMLogin" / "profile" / "profile_data.db"
TELEMETRY_LOG = Path.home() / "AppData" / "Local" / "hermes" / "logs" / "gpm_watchdog.jsonl"

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")
logger = logging.getLogger("gpm_stale_watchdog")


def format_age(seconds: float) -> str:
    td = timedelta(seconds=int(seconds))
    return str(td)


def is_gpm_chrome_process(cmdline: List[str]) -> bool:
    if not cmdline:
        return False
    cmd_lower = " ".join(cmdline).lower()

    # 1. BẢO VỆ TUYỆT ĐỐI CHROME CÁ NHÂN CỦA USER
    if "google\\chrome\\user data" in cmd_lower or "google/chrome/user data" in cmd_lower:
        return False

    # 2. Phải có --user-data-dir trỏ đúng vào thư mục profile của GPMLogin
    user_data_dir = None
    for i, arg in enumerate(cmdline):
        arg_lower = arg.lower()
        if arg_lower.startswith("--user-data-dir="):
            user_data_dir = arg.split("=", 1)[1].strip('"\'').lower()
            break
        elif arg_lower == "--user-data-dir" and i + 1 < len(cmdline):
            user_data_dir = cmdline[i + 1].strip('"\'').lower()
            break

    if not user_data_dir:
        return False

    norm_dir = user_data_dir.replace("\\", "/")
    if "gpmlogin/profile" in norm_dir:
        return True

    return False


def extract_profile_path(cmdline: List[str]) -> Optional[str]:
    for i, arg in enumerate(cmdline):
        if arg.startswith("--user-data-dir="):
            val = arg.split("=", 1)[1].strip('"\'')
            return os.path.basename(os.path.normpath(val))
        elif arg == "--user-data-dir" and i + 1 < len(cmdline):
            val = cmdline[i + 1].strip('"\'')
            return os.path.basename(os.path.normpath(val))
    return None


def extract_debugging_port(cmdline: List[str]) -> Optional[int]:
    for i, arg in enumerate(cmdline):
        if arg.startswith("--remote-debugging-port="):
            val = arg.split("=", 1)[1].strip('"\'')
            if val.isdigit():
                return int(val)
        elif arg == "--remote-debugging-port" and i + 1 < len(cmdline):
            val = cmdline[i + 1].strip('"\'')
            if val.isdigit():
                return int(val)
    return None


def lookup_profile_info(db_path: Path, profile_path: str) -> Tuple[Optional[str], Optional[str]]:
    if not profile_path or not db_path.exists():
        return None, None
    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.execute("SELECT Id, Name FROM profiles WHERE ProfilePath = ? OR Id = ? LIMIT 1", (profile_path, profile_path))
        row = cur.fetchone()
        conn.close()
        if row:
            return row[0], row[1]
    except Exception as e:
        logger.debug(f"Lỗi truy vấn profile_data.db: {e}")
    return None, None


def reap_stale_profiles(
    threshold_seconds: int = DEFAULT_THRESHOLD_SECONDS,
    dry_run: bool = False,
    db_path: Optional[Path] = None,
    api_base: str = DEFAULT_GPM_API_BASE
) -> List[Dict[str, Any]]:
    if psutil is None:
        logger.error("psutil chưa được cài đặt, không thể quét tiến trình.")
        return []

    target_db = db_path or DEFAULT_GPM_DB_PATH
    now = time.time()
    reaped_items: List[Dict[str, Any]] = []
    seen_profiles: set[str] = set()

    try:
        proc_iter = psutil.process_iter(['pid', 'name', 'create_time', 'cmdline'])
    except Exception as ex_iter:
        logger.debug(f"Lỗi khởi tạo process_iter: {ex_iter}")
        return []

    for p in proc_iter:
        try:
            try:
                p_info = p.info
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

            p_name = (p_info.get('name') or '').lower()
            if 'chrome' not in p_name:
                continue

            cmdline = p_info.get('cmdline') or []
            if not is_gpm_chrome_process(cmdline):
                continue

            # Bỏ qua các tiến trình con của Chrome (renderer, gpu-process, utility, crashpad)
            # Chỉ xử lý tiến trình Chrome gốc (browser process) để không bị đếm trùng PID nhiều lần
            if any(arg.startswith("--type=") for arg in cmdline):
                continue

            create_time = p_info.get('create_time') or now
            age = now - create_time
            if age < threshold_seconds:
                continue

            pid = p_info['pid']
            p_path = extract_profile_path(cmdline)
            port = extract_debugging_port(cmdline)
            prof_id, prof_name = lookup_profile_info(target_db, p_path) if p_path else (None, None)

            # Khử trùng lặp theo profile
            prof_key = prof_id or p_path or str(pid)
            if prof_key in seen_profiles:
                continue
            seen_profiles.add(prof_key)

            disp_name = prof_name or p_path or f"PID_{pid}"
            item = {
                "pid": pid,
                "profile_id": prof_id,
                "name": disp_name,
                "profile_path": p_path,
                "port": port,
                "age": age,
                "dry_run": dry_run
            }

            if not dry_run:
                # 1. Gọi GPM API stop để đồng bộ trạng thái
                if prof_id:
                    try:
                        requests.get(f"{api_base}/profiles/stop/{prof_id}", timeout=5)
                    except requests.RequestException as ex_req:
                        logger.debug(f"Lỗi mạng/timeout khi gọi GPM stop API cho {prof_id}: {ex_req}")
                    except Exception as ex_api:
                        logger.debug(f"Lỗi gọi GPM stop API cho {prof_id}: {ex_api}")

                # 2. Dọn dẹp tiến trình qua psutil
                try:
                    children = p.children(recursive=True)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    children = []
                except Exception:
                    children = []

                try:
                    p.terminate()
                    try:
                        p.wait(timeout=1.0)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                    except Exception:
                        try:
                            p.kill()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                        except Exception:
                            pass
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                except Exception:
                    pass

                for child in children:
                    try:
                        child.kill()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                    except Exception:
                        pass

            # Telemetry metric
            metric = {
                "timestamp": datetime.now().isoformat(),
                "event": "stale_gpm_reaped",
                "pid": pid,
                "profile_id": prof_id,
                "profile_name": disp_name,
                "age_seconds": int(age),
                "dry_run": dry_run
            }

            # Ghi telemetry log ra file JSONL
            try:
                TELEMETRY_LOG.parent.mkdir(parents=True, exist_ok=True)
                with open(TELEMETRY_LOG, "a", encoding="utf-8") as f_log:
                    f_log.write(json.dumps(metric, ensure_ascii=False) + "\n")
            except Exception as ex_log:
                logger.debug(f"Lỗi ghi telemetry log file: {ex_log}")

            # Ghi stderr
            sys.stderr.write(f"[TELEMETRY_METRIC] {json.dumps(metric, ensure_ascii=False)}\n")
            sys.stderr.flush()

            reaped_items.append(item)

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        except Exception as e:
            logger.debug(f"Lỗi kiểm tra tiến trình: {e}")

    return reaped_items


def main() -> int:
    parser = argparse.ArgumentParser(description="Watchdog dọn dẹp profile GPM bị treo > 1 giờ")
    parser.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD_SECONDS, help="Ngưỡng giây bị coi là treo (mặc định: 3600)")
    parser.add_argument("--dry-run", action="store_true", help="Chỉ quét và in danh sách, không kill")
    parser.add_argument("--db-path", type=str, default="", help="Đường dẫn custom tới profile_data.db")
    parser.add_argument("--api-base", type=str, default=DEFAULT_GPM_API_BASE, help="URL GPM Local API")
    args = parser.parse_args()

    db_path = Path(args.db_path) if args.db_path else None
    items = reap_stale_profiles(
        threshold_seconds=args.threshold,
        dry_run=args.dry_run,
        db_path=db_path,
        api_base=args.api_base
    )

    if not items:
        # SILENT WATCHDOG DISCIPLINE: Empty stdout when clean
        return 0

    h_str = f"{args.threshold // 3600}h" if args.threshold >= 3600 else f"{args.threshold}s"
    tag = "[GPM-WATCHDOG DRY-RUN]" if args.dry_run else "[GPM-WATCHDOG]"
    print(f"{tag} ĐÃ PHÁT HIỆN & DỌN DẸP {len(items)} PROFILE TREO > {h_str}:")
    for it in items:
        port_info = f" | Port: {it['port']}" if it['port'] else ""
        print(f"• {it['name']} (PID: {it['pid']}) | Treo: {format_age(it['age'])}{port_info}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
