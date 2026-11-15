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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("watchdog_scans")

TARGET_PROCESSES = {p.lower() for p in ["grep.exe", "rg.exe", "find.exe", "grep", "rg", "find"]}
MAX_AGE_SECONDS = 180

def kill_orphaned_scans(dry_run: bool = False):
    now = time.time()
    killed_count = 0

    for proc in psutil.process_iter(['pid', 'name', 'create_time', 'cmdline']):
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

            age = now - create_time
            if age > MAX_AGE_SECONDS:
                pid = pinfo.get('pid')
                cmdline = " ".join(pinfo.get('cmdline') or [])
                
                logger.warning(
                    f"Found long-running scan process: PID={pid}, Name={name}, Age={age:.1f}s (> {MAX_AGE_SECONDS}s), Cmdline='{cmdline}'"
                )

                if dry_run:
                    logger.info(f"[DRY-RUN] Would terminate PID {pid} ({name})")
                else:
                    try:
                        proc.terminate()
                        # Give it a short moment to terminate gracefully, then kill if alive
                        try:
                            proc.wait(timeout=3)
                        except psutil.TimeoutExpired:
                            proc.kill()
                        logger.info(f"Successfully terminated process PID={pid} ({name})")
                        killed_count += 1
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
                        logger.error(f"Failed to terminate PID {pid} ({name}): {e}")

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
        except Exception as e:
            logger.debug(f"Error inspecting process: {e}")

    logger.info(f"Scan check completed. Total processes terminated: {killed_count}")

def main():
    parser = argparse.ArgumentParser(description="Watchdog to kill orphaned or long-running scan processes (>180s).")
    parser.add_argument("--dry-run", action="store_true", help="Log processes that exceed the threshold without terminating them.")
    args = parser.parse_args()

    logger.info("Starting watchdog scan process check (Threshold: >%ds)...", MAX_AGE_SECONDS)
    kill_orphaned_scans(dry_run=args.dry_run)

if __name__ == "__main__":
    main()
