#!/usr/bin/env python3
"""
Fix watchdog upload classification bug - add 'already_uploaded_in_shift' to skipped keywords.
Run this to patch feed_session_watchdog.py automatically.
"""
import re

WATCHDOG_PATH = r"D:\Taadaa\tiktok-luot nuoi acc\scripts\hermes_cron\feed_session_watchdog.py"

def fix_watchdog_classification():
    with open(WATCHDOG_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the skipped_keywords tuple and add the missing keyword
    old_pattern = r'(skipped_keywords\s*=\s*\(\s*"video_not_rendered",\s*"missing_video_folder",\s*"missing_account_id",\s*"not-final-session",\s*"sensitive-skip",\s*"cooling_period",\s*"account_cooling_period",\s*"age_gate",\s*"under_10_days"\s*\))'
    
    new_tuple = '''(skipped_keywords = (
    "video_not_rendered", "missing_video_folder", "missing_account_id",
    "not-final-session", "sensitive-skip", "cooling_period",
    "account_cooling_period", "age_gate", "under_10_days",
    "already_uploaded_in_shift"
))'''

    if re.search(old_pattern, content):
        new_content = re.sub(old_pattern, new_tuple, content)
        with open(WATCHDOG_PATH, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("✅ Patched feed_session_watchdog.py - added 'already_uploaded_in_shift' to skipped_keywords")
        return True
    else:
        print("❌ Pattern not found - file may have changed")
        return False

if __name__ == "__main__":
    fix_watchdog_classification()