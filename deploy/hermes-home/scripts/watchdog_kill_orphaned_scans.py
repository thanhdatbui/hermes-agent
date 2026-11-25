#!/usr/bin/env python3
"""
Watchdog script to detect and terminate orphaned or long-running search processes
(grep.exe, rg.exe, find.exe) that have been running continuously for over 180 seconds.
"""

import argparse
import logging
import sys
import time

try:
    import psutil
except ImportError:
    print("Error: 'psutil' library is required. Install it via 'pip install psutil'.", file=sys.stderr)
    sys.exit(1)

# Configure logging: all diagnostics go to stderr, never stdout.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger("watchdog_scans")

TARGET_PROCESSES = {p.lower() for p in ["grep.exe", "rg.exe", "find.exe", "grep", "rg", "find"]}
MAX_AGE_ORPHAN = 60
MAX_AGE_ALIVE = 300

def is_reboot_blackout_window(now_dt=None, now_ts=None) -> bool:
    """Ne 3 khung gio reboot Farm: 05:05-05:35, 11:05-11:35, 17:05-17:35 va uptime < 15m."""
    ts = time.time() if now_ts is None else now_ts
    try:
        if (ts - psutil.boot_time()) < 900.0:
            return True
    except Exception:
        pass
    m = (time.localtime(ts).tm_hour * 60 + time.localtime(ts).tm_min) if now_dt is None else (now_dt.hour * 60 + now_dt.minute)
    return any(h * 60 + 5 <= m <= h * 60 + 35 for h in (5, 11, 17))

def kill_orphaned_scans(dry_run: bool = False):
    if is_reboot_blackout_window():
        return
    now = time.time()
    killed_count = 0

    # Buoc 1: Thu thap ban do tien trinh
    # Snapshot process map for parent validation and anti-PID reuse check
    proc_map = {}
    for proc in psutil.process_iter(['pid', 'create_time']):
        try:
            info = proc.info
            if info.get('pid') is not None:
                proc_map[info['pid']] = info.get('create_time')
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    # Buoc 2: Duyet tien trinh va phan loai orphan vs alive
    for proc in psutil.process_iter(['pid', 'name', 'create_time', 'cmdline', 'ppid']):
        try:
            pinfo = proc.info
            name = pinfo.get('name')
            if not name:
                continue

            # Check if basename matches target processes (case-insensitive)
            if name.lower() not in TARGET_PROCESSES:
                continue

            create_time = pinfo.get('create_time')
            if not create_time:
                continue

            ppid = pinfo.get('ppid')
            
            # Determine if parent is alive and valid (anti-PID reuse)
            parent_alive = False
            if ppid and ppid in proc_map:
                parent_create_time = proc_map[ppid]
                if parent_create_time is not None and parent_create_time <= create_time:
                    parent_alive = True

            max_age = MAX_AGE_ALIVE if parent_alive else MAX_AGE_ORPHAN
            reason = "timeout" if parent_alive else "orphan"

            age = now - create_time
            # Buoc 3: Tieu diet tien trinh va in alert
            if age > max_age:
                pid = pinfo.get('pid')
                cmdline = " ".join(pinfo.get('cmdline') or [])
                
                logger.warning(
                    f"Found long-running scan process ({reason}): PID={pid}, Name={name}, Age={age:.1f}s (> {max_age}s), PPID={ppid}, Cmdline='{cmdline}'"
                )

                if dry_run:
                    logger.info(f"[DRY-RUN] Would terminate PID {pid} ({name}) [Reason: {reason}, Age: {age:.1f}s]")
                else:
                    try:
                        proc.terminate()
                        # Confirm graceful termination; force kill and confirm if necessary.
                        try:
                            proc.wait(timeout=3)
                        except psutil.TimeoutExpired:
                            proc.kill()
                            proc.wait(timeout=3)
                        logger.info(f"Successfully terminated process PID={pid} ({name}) [Reason: {reason}]")
                        print(f"ALERT: Terminated PID={pid}, reason={reason}, age={age:.1f}s, cmdline='{cmdline}'", flush=True)
                        killed_count += 1
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
                        logger.error(f"Failed to terminate PID {pid} ({name}): {e}")

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
        except Exception as e:
            logger.debug(f"Error inspecting process: {e}")

    logger.info(f"Scan check completed. Total processes terminated: {killed_count}")

def main():
    # Buoc 1
    parser = argparse.ArgumentParser(description="Watchdog to kill orphaned (>60s) or long-running (>300s) scan processes.")
    parser.add_argument("--dry-run", action="store_true", help="Log processes that exceed the threshold without terminating them.")
    args = parser.parse_args()

    # Buoc 2

    # Buoc 3
    kill_orphaned_scans(dry_run=args.dry_run)

if __name__ == "__main__":
    main()
