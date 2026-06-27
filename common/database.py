"""SQLite 数据库封装，用于替代 JSON 文件持久化"""
import sqlite3
import os
from datetime import datetime
from typing import Optional
from loguru import logger
from utils.path_helper import get_app_dir


class Database:
    """SQLite 数据库管理器（单例）"""

    _instance: Optional["Database"] = None

    def __new__(cls, db_path: Optional[str] = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_path: Optional[str] = None):
        if self._initialized:
            return
        self._initialized = True
        db_path = db_path or os.path.join(get_app_dir(), "dailybot.db")
        self.db_path = db_path
        self._init_tables()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self):
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS camouflage_history (
                    id TEXT PRIMARY KEY, date TEXT NOT NULL, content TEXT,
                    source_name TEXT, repo_path TEXT, platform TEXT,
                    author TEXT, original_date TEXT,
                    variants TEXT DEFAULT '[]', created_at TEXT DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_camouflage_date ON camouflage_history(date);
                CREATE TABLE IF NOT EXISTS daily_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL,
                    platform TEXT NOT NULL, summary TEXT NOT NULL, raw_data TEXT,
                    is_camouflage INTEGER DEFAULT 0,
                    pushed INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_reports_date ON daily_reports(date);
                CREATE TABLE IF NOT EXISTS run_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL,
                    platform TEXT, status TEXT NOT NULL, message TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                );
            """)
        # 迁移：给旧表加 pushed 列（幂等）
        try:
            with self._get_conn() as conn:
                conn.execute("ALTER TABLE daily_reports ADD COLUMN pushed INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass  # 列已存在
        logger.debug(f"数据库已初始化: {self.db_path}")

    def save_report(self, date, platform, summary, raw_data=None, is_camouflage=False, pushed=1):
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO daily_reports (date, platform, summary, raw_data, is_camouflage, pushed) VALUES (?, ?, ?, ?, ?, ?)",
                (date, platform, summary, raw_data, int(is_camouflage), pushed),
            )

    def get_reports(self, date, platform=None, limit=10, search=None):
        with self._get_conn() as conn:
            sql = "SELECT * FROM daily_reports WHERE date=?"
            params = [date]
            if platform:
                sql += " AND platform=?"
                params.append(platform)
            if search:
                sql += " AND (summary LIKE ? OR raw_data LIKE ?)"
                params.extend([f"%{search}%", f"%{search}%"])
            sql += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]

    def get_reports_by_date_range(self, start_date, end_date, limit=100):
        with self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM daily_reports WHERE date BETWEEN ? AND ? ORDER BY created_at DESC LIMIT ?", (start_date, end_date, limit)).fetchall()
            return [dict(r) for r in rows]

    def log_run(self, date, status, platform=None, message=None):
        with self._get_conn() as conn:
            conn.execute("INSERT INTO run_logs (date, platform, status, message) VALUES (?, ?, ?, ?)", (date, platform, status, message))

    def get_run_logs(self, limit=50, search=None):
        with self._get_conn() as conn:
            sql = "SELECT * FROM run_logs"
            params = []
            if search:
                sql += " WHERE message LIKE ? OR platform LIKE ?"
                params.extend([f"%{search}%", f"%{search}%"])
            sql += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]

    def get_report_trend(self, days: int = 7):
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT date, COUNT(*) as cnt FROM daily_reports WHERE date >= date('now', ?) GROUP BY date ORDER BY date",
                (f"-{days} days",)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_platform_trend(self, days: int = 7):
        """获取各平台每日报告数（多平台对比用）"""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT date, platform, COUNT(*) as cnt FROM daily_reports WHERE date >= date('now', ?) GROUP BY date, platform ORDER BY date, platform",
                (f"-{days} days",)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_platform_stats(self):
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT platform, status, COUNT(*) as cnt FROM run_logs GROUP BY platform, status"
            ).fetchall()
            return [dict(r) for r in rows]

    def get_report_by_id(self, report_id: int):
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM daily_reports WHERE id=?", (report_id,)).fetchone()
            return dict(row) if row else None

    def update_report_summary(self, report_id: int, summary: str):
        """更新草稿日报的摘要内容"""
        with self._get_conn() as conn:
            conn.execute("UPDATE daily_reports SET summary=? WHERE id=?", (summary, report_id))

    def get_unpushed_reports(self, limit=20):
        """获取所有未推送的日报草稿"""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM daily_reports WHERE pushed=0 ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    def set_report_pushed(self, report_id: int):
        """将日报标记为已推送"""
        with self._get_conn() as conn:
            conn.execute("UPDATE daily_reports SET pushed=1 WHERE id=?", (report_id,))

    def cleanup_old_records(self, days: int = 30):
        """清理指定天数前的历史数据"""
        with self._get_conn() as conn:
            reports_deleted = conn.execute(
                "DELETE FROM daily_reports WHERE date < date('now', ?)", (f"-{days} days",)
            ).rowcount
            logs_deleted = conn.execute(
                "DELETE FROM run_logs WHERE date < date('now', ?)", (f"-{days} days",)
            ).rowcount
            # 也清理伪装历史
            camo_deleted = conn.execute(
                "DELETE FROM camouflage_history WHERE date < date('now', ?)", (f"-{days} days",)
            ).rowcount
            return {"reports_deleted": reports_deleted, "logs_deleted": logs_deleted, "camouflage_deleted": camo_deleted}


db = Database()
