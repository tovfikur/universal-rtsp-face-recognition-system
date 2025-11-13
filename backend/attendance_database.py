"""
Attendance Analysis Database - Store high-quality frame analysis results.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Dict, List, Optional


class AttendanceDatabase:
    """SQLite-backed attendance analysis database."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

        # Initialize database
        self._init_db()
        print(f"[AttendanceDB] Initialized at {self.db_path}")

    def _init_db(self) -> None:
        """Create attendance tables if they don't exist."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            # Attendance snapshots - one record per analysis
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS attendance_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    total_persons INTEGER NOT NULL,
                    known_persons INTEGER NOT NULL,
                    unknown_persons INTEGER NOT NULL,
                    person_names TEXT,
                    person_details TEXT,
                    source TEXT,
                    snapshot_path TEXT,
                    metadata TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            # Attendance summary - tracks presence over time
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS attendance_summary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    person_name TEXT NOT NULL,
                    person_id TEXT,
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    total_appearances INTEGER DEFAULT 1,
                    average_confidence REAL,
                    source TEXT,
                    date TEXT NOT NULL,
                    metadata TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_snapshot_timestamp
                ON attendance_snapshots(timestamp DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_summary_person
                ON attendance_summary(person_name, date)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_summary_date
                ON attendance_summary(date DESC)
            """)

            conn.commit()
            conn.close()

    def add_snapshot(
        self,
        total_persons: int,
        known_persons: int,
        unknown_persons: int,
        person_names: List[str],
        person_details: List[Dict],
        source: Optional[str] = None,
        snapshot_path: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> int:
        """
        Add a new attendance snapshot.

        Args:
            total_persons: Total number of people detected
            known_persons: Number of known people
            unknown_persons: Number of unknown people
            person_names: List of detected person names
            person_details: List of person detail dictionaries
            source: Video source
            snapshot_path: Path to saved snapshot image
            metadata: Additional metadata

        Returns:
            int: The ID of the inserted record
        """
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            timestamp = datetime.now().isoformat()
            person_names_json = json.dumps(person_names)
            person_details_json = json.dumps(person_details)
            metadata_json = json.dumps(metadata) if metadata else None

            cursor.execute("""
                INSERT INTO attendance_snapshots (
                    timestamp, total_persons, known_persons, unknown_persons,
                    person_names, person_details, source, snapshot_path,
                    metadata, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp, total_persons, known_persons, unknown_persons,
                person_names_json, person_details_json, source, snapshot_path,
                metadata_json, timestamp
            ))

            snapshot_id = cursor.lastrowid
            conn.commit()
            conn.close()

            return snapshot_id

    def update_summary(
        self,
        person_name: str,
        person_id: Optional[str] = None,
        confidence: Optional[float] = None,
        source: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Update attendance summary for a person.

        Creates new entry if person not seen today, otherwise updates existing.
        """
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            now = datetime.now()
            timestamp = now.isoformat()
            date = now.strftime("%Y-%m-%d")

            # Check if person already has entry for today
            cursor.execute("""
                SELECT id, total_appearances, average_confidence
                FROM attendance_summary
                WHERE person_name = ? AND date = ?
            """, (person_name, date))

            row = cursor.fetchone()

            if row:
                # Update existing entry
                summary_id, appearances, avg_conf = row
                new_appearances = appearances + 1

                # Update average confidence if provided
                if confidence is not None and avg_conf is not None:
                    new_avg_conf = ((avg_conf * appearances) + confidence) / new_appearances
                elif confidence is not None:
                    new_avg_conf = confidence
                else:
                    new_avg_conf = avg_conf

                cursor.execute("""
                    UPDATE attendance_summary
                    SET last_seen = ?,
                        total_appearances = ?,
                        average_confidence = ?,
                        metadata = ?
                    WHERE id = ?
                """, (
                    timestamp,
                    new_appearances,
                    new_avg_conf,
                    json.dumps(metadata) if metadata else None,
                    summary_id
                ))
            else:
                # Create new entry for today
                cursor.execute("""
                    INSERT INTO attendance_summary (
                        person_name, person_id, first_seen, last_seen,
                        total_appearances, average_confidence, source,
                        date, metadata, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    person_name, person_id, timestamp, timestamp,
                    1, confidence, source, date,
                    json.dumps(metadata) if metadata else None, timestamp
                ))

            conn.commit()
            conn.close()

    def get_latest_snapshot(self) -> Optional[Dict]:
        """Get the most recent attendance snapshot."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM attendance_snapshots
                ORDER BY timestamp DESC
                LIMIT 1
            """)

            row = cursor.fetchone()
            conn.close()

            if row:
                snapshot = dict(row)
                # Parse JSON fields
                if snapshot.get('person_names'):
                    snapshot['person_names'] = json.loads(snapshot['person_names'])
                if snapshot.get('person_details'):
                    snapshot['person_details'] = json.loads(snapshot['person_details'])
                if snapshot.get('metadata'):
                    snapshot['metadata'] = json.loads(snapshot['metadata'])
                return snapshot
            return None

    def get_snapshots(
        self,
        limit: int = 50,
        offset: int = 0,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict]:
        """Get attendance snapshots with optional filtering."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = "SELECT * FROM attendance_snapshots WHERE 1=1"
            params = []

            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date)

            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date)

            query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            rows = cursor.fetchall()

            snapshots = []
            for row in rows:
                snapshot = dict(row)
                # Parse JSON fields
                if snapshot.get('person_names'):
                    snapshot['person_names'] = json.loads(snapshot['person_names'])
                if snapshot.get('person_details'):
                    snapshot['person_details'] = json.loads(snapshot['person_details'])
                if snapshot.get('metadata'):
                    snapshot['metadata'] = json.loads(snapshot['metadata'])
                snapshots.append(snapshot)

            conn.close()
            return snapshots

    def get_todays_summary(self) -> List[Dict]:
        """Get attendance summary for today."""
        today = datetime.now().strftime("%Y-%m-%d")
        return self.get_summary_by_date(today)

    def get_summary_by_date(self, date: str) -> List[Dict]:
        """Get attendance summary for a specific date."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM attendance_summary
                WHERE date = ?
                ORDER BY total_appearances DESC, person_name
            """, (date,))

            rows = cursor.fetchall()
            conn.close()

            summaries = []
            for row in rows:
                summary = dict(row)
                if summary.get('metadata'):
                    try:
                        summary['metadata'] = json.loads(summary['metadata'])
                    except:
                        summary['metadata'] = {}
                summaries.append(summary)

            return summaries

    def get_attendance_statistics(self, date: Optional[str] = None) -> Dict:
        """Get attendance statistics for a date (defaults to today)."""
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")

        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            # Total unique people today
            cursor.execute("""
                SELECT COUNT(DISTINCT person_name) as total_unique
                FROM attendance_summary
                WHERE date = ?
            """, (date,))
            total_unique = cursor.fetchone()[0]

            # Known vs Unknown
            cursor.execute("""
                SELECT COUNT(*) as known_count
                FROM attendance_summary
                WHERE date = ? AND person_name != 'Unknown'
            """, (date,))
            known_count = cursor.fetchone()[0]

            cursor.execute("""
                SELECT COUNT(*) as unknown_count
                FROM attendance_summary
                WHERE date = ? AND person_name = 'Unknown'
            """, (date,))
            unknown_count = cursor.fetchone()[0]

            # Most frequent person
            cursor.execute("""
                SELECT person_name, total_appearances
                FROM attendance_summary
                WHERE date = ? AND person_name != 'Unknown'
                ORDER BY total_appearances DESC
                LIMIT 1
            """, (date,))
            most_frequent = cursor.fetchone()

            # Average persons per snapshot
            cursor.execute("""
                SELECT AVG(total_persons) as avg_persons
                FROM attendance_snapshots
                WHERE DATE(timestamp) = ?
            """, (date,))
            avg_persons = cursor.fetchone()[0] or 0

            conn.close()

            return {
                "date": date,
                "total_unique_persons": total_unique,
                "known_persons": known_count,
                "unknown_persons": unknown_count,
                "most_frequent_person": {
                    "name": most_frequent[0] if most_frequent else None,
                    "appearances": most_frequent[1] if most_frequent else 0
                },
                "average_persons_per_frame": round(avg_persons, 2)
            }

    def clear_old_snapshots(self, days: int = 7) -> int:
        """Delete snapshots older than specified days. Returns count of deleted records."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM attendance_snapshots
                WHERE timestamp < datetime('now', '-' || ? || ' days')
            """, (days,))

            count = cursor.rowcount
            conn.commit()
            conn.close()

            return count
