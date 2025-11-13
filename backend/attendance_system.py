"""
Advanced Attendance Management System
API-driven attendance tracking with comprehensive features
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from threading import RLock
from typing import Dict, List, Optional, Tuple
import hashlib
import secrets


class AttendanceSystem:
    """Complete attendance management system with API support."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

        # Default configuration
        self.config = {
            "duplicate_window_minutes": 5,  # Prevent duplicate entries within 5 minutes
            "auto_mark_enabled": True,
            "working_hours_start": "09:00",
            "working_hours_end": "18:00",
            "timezone": "UTC"
        }

        # Initialize database
        self._init_db()
        print(f"[AttendanceSystem] Initialized at {self.db_path}")

    def _init_db(self) -> None:
        """Create all necessary tables."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            # Persons table (enhanced from face database)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS persons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    person_id TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    email TEXT,
                    department TEXT,
                    position TEXT,
                    phone TEXT,
                    face_encoding_path TEXT,
                    face_image_path TEXT,
                    status TEXT DEFAULT 'active',
                    metadata TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Attendance records
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    person_id TEXT NOT NULL,
                    person_name TEXT NOT NULL,
                    check_in TEXT NOT NULL,
                    check_out TEXT,
                    date TEXT NOT NULL,
                    duration_minutes INTEGER,
                    source TEXT,
                    confidence REAL,
                    snapshot_path TEXT,
                    location TEXT,
                    status TEXT DEFAULT 'present',
                    marked_by TEXT DEFAULT 'auto',
                    notes TEXT,
                    metadata TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (person_id) REFERENCES persons(person_id)
                )
            """)

            # Detection events (for audit trail)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS detection_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    person_id TEXT,
                    person_name TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    confidence REAL,
                    source TEXT,
                    snapshot_path TEXT,
                    attendance_id INTEGER,
                    processed INTEGER DEFAULT 0,
                    metadata TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (attendance_id) REFERENCES attendance(id)
                )
            """)

            # System configuration
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    description TEXT,
                    updated_at TEXT NOT NULL
                )
            """)

            # API keys for authentication
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key_hash TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    permissions TEXT NOT NULL,
                    status TEXT DEFAULT 'active',
                    created_at TEXT NOT NULL,
                    last_used TEXT,
                    expires_at TEXT
                )
            """)

            # System logs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    level TEXT NOT NULL,
                    category TEXT NOT NULL,
                    message TEXT NOT NULL,
                    details TEXT,
                    timestamp TEXT NOT NULL
                )
            """)

            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_attendance_person ON attendance(person_id, date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(date DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_detection_timestamp ON detection_events(timestamp DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_detection_person ON detection_events(person_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON system_logs(timestamp DESC)")

            conn.commit()
            conn.close()

    # ==================== PERSON MANAGEMENT ====================

    def add_person(self, person_id: str, name: str, **kwargs) -> Dict:
        """Add a new person to the system."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            try:
                now = datetime.now().isoformat()

                cursor.execute("""
                    INSERT INTO persons (
                        person_id, name, email, department, position, phone,
                        face_encoding_path, face_image_path, status, metadata,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    person_id, name,
                    kwargs.get('email'),
                    kwargs.get('department'),
                    kwargs.get('position'),
                    kwargs.get('phone'),
                    kwargs.get('face_encoding_path'),
                    kwargs.get('face_image_path'),
                    kwargs.get('status', 'active'),
                    json.dumps(kwargs.get('metadata', {})),
                    now, now
                ))

                conn.commit()

                self._log('info', 'person', f'Added person: {name} ({person_id})')

                return {
                    "success": True,
                    "message": f"Person {name} added successfully",
                    "person_id": person_id
                }

            except sqlite3.IntegrityError:
                return {
                    "success": False,
                    "message": f"Person with ID {person_id} already exists"
                }
            except Exception as e:
                return {
                    "success": False,
                    "message": f"Error adding person: {str(e)}"
                }
            finally:
                conn.close()

    def update_person(self, person_id: str, **kwargs) -> Dict:
        """Update person information."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            try:
                # Build dynamic update query
                update_fields = []
                values = []

                for field in ['name', 'email', 'department', 'position', 'phone', 'status']:
                    if field in kwargs:
                        update_fields.append(f"{field} = ?")
                        values.append(kwargs[field])

                if 'metadata' in kwargs:
                    update_fields.append("metadata = ?")
                    values.append(json.dumps(kwargs['metadata']))

                if not update_fields:
                    return {"success": False, "message": "No fields to update"}

                update_fields.append("updated_at = ?")
                values.append(datetime.now().isoformat())
                values.append(person_id)

                query = f"UPDATE persons SET {', '.join(update_fields)} WHERE person_id = ?"
                cursor.execute(query, values)

                if cursor.rowcount == 0:
                    return {"success": False, "message": "Person not found"}

                conn.commit()

                self._log('info', 'person', f'Updated person: {person_id}')

                return {"success": True, "message": "Person updated successfully"}

            except Exception as e:
                return {"success": False, "message": f"Error updating person: {str(e)}"}
            finally:
                conn.close()

    def delete_person(self, person_id: str) -> Dict:
        """Delete a person (soft delete by setting status to 'deleted')."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            try:
                cursor.execute("""
                    UPDATE persons SET status = 'deleted', updated_at = ?
                    WHERE person_id = ?
                """, (datetime.now().isoformat(), person_id))

                if cursor.rowcount == 0:
                    return {"success": False, "message": "Person not found"}

                conn.commit()

                self._log('warning', 'person', f'Deleted person: {person_id}')

                return {"success": True, "message": "Person deleted successfully"}

            except Exception as e:
                return {"success": False, "message": f"Error deleting person: {str(e)}"}
            finally:
                conn.close()

    def get_person(self, person_id: str) -> Optional[Dict]:
        """Get person details by ID."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM persons WHERE person_id = ?", (person_id,))
            row = cursor.fetchone()
            conn.close()

            if row:
                person = dict(row)
                if person.get('metadata'):
                    person['metadata'] = json.loads(person['metadata'])
                return person
            return None

    def list_persons(self, status: str = 'active', limit: int = 100, offset: int = 0) -> List[Dict]:
        """List all persons with optional filtering."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if status:
                cursor.execute("""
                    SELECT * FROM persons WHERE status = ?
                    ORDER BY name LIMIT ? OFFSET ?
                """, (status, limit, offset))
            else:
                cursor.execute("""
                    SELECT * FROM persons ORDER BY name LIMIT ? OFFSET ?
                """, (limit, offset))

            rows = cursor.fetchall()
            conn.close()

            persons = []
            for row in rows:
                person = dict(row)
                if person.get('metadata'):
                    person['metadata'] = json.loads(person['metadata'])
                persons.append(person)

            return persons

    # ==================== ATTENDANCE MANAGEMENT ====================

    def mark_attendance(
        self,
        person_id: str,
        person_name: str,
        confidence: float = 1.0,
        source: str = 'auto',
        marked_by: str = 'auto',
        **kwargs
    ) -> Dict:
        """Mark attendance for a person."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            try:
                now = datetime.now()
                today = now.strftime("%Y-%m-%d")
                check_in_time = now.isoformat()

                # Check for duplicate within time window
                if self.config['auto_mark_enabled'] and marked_by == 'auto':
                    window_start = (now - timedelta(minutes=self.config['duplicate_window_minutes'])).isoformat()

                    cursor.execute("""
                        SELECT id FROM attendance
                        WHERE person_id = ? AND date = ? AND check_in >= ?
                    """, (person_id, today, window_start))

                    if cursor.fetchone():
                        return {
                            "success": False,
                            "message": "Duplicate entry prevented (already marked recently)",
                            "duplicate": True
                        }

                # Create attendance record
                cursor.execute("""
                    INSERT INTO attendance (
                        person_id, person_name, check_in, date, source,
                        confidence, snapshot_path, location, marked_by,
                        notes, metadata, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    person_id, person_name, check_in_time, today, source,
                    confidence,
                    kwargs.get('snapshot_path'),
                    kwargs.get('location'),
                    marked_by,
                    kwargs.get('notes'),
                    json.dumps(kwargs.get('metadata', {})),
                    check_in_time, check_in_time
                ))

                attendance_id = cursor.lastrowid
                conn.commit()

                self._log('info', 'attendance', f'Marked attendance for {person_name} ({person_id})')

                return {
                    "success": True,
                    "message": "Attendance marked successfully",
                    "attendance_id": attendance_id,
                    "check_in": check_in_time
                }

            except Exception as e:
                return {"success": False, "message": f"Error marking attendance: {str(e)}"}
            finally:
                conn.close()

    def mark_checkout(self, attendance_id: int) -> Dict:
        """Mark checkout time for an attendance record."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            try:
                now = datetime.now().isoformat()

                # Get attendance record
                cursor.execute("SELECT check_in FROM attendance WHERE id = ?", (attendance_id,))
                row = cursor.fetchone()

                if not row:
                    return {"success": False, "message": "Attendance record not found"}

                check_in = datetime.fromisoformat(row[0])
                check_out = datetime.fromisoformat(now)
                duration = int((check_out - check_in).total_seconds() / 60)

                cursor.execute("""
                    UPDATE attendance
                    SET check_out = ?, duration_minutes = ?, updated_at = ?
                    WHERE id = ?
                """, (now, duration, now, attendance_id))

                conn.commit()

                return {
                    "success": True,
                    "message": "Checkout marked successfully",
                    "check_out": now,
                    "duration_minutes": duration
                }

            except Exception as e:
                return {"success": False, "message": f"Error marking checkout: {str(e)}"}
            finally:
                conn.close()

    def get_attendance(self, attendance_id: int) -> Optional[Dict]:
        """Get attendance record by ID."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM attendance WHERE id = ?", (attendance_id,))
            row = cursor.fetchone()
            conn.close()

            if row:
                record = dict(row)
                if record.get('metadata'):
                    record['metadata'] = json.loads(record['metadata'])
                return record
            return None

    def get_daily_attendance(self, date: str) -> List[Dict]:
        """Get all attendance records for a specific date."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM attendance
                WHERE date = ?
                ORDER BY check_in DESC
            """, (date,))

            rows = cursor.fetchall()
            conn.close()

            records = []
            for row in rows:
                record = dict(row)
                if record.get('metadata'):
                    record['metadata'] = json.loads(record['metadata'])
                records.append(record)

            return records

    def get_person_attendance(
        self,
        person_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict]:
        """Get attendance history for a specific person."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = "SELECT * FROM attendance WHERE person_id = ?"
            params = [person_id]

            if start_date:
                query += " AND date >= ?"
                params.append(start_date)
            if end_date:
                query += " AND date <= ?"
                params.append(end_date)

            query += " ORDER BY date DESC, check_in DESC"

            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()

            records = []
            for row in rows:
                record = dict(row)
                if record.get('metadata'):
                    record['metadata'] = json.loads(record['metadata'])
                records.append(record)

            return records

    # ==================== REPORTING & ANALYTICS ====================

    def get_attendance_report(
        self,
        start_date: str,
        end_date: str,
        person_id: Optional[str] = None
    ) -> Dict:
        """Generate comprehensive attendance report."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            # Base query
            query_base = """
                SELECT
                    person_id,
                    person_name,
                    COUNT(*) as total_days,
                    SUM(CASE WHEN status = 'present' THEN 1 ELSE 0 END) as present_days,
                    SUM(CASE WHEN status = 'absent' THEN 1 ELSE 0 END) as absent_days,
                    AVG(duration_minutes) as avg_duration,
                    SUM(duration_minutes) as total_duration
                FROM attendance
                WHERE date >= ? AND date <= ?
            """

            params = [start_date, end_date]

            if person_id:
                query_base += " AND person_id = ?"
                params.append(person_id)

            query_base += " GROUP BY person_id, person_name"

            cursor.execute(query_base, params)
            rows = cursor.fetchall()

            report = []
            for row in rows:
                report.append({
                    "person_id": row[0],
                    "person_name": row[1],
                    "total_days": row[2],
                    "present_days": row[3],
                    "absent_days": row[4],
                    "avg_duration_minutes": round(row[5], 2) if row[5] else 0,
                    "total_duration_minutes": row[6] or 0
                })

            conn.close()

            return {
                "success": True,
                "period": {"start": start_date, "end": end_date},
                "report": report
            }

    def get_daily_summary(self, date: str) -> Dict:
        """Get daily attendance summary."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    COUNT(*) as total_records,
                    COUNT(DISTINCT person_id) as unique_persons,
                    SUM(CASE WHEN status = 'present' THEN 1 ELSE 0 END) as present,
                    AVG(confidence) as avg_confidence,
                    AVG(duration_minutes) as avg_duration
                FROM attendance
                WHERE date = ?
            """, (date,))

            row = cursor.fetchone()
            conn.close()

            return {
                "date": date,
                "total_records": row[0],
                "unique_persons": row[1],
                "present": row[2],
                "avg_confidence": round(row[3], 3) if row[3] else 0,
                "avg_duration_minutes": round(row[4], 2) if row[4] else 0
            }

    # ==================== DETECTION EVENTS ====================

    def log_detection(
        self,
        person_id: Optional[str],
        person_name: str,
        confidence: float,
        source: str,
        **kwargs
    ) -> int:
        """Log a detection event."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            timestamp = datetime.now().isoformat()

            cursor.execute("""
                INSERT INTO detection_events (
                    person_id, person_name, timestamp, confidence, source,
                    snapshot_path, metadata, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                person_id, person_name, timestamp, confidence, source,
                kwargs.get('snapshot_path'),
                json.dumps(kwargs.get('metadata', {})),
                timestamp
            ))

            event_id = cursor.lastrowid
            conn.commit()
            conn.close()

            return event_id

    # ==================== CONFIGURATION ====================

    def set_config(self, key: str, value: any, description: str = "") -> Dict:
        """Update system configuration."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO system_config (key, value, description, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (key, json.dumps(value), description, datetime.now().isoformat()))

                conn.commit()

                # Update in-memory config
                self.config[key] = value

                return {"success": True, "message": "Configuration updated"}

            except Exception as e:
                return {"success": False, "message": f"Error updating config: {str(e)}"}
            finally:
                conn.close()

    def get_config(self, key: Optional[str] = None) -> Dict:
        """Get system configuration."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if key:
                cursor.execute("SELECT * FROM system_config WHERE key = ?", (key,))
                row = cursor.fetchone()
                conn.close()

                if row:
                    return {
                        "key": row['key'],
                        "value": json.loads(row['value']),
                        "description": row['description']
                    }
                return None
            else:
                cursor.execute("SELECT * FROM system_config")
                rows = cursor.fetchall()
                conn.close()

                config = {}
                for row in rows:
                    config[row['key']] = {
                        "value": json.loads(row['value']),
                        "description": row['description']
                    }

                return config

    # ==================== API AUTHENTICATION ====================

    def create_api_key(self, name: str, permissions: List[str], expires_days: Optional[int] = None) -> Dict:
        """Generate a new API key."""
        with self._lock:
            # Generate secure random key
            api_key = secrets.token_urlsafe(32)
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()

            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            try:
                now = datetime.now()
                expires_at = None
                if expires_days:
                    expires_at = (now + timedelta(days=expires_days)).isoformat()

                cursor.execute("""
                    INSERT INTO api_keys (key_hash, name, permissions, created_at, expires_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (key_hash, name, json.dumps(permissions), now.isoformat(), expires_at))

                conn.commit()

                return {
                    "success": True,
                    "api_key": api_key,
                    "message": "API key created successfully. Store it securely - it won't be shown again."
                }

            except Exception as e:
                return {"success": False, "message": f"Error creating API key: {str(e)}"}
            finally:
                conn.close()

    def validate_api_key(self, api_key: str, required_permission: Optional[str] = None) -> bool:
        """Validate API key and check permissions."""
        with self._lock:
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()

            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM api_keys
                WHERE key_hash = ? AND status = 'active'
            """, (key_hash,))

            row = cursor.fetchone()

            if not row:
                conn.close()
                return False

            # Check expiration
            if row['expires_at']:
                if datetime.fromisoformat(row['expires_at']) < datetime.now():
                    conn.close()
                    return False

            # Check permissions
            if required_permission:
                permissions = json.loads(row['permissions'])
                if required_permission not in permissions and '*' not in permissions:
                    conn.close()
                    return False

            # Update last_used
            cursor.execute("""
                UPDATE api_keys SET last_used = ? WHERE key_hash = ?
            """, (datetime.now().isoformat(), key_hash))
            conn.commit()
            conn.close()

            return True

    # ==================== LOGGING ====================

    def _log(self, level: str, category: str, message: str, details: Optional[Dict] = None) -> None:
        """Internal logging method."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO system_logs (level, category, message, details, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (
                level, category, message,
                json.dumps(details) if details else None,
                datetime.now().isoformat()
            ))

            conn.commit()
            conn.close()

    def get_logs(
        self,
        level: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get system logs."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = "SELECT * FROM system_logs WHERE 1=1"
            params = []

            if level:
                query += " AND level = ?"
                params.append(level)
            if category:
                query += " AND category = ?"
                params.append(category)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()

            logs = []
            for row in rows:
                log = dict(row)
                if log.get('details'):
                    log['details'] = json.loads(log['details'])
                logs.append(log)

            return logs

    # ========================================================================
    # ODOO INTEGRATION METHODS
    # ========================================================================

    def get_odoo_config(self) -> Optional[Dict]:
        """Get Odoo connection configuration."""
        odoo_url = self.get_config('odoo_url')
        odoo_db = self.get_config('odoo_db')
        odoo_username = self.get_config('odoo_username')
        odoo_password = self.get_config('odoo_password')

        if not all([odoo_url, odoo_db, odoo_username, odoo_password]):
            return None

        return {
            'url': odoo_url.get('value'),
            'db': odoo_db.get('value'),
            'username': odoo_username.get('value'),
            'password': odoo_password.get('value')
        }

    def sync_employees_from_odoo(self, odoo_connector) -> Dict:
        """
        Pull employees from Odoo and add/update in local database.

        Args:
            odoo_connector: Connected OdooConnector instance

        Returns:
            Dict with sync results
        """
        try:
            # Pull employees from Odoo
            result = odoo_connector.pull_employees()

            if not result.get('success'):
                return result

            employees = result.get('employees', [])
            added = 0
            updated = 0
            errors = []

            for emp in employees:
                try:
                    # Check if person exists
                    existing = self.get_person(emp['person_id'])

                    if existing:
                        # Update existing person
                        update_result = self.update_person(
                            person_id=emp['person_id'],
                            name=emp['name'],
                            email=emp['email'],
                            department=emp['department'],
                            position=emp['position'],
                            phone=emp['phone'],
                            metadata=emp['metadata']
                        )
                        if update_result.get('success'):
                            updated += 1
                        else:
                            errors.append(f"Failed to update {emp['person_id']}")
                    else:
                        # Add new person
                        add_result = self.add_person(
                            person_id=emp['person_id'],
                            name=emp['name'],
                            email=emp['email'],
                            department=emp['department'],
                            position=emp['position'],
                            phone=emp['phone'],
                            metadata=emp['metadata']
                        )
                        if add_result.get('success'):
                            added += 1
                        else:
                            errors.append(f"Failed to add {emp['person_id']}")

                except Exception as e:
                    errors.append(f"Error processing {emp.get('person_id', 'unknown')}: {str(e)}")

            self._log('info', 'odoo_sync',
                     f'Synced employees from Odoo: {added} added, {updated} updated',
                     {'added': added, 'updated': updated, 'errors': len(errors)})

            return {
                'success': True,
                'message': f'Synced {added + updated} employees from Odoo',
                'added': added,
                'updated': updated,
                'errors': errors if errors else None,
                'total': len(employees)
            }

        except Exception as e:
            self._log('error', 'odoo_sync', f'Failed to sync employees from Odoo: {str(e)}')
            return {
                'success': False,
                'error': f'Sync failed: {str(e)}'
            }

    def sync_attendance_to_odoo(self, odoo_connector, start_date: str, end_date: str) -> Dict:
        """
        Push attendance records to Odoo for a date range.

        Args:
            odoo_connector: Connected OdooConnector instance
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            Dict with sync results
        """
        try:
            # Get attendance records for the date range
            report = self.get_attendance_report(start_date, end_date)

            if not report.get('success'):
                return report

            records = report.get('records', [])

            if not records:
                return {
                    'success': True,
                    'message': 'No attendance records to sync',
                    'pushed': 0,
                    'total': 0
                }

            # Push to Odoo
            result = odoo_connector.push_attendance(records)

            self._log('info', 'odoo_sync',
                     f'Pushed attendance to Odoo: {result.get("pushed", 0)} records',
                     {'start_date': start_date, 'end_date': end_date, 'result': result})

            return result

        except Exception as e:
            self._log('error', 'odoo_sync', f'Failed to push attendance to Odoo: {str(e)}')
            return {
                'success': False,
                'error': f'Push failed: {str(e)}'
            }
