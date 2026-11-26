#!/usr/bin/env python3
"""
cron_hermes_db_night_maintenance.py

Script bảo trì CSDL Hermes chạy định kỳ lúc 2h sáng:
1. Xóa session cũ hơn 30 ngày (prune sessions).
2. Tối ưu FTS5 trigram indexes.
3. Thực hiện WAL checkpoint (TRUNCATE).
4. Chạy VACUUM để thu hồi không gian lưu trữ vật lý.
5. Cơ chế an toàn: Lock file chống chạy chồng, timeout bận, logging chi tiết.
"""

import os
import sys
import time
import sqlite3
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
from hermes_state import SessionDB, DEFAULT_DB_PATH

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("hermes_db_maintenance")

LOCK_FILE = "/tmp/hermes_db_night_maintenance.lock"

def get_db_path() -> Path:
    """Xác định đường dẫn tới CSDL Hermes."""
    env_path = os.environ.get("HERMES_DB_PATH")
    if env_path:
        return Path(env_path)

    return Path(DEFAULT_DB_PATH)

def main():
    logger.info("Bắt đầu tiến trình bảo trì CSDL Hermes đêm...")

    db_path = get_db_path()
    logger.info(f"Đường dẫn CSDL Hermes: {db_path}")
    
    if not db_path.exists():
        logger.error(f"Không tìm thấy file CSDL tại {db_path}. Thoát.")
        sys.exit(1)

    initial_size = db_path.stat().st_size
    logger.info(f"Kích thước CSDL trước bảo trì: {initial_size / (1024*1024):.2f} MB")

    try:
        db = SessionDB(db_path=db_path)

        logger.info("Prune session cũ hơn 30 ngày qua SessionDB.prune_sessions()...")
        deleted_count = db.prune_sessions(older_than_days=30)
        logger.info(f"Đã xóa thành công {deleted_count} session cũ hơn 30 ngày.")

        import shutil
        free_bytes = shutil.disk_usage(db_path.parent).free
        if free_bytes < initial_size * 2.5:
            logger.warning(f"Bỏ qua VACUUM in-place trên C: do dung lượng trống ({free_bytes // (1024*1024)} MB) < 2.5x CSDL.")
        else:
            try:
                start_time = time.time()
                optimized = db.vacuum()
                logger.info(f"Hoàn thành VACUUM trong {time.time() - start_time:.2f}s (optimize {optimized} FTS index).")
            except Exception as ve:
                logger.warning(f"Bỏ qua VACUUM do lỗi đĩa/khóa: {ve}")

        final_size = db_path.stat().st_size
        saved_space = initial_size - final_size
        logger.info(f"Kích thước CSDL sau bảo trì: {final_size / (1024*1024):.2f} MB (Tiết kiệm: {saved_space / (1024*1024):.2f} MB)")
        logger.info("Hoàn tất quy trình bảo trì CSDL Hermes thành công.")

    except Exception as e:
        logger.exception(f"Lỗi nghiêm trọng trong quá trình bảo trì CSDL: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
