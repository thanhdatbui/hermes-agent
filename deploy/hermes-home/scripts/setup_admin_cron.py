#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Setup Admin Hermes Cron Jobs and deploy scripts.

Features:
- Copies all scripts from D:\\OneDrive\\Taadaa_Sync_Shared\\hermes-cron\\scripts\\ to %LOCALAPPDATA%\\hermes\\scripts\\
- Manages %LOCALAPPDATA%\\hermes\\cron\\jobs.json (with automatic backup to jobs.json.bak)
- Configures 12 core Admin cron jobs (updates existing or registers new)
- Supports --dry-run to preview actions without modifying files
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import shutil
import sys
import uuid
from typing import Any, Dict, List, Optional

SHARED_SCRIPTS_DIR = r"D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\scripts"

ADMIN_CRON_JOBS = [
    {
        "name": "taikhoan-run-safe-sync",
        "expr": "*/5 * * * *",
        "no_agent": True,
        "script": "taikhoan_sync_cron_launcher.py",
        "deliver": "local",
        "workdir": None,
    },
    {
        "name": "reap-dead-owner-locks",
        "expr": "*/15 * * * *",
        "no_agent": True,
        "script": "reap-dead-owner-locks-wrapper.py",
        "deliver": "local",
        "workdir": r"D:\Taadaa\tiktok-luot nuoi acc",
    },
    {
        "name": "phase9-staging-picker",
        "expr": "0 6 * * *",
        "no_agent": True,
        "script": "tiktok_picker.py",
        "deliver": "local",
        "workdir": r"D:\Taadaa\tiktok-luot nuoi acc",
    },
    {
        "name": "auto-trim-startup-files",
        "expr": "0 3 * * 0",
        "no_agent": True,
        "script": "auto_trim_startup_files.py",
        "deliver": "telegram:-5188753741",
        "workdir": None,
    },
    {
        "name": "phase9-runner-tiktok-feed",
        "expr": "*/15 * * * *",
        "no_agent": True,
        "script": "tiktok_runner.py",
        "deliver": "local",
        "workdir": r"D:\Taadaa\tiktok-luot nuoi acc",
    },
    {
        "name": "device-locks-watchdog",
        "expr": "1,16,31,46 * * * *",
        "no_agent": True,
        "script": "watch_device_locks.py",
        "deliver": "telegram:-5188753741",
        "workdir": None,
    },
    {
        "name": "end-of-day-clear-tiktok-cache",
        "expr": "*/10 1,2,3,4 * * *",
        "no_agent": True,
        "script": "cron_clear_tiktok_cache.py",
        "deliver": "telegram:-5188753741",
        "workdir": None,
    },
    {
        "name": "tiktok-feed-session-watchdog",
        "expr": "*/5 * * * *",
        "no_agent": True,
        "script": "feed_session_watchdog.py",
        "deliver": "telegram:-5188753741",
        "workdir": None,
    },
    {
        "name": "hermes-stale-watchdog",
        "expr": "*/2 * * * *",
        "no_agent": True,
        "script": "hermes_stale_watchdog.py",
        "deliver": "telegram:-5188753741",
        "workdir": None,
    },
    {
        "name": "farm-render-download-watchdog",
        "expr": "0 * * * *",
        "no_agent": True,
        "script": "farm_render_download_watchdog.py",
        "deliver": "telegram:-5188753741",
        "workdir": None,
    },
    {
        "name": "post-morning-gmail-2fa-watchdog",
        "expr": "*/5 8,9,10,11 * * *",
        "no_agent": True,
        "script": "post_morning_gmail_2fa_watchdog.py",
        "deliver": "telegram:-5188753741",
        "workdir": None,
    },
    {
        "name": "post-noon-chain-watchdog",
        "expr": "*/5 14,15,16,17 * * *",
        "no_agent": True,
        "script": "post_noon_chain_watchdog.py",
        "deliver": "telegram:-5188753741",
        "workdir": None,
    },
    {
        "name": "post-evening-avatar-watchdog",
        "expr": "*/10 21,22,23 * * *",
        "no_agent": True,
        "script": "post_evening_avatar_watchdog.py",
        "deliver": "telegram:-5188753741",
        "workdir": None,
    },
    {
        "name": "post-evening-gpm-login-watchdog",
        "expr": "*/10 21,22,23 * * *",
        "no_agent": True,
        "script": "post_evening_gpm_login_watchdog.py",
        "deliver": "telegram:-5188753741",
        "workdir": None,
    },
    {
        "name": "sync-all-tik-keywords-cron",
        "expr": "*/15 * * * *",
        "no_agent": True,
        "script": "sync_all_tik_keywords.py",
        "deliver": "local",
        "workdir": None,
    },
]


def get_localappdata() -> str:
    local_app = os.environ.get("LOCALAPPDATA")
    if not local_app:
        local_app = os.path.expanduser(r"~\AppData\Local")
    return local_app


def get_hermes_scripts_dir() -> str:
    return os.path.join(get_localappdata(), "hermes", "scripts")


def get_jobs_json_path() -> str:
    return os.path.join(get_localappdata(), "hermes", "cron", "jobs.json")


def make_new_job_dict(spec: Dict[str, Any]) -> Dict[str, Any]:
    now_iso = datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()
    return {
        "id": uuid.uuid4().hex[:12],
        "name": spec["name"],
        "prompt": "",
        "skills": [],
        "skill": None,
        "model": None,
        "provider": None,
        "provider_snapshot": None,
        "model_snapshot": None,
        "base_url": None,
        "script": spec["script"],
        "no_agent": spec.get("no_agent", True),
        "context_from": None,
        "schedule": {
            "kind": "cron",
            "expr": spec["expr"],
            "display": spec["expr"],
        },
        "schedule_display": spec["expr"],
        "repeat": {
            "times": None,
            "completed": 0,
        },
        "enabled": True,
        "state": "scheduled",
        "paused_at": None,
        "paused_reason": None,
        "created_at": now_iso,
        "next_run_at": None,
        "last_run_at": None,
        "last_status": None,
        "last_error": None,
        "last_delivery_error": None,
        "deliver": spec["deliver"],
        "origin": None,
        "enabled_toolsets": None,
        "workdir": spec.get("workdir"),
        "run_claim": None,
        "fire_claim": None,
    }


def update_job_dict(job: Dict[str, Any], spec: Dict[str, Any]) -> None:
    job["name"] = spec["name"]
    job["script"] = spec["script"]
    job["no_agent"] = spec.get("no_agent", True)
    job["schedule"] = {
        "kind": "cron",
        "expr": spec["expr"],
        "display": spec["expr"],
    }
    job["schedule_display"] = spec["expr"]
    job["deliver"] = spec["deliver"]
    job["workdir"] = spec.get("workdir")
    job["enabled"] = True
    job["state"] = "scheduled"


def match_existing_job(jobs: List[Dict[str, Any]], spec_name: str) -> Optional[Dict[str, Any]]:
    for job in jobs:
        curr_name = job.get("name", "")
        if curr_name == spec_name:
            return job
    # Also match prefix (e.g. phase9-staging-picker-*)
    for job in jobs:
        curr_name = job.get("name", "")
        if curr_name.startswith(f"{spec_name}-"):
            return job
    return None


def run(dry_run: bool = False) -> None:
    print(f"=== Setup Admin Hermes Cron (dry_run={dry_run}) ===")

    # Step 1: Check scripts to copy
    scripts_src = SHARED_SCRIPTS_DIR
    scripts_dst = get_hermes_scripts_dir()

    if not os.path.exists(scripts_src):
        print(f"[ERROR] Source scripts folder does not exist: {scripts_src}", file=sys.stderr)
        sys.exit(1)

    src_files = [f for f in sorted(os.listdir(scripts_src)) if os.path.isfile(os.path.join(scripts_src, f))]
    print(f"\n[1] Source scripts to deploy ({len(src_files)} files):")
    for f in src_files:
        print(f"  - {f}")

    if not dry_run:
        os.makedirs(scripts_dst, exist_ok=True)
        copied_cnt = 0
        for f in src_files:
            s_path = os.path.join(scripts_src, f)
            d_path = os.path.join(scripts_dst, f)
            shutil.copy2(s_path, d_path)
            copied_cnt += 1
        print(f"-> Successfully copied {copied_cnt} scripts to {scripts_dst}")
    else:
        print(f"-> [DRY-RUN] Would copy {len(src_files)} scripts to {scripts_dst}")

    # Step 2: Read jobs.json
    jobs_file = get_jobs_json_path()
    jobs_data: Dict[str, Any] = {"jobs": []}

    if os.path.exists(jobs_file):
        try:
            with open(jobs_file, "r", encoding="utf-8") as f:
                jobs_data = json.load(f)
            if not isinstance(jobs_data, dict) or "jobs" not in jobs_data:
                jobs_data = {"jobs": []}
        except Exception as exc:
            print(f"[WARN] Failed to parse {jobs_file}: {exc}. Starting with empty jobs.")
            jobs_data = {"jobs": []}

    jobs_list: List[Dict[str, Any]] = jobs_data.get("jobs", [])

    # Step 3: Plan updates / inserts for the 13 Admin cron jobs
    print(f"\n[2] Target Admin Cron Jobs ({len(ADMIN_CRON_JOBS)} jobs):")
    plan = []
    for spec in ADMIN_CRON_JOBS:
        existing = match_existing_job(jobs_list, spec["name"])
        action = "UPDATE" if existing else "CREATE"
        plan.append((action, spec, existing))
        workdir_str = f" [workdir={spec['workdir']}]" if spec.get("workdir") else ""
        print(f"  - [{action}] {spec['name']} ({spec['expr']}) -> {spec['script']} | deliver={spec['deliver']}{workdir_str}")

    if dry_run:
        print("\n[DRY-RUN] Dry run complete. No modifications were written to disk.")
        return

    # Backup jobs.json if exists
    if os.path.exists(jobs_file):
        bak_file = f"{jobs_file}.bak"
        shutil.copy2(jobs_file, bak_file)
        print(f"\n-> Backed up existing jobs.json to {bak_file}")

    # Apply changes
    for action, spec, existing in plan:
        if action == "UPDATE" and existing is not None:
            update_job_dict(existing, spec)
        else:
            new_job = make_new_job_dict(spec)
            jobs_list.append(new_job)

    jobs_data["jobs"] = jobs_list
    jobs_data["updated_at"] = datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()

    os.makedirs(os.path.dirname(jobs_file), exist_ok=True)
    temp_file = f"{jobs_file}.tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(jobs_data, f, ensure_ascii=False, indent=2)
    os.replace(temp_file, jobs_file)

    print(f"-> Successfully updated {len(ADMIN_CRON_JOBS)} Admin jobs in {jobs_file}")
    print("\n=== Hoàn tất cài đặt Admin Cron Jobs! ===")


def main() -> None:
    parser = argparse.ArgumentParser(description="Setup Admin Hermes Cron Jobs")
    parser.add_argument("--dry-run", action="store_true", help="Preview scripts and cron jobs without changing disk")
    args = parser.parse_args()
    run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
