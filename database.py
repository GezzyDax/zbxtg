"""SQLite database for persistent storage of alerts and statistics."""

import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

import aiosqlite

logger = logging.getLogger(__name__)


class AlertDatabase:
    """Database для хранения информации об алертах."""

    def __init__(self, db_path: str = "data/alerts.db"):
        self.db_path = db_path
        self._ensure_data_directory()

    def _ensure_data_directory(self):
        """Создает директорию для базы данных если её нет."""
        directory = os.path.dirname(self.db_path)
        if directory:
            os.makedirs(directory, exist_ok=True)

    @asynccontextmanager
    async def get_connection(self):
        """Context manager для получения подключения к БД."""
        conn = await aiosqlite.connect(self.db_path)
        try:
            yield conn
            await conn.commit()
        except Exception as e:
            await conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            await conn.close()

    async def initialize(self):
        """Инициализирует схему базы данных."""
        async with self.get_connection() as conn:
            # Таблица алертов
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS alerts (
                    event_id TEXT PRIMARY KEY,
                    message_id INTEGER,
                    status TEXT NOT NULL,
                    severity INTEGER,
                    hostname TEXT,
                    problem_name TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL,
                    resolved_at REAL,
                    acknowledged_at REAL,
                    metadata TEXT
                )
                """
            )

            # Таблица статистики
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value INTEGER NOT NULL,
                    created_at REAL NOT NULL
                )
                """
            )

            # Таблица событий (audit log)
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    event_id TEXT,
                    details TEXT,
                    timestamp REAL NOT NULL
                )
                """
            )

            # Индексы
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status)")
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts(created_at)"
            )
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_statistics_date ON statistics(date)")
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp)"
            )

            logger.info(f"Database initialized at {self.db_path}")

    async def save_alert(
        self,
        event_id: str,
        message_id: Optional[int],
        status: str,
        severity: int = 0,
        hostname: str = "",
        problem_name: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Сохраняет или обновляет алерт в базе."""
        import json
        import time

        metadata_json = json.dumps(metadata) if metadata else None
        current_time = time.time()

        async with self.get_connection() as conn:
            await conn.execute(
                """
                INSERT INTO alerts
                (event_id, message_id, status, severity, hostname, problem_name,
                 created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(event_id) DO UPDATE SET
                    message_id = excluded.message_id,
                    status = excluded.status,
                    updated_at = excluded.updated_at,
                    metadata = excluded.metadata
                """,
                (
                    event_id,
                    message_id,
                    status,
                    severity,
                    hostname,
                    problem_name,
                    current_time,
                    current_time,
                    metadata_json,
                ),
            )

    async def update_alert_status(
        self,
        event_id: str,
        status: str,
        resolved_at: Optional[float] = None,
        acknowledged_at: Optional[float] = None,
    ):
        """Обновляет статус алерта."""
        import time

        async with self.get_connection() as conn:
            await conn.execute(
                """
                UPDATE alerts
                SET status = ?, updated_at = ?, resolved_at = ?, acknowledged_at = ?
                WHERE event_id = ?
                """,
                (status, time.time(), resolved_at, acknowledged_at, event_id),
            )

    async def get_alert(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Получает алерт по event_id."""
        async with self.get_connection() as conn:
            async with conn.execute(
                "SELECT * FROM alerts WHERE event_id = ?", (event_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, row))
                return None

    async def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Получает все активные алерты."""
        async with self.get_connection() as conn:
            async with conn.execute(
                "SELECT * FROM alerts WHERE status = 'problem' ORDER BY created_at DESC"
            ) as cursor:
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]

    async def get_alerts_by_status(self, status: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Получает алерты по статусу."""
        async with self.get_connection() as conn:
            async with conn.execute(
                "SELECT * FROM alerts WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit),
            ) as cursor:
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]

    async def delete_old_alerts(self, days: int = 30):
        """Удаляет старые алерты."""
        import time

        cutoff_time = time.time() - (days * 24 * 3600)
        async with self.get_connection() as conn:
            result = await conn.execute("DELETE FROM alerts WHERE created_at < ?", (cutoff_time,))
            deleted_count = result.rowcount
            logger.info(f"Deleted {deleted_count} old alerts (older than {days} days)")
            return deleted_count

    async def save_statistic(self, metric_name: str, metric_value: int):
        """Сохраняет статистику."""
        import time
        from datetime import datetime

        date = datetime.now().strftime("%Y-%m-%d")
        async with self.get_connection() as conn:
            await conn.execute(
                "INSERT INTO statistics (date, metric_name, metric_value, created_at) VALUES (?, ?, ?, ?)",
                (date, metric_name, metric_value, time.time()),
            )

    async def get_statistics(self, metric_name: str, days: int = 7) -> List[Dict[str, Any]]:
        """Получает статистику за период."""
        from datetime import datetime, timedelta

        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        async with self.get_connection() as conn:
            async with conn.execute(
                """
                SELECT date, metric_name, SUM(metric_value) as total
                FROM statistics
                WHERE metric_name = ? AND date >= ?
                GROUP BY date
                ORDER BY date DESC
                """,
                (metric_name, start_date),
            ) as cursor:
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]

    async def log_event(
        self, event_type: str, event_id: Optional[str] = None, details: Optional[str] = None
    ):
        """Логирует событие в audit log."""
        import time

        async with self.get_connection() as conn:
            await conn.execute(
                "INSERT INTO events (event_type, event_id, details, timestamp) VALUES (?, ?, ?, ?)",
                (event_type, event_id, details, time.time()),
            )

    async def get_recent_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Получает последние события."""
        async with self.get_connection() as conn:
            async with conn.execute(
                "SELECT * FROM events ORDER BY timestamp DESC LIMIT ?", (limit,)
            ) as cursor:
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]

    async def get_stats_summary(self) -> Dict[str, Any]:
        """Получает сводную статистику."""
        async with self.get_connection() as conn:
            # Общее количество алертов
            async with conn.execute("SELECT COUNT(*) FROM alerts") as cursor:
                total_alerts = (await cursor.fetchone())[0]

            # Активные алерты
            async with conn.execute(
                "SELECT COUNT(*) FROM alerts WHERE status = 'problem'"
            ) as cursor:
                active_alerts = (await cursor.fetchone())[0]

            # Решенные алерты
            async with conn.execute(
                "SELECT COUNT(*) FROM alerts WHERE status = 'resolved'"
            ) as cursor:
                resolved_alerts = (await cursor.fetchone())[0]

            # Алерты по серьезности
            async with conn.execute(
                """
                SELECT severity, COUNT(*) as count
                FROM alerts
                WHERE status = 'problem'
                GROUP BY severity
                """
            ) as cursor:
                severity_counts = {row[0]: row[1] for row in await cursor.fetchall()}

            return {
                "total_alerts": total_alerts,
                "active_alerts": active_alerts,
                "resolved_alerts": resolved_alerts,
                "severity_distribution": severity_counts,
            }
