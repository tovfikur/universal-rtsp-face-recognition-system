"""
Detection History Database - Store and manage detection records.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Dict, List, Optional


class DetectionHistory:
    """SQLite-backed detection history database with CRUD operations."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

        # Initialize database
        self._init_db()
        print(f"[DetectionHistory] Initialized at {self.db_path}")

    def _init_db(self) -> None:
        """Create detection history table if it doesn't exist."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS detections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    person_name TEXT NOT NULL,
                    person_id TEXT,
                    confidence REAL,
                    status TEXT,
                    track_id INTEGER,
                    bbox_x1 REAL,
                    bbox_y1 REAL,
                    bbox_x2 REAL,
                    bbox_y2 REAL,
                    source TEXT,
                    snapshot_path TEXT,
                    metadata TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            # Create indexes for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON detections(timestamp DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_person_name
                ON detections(person_name)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_created_at
                ON detections(created_at DESC)
            """)

            conn.commit()
            conn.close()

    def add_detection(
        self,
        person_name: str,
        person_id: Optional[str] = None,
        confidence: Optional[float] = None,
        status: str = "Unknown",
        track_id: Optional[int] = None,
        bbox: Optional[List[float]] = None,
        source: Optional[str] = None,
        snapshot_path: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> int:
        """
        Add a new detection record.

        Returns:
            int: The ID of the inserted record
        """
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            timestamp = datetime.now().isoformat()
            bbox_values = bbox if bbox and len(bbox) == 4 else [None, None, None, None]
            metadata_json = json.dumps(metadata) if metadata else None

            cursor.execute("""
                INSERT INTO detections (
                    timestamp, person_name, person_id, confidence, status,
                    track_id, bbox_x1, bbox_y1, bbox_x2, bbox_y2,
                    source, snapshot_path, metadata, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp, person_name, person_id, confidence, status,
                track_id, *bbox_values, source, snapshot_path, metadata_json, timestamp
            ))

            detection_id = cursor.lastrowid
            conn.commit()
            conn.close()

            return detection_id

    def get_all_detections(
        self,
        limit: int = 100,
        offset: int = 0,
        person_name: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict]:
        """
        Get all detection records with optional filtering.

        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            person_name: Filter by person name
            start_date: Filter by start date (ISO format)
            end_date: Filter by end date (ISO format)
        """
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = "SELECT * FROM detections WHERE 1=1"
            params = []

            if person_name:
                query += " AND person_name = ?"
                params.append(person_name)

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

            detections = []
            for row in rows:
                detection = dict(row)
                # Parse metadata JSON
                if detection.get('metadata'):
                    try:
                        detection['metadata'] = json.loads(detection['metadata'])
                    except:
                        detection['metadata'] = {}

                # Combine bbox values
                if detection.get('bbox_x1') is not None:
                    detection['bbox'] = [
                        detection['bbox_x1'],
                        detection['bbox_y1'],
                        detection['bbox_x2'],
                        detection['bbox_y2']
                    ]

                detections.append(detection)

            conn.close()
            return detections

    def get_detection_by_id(self, detection_id: int) -> Optional[Dict]:
        """Get a single detection record by ID."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM detections WHERE id = ?", (detection_id,))
            row = cursor.fetchone()
            conn.close()

            if row:
                detection = dict(row)
                if detection.get('metadata'):
                    try:
                        detection['metadata'] = json.loads(detection['metadata'])
                    except:
                        detection['metadata'] = {}
                return detection
            return None

    def update_detection(self, detection_id: int, updates: Dict) -> bool:
        """
        Update a detection record.

        Args:
            detection_id: ID of the detection to update
            updates: Dictionary of fields to update

        Returns:
            bool: True if update successful, False otherwise
        """
        allowed_fields = {
            'person_name', 'person_id', 'confidence', 'status',
            'track_id', 'source', 'snapshot_path', 'metadata'
        }

        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            # Build UPDATE query
            update_fields = []
            values = []

            for key, value in updates.items():
                if key in allowed_fields:
                    if key == 'metadata' and isinstance(value, dict):
                        value = json.dumps(value)
                    update_fields.append(f"{key} = ?")
                    values.append(value)

            if not update_fields:
                conn.close()
                return False

            values.append(detection_id)
            query = f"UPDATE detections SET {', '.join(update_fields)} WHERE id = ?"

            cursor.execute(query, values)
            success = cursor.rowcount > 0
            conn.commit()
            conn.close()

            return success

    def delete_detection(self, detection_id: int) -> bool:
        """Delete a detection record by ID."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute("DELETE FROM detections WHERE id = ?", (detection_id,))
            success = cursor.rowcount > 0
            conn.commit()
            conn.close()

            return success

    def delete_all_detections(self) -> int:
        """Delete all detection records. Returns number of deleted records."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM detections")
            count = cursor.fetchone()[0]

            cursor.execute("DELETE FROM detections")
            conn.commit()
            conn.close()

            return count

    def get_statistics(self) -> Dict:
        """Get detection statistics."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            # Total detections
            cursor.execute("SELECT COUNT(*) FROM detections")
            total = cursor.fetchone()[0]

            # Known vs Unknown
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM detections
                GROUP BY status
            """)
            status_counts = dict(cursor.fetchall())

            # Top detected persons
            cursor.execute("""
                SELECT person_name, COUNT(*) as count
                FROM detections
                WHERE person_name != 'Unknown'
                GROUP BY person_name
                ORDER BY count DESC
                LIMIT 10
            """)
            top_persons = [
                {"name": row[0], "count": row[1]}
                for row in cursor.fetchall()
            ]

            # Detections per day (last 7 days)
            cursor.execute("""
                SELECT DATE(timestamp) as date, COUNT(*) as count
                FROM detections
                WHERE timestamp >= datetime('now', '-7 days')
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
            """)
            daily_counts = [
                {"date": row[0], "count": row[1]}
                for row in cursor.fetchall()
            ]

            conn.close()

            return {
                "total_detections": total,
                "status_breakdown": status_counts,
                "top_detected_persons": top_persons,
                "daily_detections": daily_counts
            }
