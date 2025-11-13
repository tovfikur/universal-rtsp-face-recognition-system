"""
Complete API Routes for Attendance Management System
All system operations are controlled through these APIs
"""

from quart import Blueprint, request, Response, jsonify
from functools import wraps
from typing import Dict, Optional
import csv
import io
from datetime import datetime, timedelta

# Create blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

# Global reference to attendance system (will be set in main app)
attendance_system = None


# ==================== AUTHENTICATION DECORATOR ====================

def require_auth(permission: Optional[str] = None):
    """Decorator to require API key authentication."""
    def decorator(f):
        @wraps(f)
        async def decorated_function(*args, **kwargs):
            # Get API key from header
            api_key = request.headers.get('X-API-Key') or request.headers.get('Authorization')

            if not api_key:
                return jsonify({
                    "success": False,
                    "error": "API key required",
                    "message": "Please provide X-API-Key header"
                }), 401

            # Remove 'Bearer ' prefix if present
            if api_key.startswith('Bearer '):
                api_key = api_key[7:]

            # Validate API key
            if not attendance_system.validate_api_key(api_key, permission):
                return jsonify({
                    "success": False,
                    "error": "Invalid or expired API key",
                    "message": "Authentication failed"
                }), 403

            return await f(*args, **kwargs)
        return decorated_function
    return decorator


# ==================== PERSON MANAGEMENT APIs ====================

@api_bp.route('/persons', methods=['POST'])
@require_auth('person:write')
async def create_person():
    """
    Create a new person in the system.

    Request Body:
    {
        "person_id": "EMP001",
        "name": "John Doe",
        "email": "john@example.com",
        "department": "Engineering",
        "position": "Developer",
        "phone": "+1234567890",
        "metadata": {}
    }
    """
    try:
        data = await request.get_json()

        if not data.get('person_id') or not data.get('name'):
            return jsonify({
                "success": False,
                "error": "Missing required fields",
                "message": "person_id and name are required"
            }), 400

        result = attendance_system.add_person(
            person_id=data['person_id'],
            name=data['name'],
            email=data.get('email'),
            department=data.get('department'),
            position=data.get('position'),
            phone=data.get('phone'),
            metadata=data.get('metadata', {})
        )

        status_code = 201 if result['success'] else 400
        return jsonify(result), status_code

    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Server error",
            "message": str(e)
        }), 500


@api_bp.route('/persons/<person_id>', methods=['GET'])
@require_auth('person:read')
async def get_person(person_id: str):
    """Get person details by ID."""
    try:
        person = attendance_system.get_person(person_id)

        if not person:
            return jsonify({
                "success": False,
                "error": "Not found",
                "message": f"Person {person_id} not found"
            }), 404

        return jsonify({
            "success": True,
            "person": person
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Server error",
            "message": str(e)
        }), 500


@api_bp.route('/persons', methods=['GET'])
@require_auth('person:read')
async def list_persons():
    """
    List all persons with pagination.

    Query Parameters:
    - status: Filter by status (active, inactive, deleted)
    - limit: Number of records per page (default: 100)
    - offset: Offset for pagination (default: 0)
    """
    try:
        status = request.args.get('status', 'active')
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))

        persons = attendance_system.list_persons(status=status, limit=limit, offset=offset)

        return jsonify({
            "success": True,
            "count": len(persons),
            "limit": limit,
            "offset": offset,
            "persons": persons
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Server error",
            "message": str(e)
        }), 500


@api_bp.route('/persons/<person_id>', methods=['PUT'])
@require_auth('person:write')
async def update_person(person_id: str):
    """
    Update person information.

    Request Body:
    {
        "name": "Updated Name",
        "email": "new@example.com",
        "department": "New Department",
        "status": "active"
    }
    """
    try:
        data = await request.get_json()
        result = attendance_system.update_person(person_id, **data)

        status_code = 200 if result['success'] else 400
        return jsonify(result), status_code

    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Server error",
            "message": str(e)
        }), 500


@api_bp.route('/persons/<person_id>', methods=['DELETE'])
@require_auth('person:delete')
async def delete_person(person_id: str):
    """Soft delete a person (sets status to 'deleted')."""
    try:
        result = attendance_system.delete_person(person_id)

        status_code = 200 if result['success'] else 404
        return jsonify(result), status_code

    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Server error",
            "message": str(e)
        }), 500


@api_bp.route('/persons/<person_id>/register-face', methods=['POST'])
@require_auth('person:write')
async def register_person_face(person_id: str):
    """
    Register a face for an existing person (for Odoo integration).

    This endpoint allows external systems (like Odoo) to send a face image
    to register for an existing person.

    Request Body:
    {
        "image": "base64_encoded_image_data",
        "force_update": false  // Optional: overwrite existing face
    }

    The image should be base64 encoded (with or without data:image prefix)
    """
    try:
        import base64
        import cv2
        import numpy as np
        import face_recognition
        from pathlib import Path

        # Get the person first
        person = attendance_system.get_person(person_id)
        if not person:
            return jsonify({
                "success": False,
                "error": "Person not found",
                "message": f"Person with ID {person_id} not found"
            }), 404

        # Get request data
        data = await request.get_json()
        image_data = data.get('image')
        force_update = data.get('force_update', False)

        if not image_data:
            return jsonify({
                "success": False,
                "error": "Missing image data",
                "message": "image field is required"
            }), 400

        # Decode base64 image
        try:
            # Remove data URI prefix if present
            if ',' in image_data:
                image_data = image_data.split(',')[1]

            image_bytes = base64.b64decode(image_data)
            nparr = np.frombuffer(image_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if frame is None:
                raise ValueError("Failed to decode image")

        except Exception as e:
            return jsonify({
                "success": False,
                "error": "Invalid image data",
                "message": f"Could not decode image: {str(e)}"
            }), 400

        # Detect face in image
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        locations = face_recognition.face_locations(rgb, number_of_times_to_upsample=0, model="hog")

        if not locations:
            return jsonify({
                "success": False,
                "error": "No face detected",
                "message": "No face was detected in the provided image"
            }), 422

        # Get face encodings
        encodings = face_recognition.face_encodings(rgb, locations)
        if not encodings:
            return jsonify({
                "success": False,
                "error": "Could not encode face",
                "message": "Face was detected but could not be encoded"
            }), 422

        # Use the most prominent face
        encoding = encodings[0]
        top, right, bottom, left = locations[0]

        # Extract face image
        face_image = frame[top:bottom, left:right]
        if face_image.size == 0:
            face_image = frame

        # Save face image
        from app import save_face_image, database, recognizer, BACKEND_DIR

        image_path = save_face_image(face_image, person['name'])

        # Add to face database
        entry = database.add_face(
            name=person['name'],
            encoding=encoding,
            image_path=image_path,
            person_id=person_id
        )

        # Update recognizer's known faces immediately
        recognizer.known_face_encodings.append(encoding)
        recognizer.known_face_names.append(person['name'])

        # Update person in attendance system with face info
        attendance_system.update_person(
            person_id=person_id,
            face_encoding_path=str(BACKEND_DIR / "data" / f"{person['name']}.npy"),
            face_image_path=str(image_path),
            metadata={
                **person.get('metadata', {}),
                'face_registered': True,
                'face_registered_at': datetime.now().isoformat(),
                'registered_via': 'api'
            }
        )

        print(f"[INFO] Registered face for person: {person['name']} (ID: {person_id})")
        print(f"[INFO] Total known faces: {len(recognizer.known_face_encodings)}")

        return jsonify({
            "success": True,
            "message": f"Face registered successfully for {person['name']}",
            "data": {
                "person_id": person_id,
                "name": person['name'],
                "face_id": entry.get('created_at'),
                "image_path": str(image_path),
                "total_faces": len(recognizer.known_face_encodings)
            }
        }), 201

    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Server error",
            "message": str(e)
        }), 500


# ==================== ATTENDANCE MANAGEMENT APIs ====================

@api_bp.route('/attendance/mark', methods=['POST'])
@require_auth('attendance:write')
async def mark_attendance():
    """
    Mark attendance for a person.

    Request Body:
    {
        "person_id": "EMP001",
        "person_name": "John Doe",
        "confidence": 0.95,
        "source": "camera_1",
        "marked_by": "auto",
        "location": "Main Entrance",
        "notes": "",
        "metadata": {}
    }
    """
    try:
        data = await request.get_json()

        if not data.get('person_id') or not data.get('person_name'):
            return jsonify({
                "success": False,
                "error": "Missing required fields",
                "message": "person_id and person_name are required"
            }), 400

        result = attendance_system.mark_attendance(
            person_id=data['person_id'],
            person_name=data['person_name'],
            confidence=data.get('confidence', 1.0),
            source=data.get('source', 'manual'),
            marked_by=data.get('marked_by', 'api'),
            location=data.get('location'),
            notes=data.get('notes'),
            metadata=data.get('metadata', {})
        )

        status_code = 201 if result['success'] else 400
        return jsonify(result), status_code

    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Server error",
            "message": str(e)
        }), 500


@api_bp.route('/attendance/<int:attendance_id>/checkout', methods=['POST'])
@require_auth('attendance:write')
async def mark_checkout(attendance_id: int):
    """Mark checkout time for an attendance record."""
    try:
        result = attendance_system.mark_checkout(attendance_id)

        status_code = 200 if result['success'] else 404
        return jsonify(result), status_code

    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Server error",
            "message": str(e)
        }), 500


@api_bp.route('/attendance/<int:attendance_id>', methods=['GET'])
@require_auth('attendance:read')
async def get_attendance_record(attendance_id: int):
    """Get specific attendance record."""
    try:
        record = attendance_system.get_attendance(attendance_id)

        if not record:
            return jsonify({
                "success": False,
                "error": "Not found",
                "message": f"Attendance record {attendance_id} not found"
            }), 404

        return jsonify({
            "success": True,
            "attendance": record
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Server error",
            "message": str(e)
        }), 500


@api_bp.route('/attendance/daily/<date>', methods=['GET'])
@require_auth('attendance:read')
async def get_daily_attendance(date: str):
    """
    Get all attendance records for a specific date.

    URL Parameter:
    - date: Date in YYYY-MM-DD format
    """
    try:
        records = attendance_system.get_daily_attendance(date)

        return jsonify({
            "success": True,
            "date": date,
            "count": len(records),
            "attendance": records
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Server error",
            "message": str(e)
        }), 500


@api_bp.route('/attendance/person/<person_id>', methods=['GET'])
@require_auth('attendance:read')
async def get_person_attendance_history(person_id: str):
    """
    Get attendance history for a specific person.

    Query Parameters:
    - start_date: Start date (YYYY-MM-DD)
    - end_date: End date (YYYY-MM-DD)
    """
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        records = attendance_system.get_person_attendance(person_id, start_date, end_date)

        return jsonify({
            "success": True,
            "person_id": person_id,
            "count": len(records),
            "attendance": records
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Server error",
            "message": str(e)
        }), 500


@api_bp.route('/attendance/today', methods=['GET'])
@require_auth('attendance:read')
async def get_todays_attendance():
    """Get today's attendance records."""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        records = attendance_system.get_daily_attendance(today)

        return jsonify({
            "success": True,
            "date": today,
            "count": len(records),
            "attendance": records
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Server error",
            "message": str(e)
        }), 500


@api_bp.route('/attendance', methods=['GET'])
@require_auth('attendance:read')
async def list_attendance():
    """
    List all attendance records with optional filtering.

    Query Parameters:
    - start_date: Filter by start date (YYYY-MM-DD)
    - end_date: Filter by end date (YYYY-MM-DD)
    - person_id: Filter by person ID
    - limit: Maximum number of records (default: 100)
    - offset: Number of records to skip (default: 0)
    """
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        person_id = request.args.get('person_id')
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))

        # If date range provided, use report function
        if start_date and end_date:
            report = attendance_system.get_attendance_report(start_date, end_date, person_id)
            if report.get('success'):
                records = report.get('records', [])
                # Apply pagination
                paginated_records = records[offset:offset+limit]
                return jsonify({
                    "success": True,
                    "data": {
                        "records": paginated_records,
                        "total": len(records),
                        "limit": limit,
                        "offset": offset
                    }
                })
            else:
                return jsonify(report), 400

        # If person_id provided, get person's attendance
        elif person_id:
            records = attendance_system.get_person_attendance(person_id)
            paginated_records = records[offset:offset+limit]
            return jsonify({
                "success": True,
                "data": {
                    "records": paginated_records,
                    "total": len(records),
                    "limit": limit,
                    "offset": offset
                }
            })

        # Otherwise, get recent attendance (last 7 days by default)
        else:
            today = datetime.now()
            week_ago = today - timedelta(days=7)
            start_date = week_ago.strftime("%Y-%m-%d")
            end_date = today.strftime("%Y-%m-%d")

            report = attendance_system.get_attendance_report(start_date, end_date)
            if report.get('success'):
                records = report.get('records', [])
                paginated_records = records[offset:offset+limit]
                return jsonify({
                    "success": True,
                    "data": {
                        "records": paginated_records,
                        "total": len(records),
                        "limit": limit,
                        "offset": offset,
                        "note": "Showing last 7 days. Use start_date and end_date for custom range."
                    }
                })
            else:
                return jsonify(report), 400

    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Server error",
            "message": str(e)
        }), 500


# ==================== REPORTING & ANALYTICS APIs ====================

@api_bp.route('/reports/attendance', methods=['GET'])
@require_auth('reports:read')
async def get_attendance_report():
    """
    Generate attendance report for a date range.

    Query Parameters:
    - start_date: Start date (YYYY-MM-DD) [required]
    - end_date: End date (YYYY-MM-DD) [required]
    - person_id: Filter by person ID (optional)
    """
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        person_id = request.args.get('person_id')

        if not start_date or not end_date:
            return jsonify({
                "success": False,
                "error": "Missing required parameters",
                "message": "start_date and end_date are required"
            }), 400

        result = attendance_system.get_attendance_report(start_date, end_date, person_id)

        return jsonify(result)

    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Server error",
            "message": str(e)
        }), 500


@api_bp.route('/reports/daily-summary/<date>', methods=['GET'])
@require_auth('reports:read')
async def get_daily_summary(date: str):
    """Get daily attendance summary with statistics."""
    try:
        summary = attendance_system.get_daily_summary(date)

        return jsonify({
            "success": True,
            **summary
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Server error",
            "message": str(e)
        }), 500


@api_bp.route('/reports/export', methods=['GET'])
@require_auth('reports:export')
async def export_attendance():
    """
    Export attendance data in CSV or JSON format.

    Query Parameters:
    - start_date: Start date (YYYY-MM-DD) [required]
    - end_date: End date (YYYY-MM-DD) [required]
    - format: Export format (csv or json, default: csv)
    - person_id: Filter by person ID (optional)
    """
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        export_format = request.args.get('format', 'csv').lower()
        person_id = request.args.get('person_id')

        if not start_date or not end_date:
            return jsonify({
                "success": False,
                "error": "Missing required parameters",
                "message": "start_date and end_date are required"
            }), 400

        # Get attendance data
        result = attendance_system.get_attendance_report(start_date, end_date, person_id)

        if export_format == 'json':
            return jsonify(result)

        elif export_format == 'csv':
            # Generate CSV
            output = io.StringIO()
            writer = csv.writer(output)

            # Write header
            writer.writerow([
                'Person ID', 'Person Name', 'Total Days', 'Present Days',
                'Absent Days', 'Avg Duration (mins)', 'Total Duration (mins)'
            ])

            # Write data
            for record in result['report']:
                writer.writerow([
                    record['person_id'],
                    record['person_name'],
                    record['total_days'],
                    record['present_days'],
                    record['absent_days'],
                    record['avg_duration_minutes'],
                    record['total_duration_minutes']
                ])

            output.seek(0)
            return Response(
                output.getvalue(),
                mimetype='text/csv',
                headers={
                    'Content-Disposition': f'attachment; filename=attendance_report_{start_date}_{end_date}.csv'
                }
            )

        else:
            return jsonify({
                "success": False,
                "error": "Invalid format",
                "message": "Format must be 'csv' or 'json'"
            }), 400

    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Server error",
            "message": str(e)
        }), 500


# ==================== SYSTEM CONFIGURATION APIs ====================

@api_bp.route('/config', methods=['GET'])
@require_auth('config:read')
async def get_configuration():
    """Get all system configuration or specific key."""
    try:
        key = request.args.get('key')
        config = attendance_system.get_config(key)

        if key and not config:
            return jsonify({
                "success": False,
                "error": "Not found",
                "message": f"Configuration key '{key}' not found"
            }), 404

        return jsonify({
            "success": True,
            "config": config
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Server error",
            "message": str(e)
        }), 500


@api_bp.route('/config', methods=['POST'])
@require_auth('config:write')
async def update_configuration():
    """
    Update system configuration.

    Request Body:
    {
        "key": "duplicate_window_minutes",
        "value": 10,
        "description": "Prevent duplicate attendance within X minutes"
    }
    """
    try:
        data = await request.get_json()

        if not data.get('key') or 'value' not in data:
            return jsonify({
                "success": False,
                "error": "Missing required fields",
                "message": "key and value are required"
            }), 400

        result = attendance_system.set_config(
            key=data['key'],
            value=data['value'],
            description=data.get('description', '')
        )

        return jsonify(result)

    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Server error",
            "message": str(e)
        }), 500


# ==================== LOGGING & MONITORING APIs ====================

@api_bp.route('/logs', methods=['GET'])
@require_auth('logs:read')
async def get_system_logs():
    """
    Get system logs.

    Query Parameters:
    - level: Filter by log level (info, warning, error)
    - category: Filter by category
    - limit: Number of logs to return (default: 100)
    """
    try:
        level = request.args.get('level')
        category = request.args.get('category')
        limit = int(request.args.get('limit', 100))

        logs = attendance_system.get_logs(level, category, limit)

        return jsonify({
            "success": True,
            "count": len(logs),
            "logs": logs
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Server error",
            "message": str(e)
        }), 500


# ==================== API KEY MANAGEMENT APIs ====================

@api_bp.route('/auth/keys', methods=['POST'])
@require_auth('admin')
async def create_api_key():
    """
    Create a new API key.

    Request Body:
    {
        "name": "Mobile App Key",
        "permissions": ["attendance:read", "attendance:write", "person:read"],
        "expires_days": 365
    }
    """
    try:
        data = await request.get_json()

        if not data.get('name') or not data.get('permissions'):
            return jsonify({
                "success": False,
                "error": "Missing required fields",
                "message": "name and permissions are required"
            }), 400

        result = attendance_system.create_api_key(
            name=data['name'],
            permissions=data['permissions'],
            expires_days=data.get('expires_days')
        )

        status_code = 201 if result['success'] else 400
        return jsonify(result), status_code

    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Server error",
            "message": str(e)
        }), 500


@api_bp.route('/keys', methods=['GET'])
@require_auth('admin')
async def list_api_keys():
    """
    List all API keys (without showing the actual keys).

    Query Parameters:
    - status: Filter by status (active/inactive/revoked)
    - limit: Maximum number of keys (default: 100)
    """
    try:
        import sqlite3

        status_filter = request.args.get('status', 'active')
        limit = int(request.args.get('limit', 100))

        conn = sqlite3.connect(str(attendance_system.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = """
            SELECT id, name, permissions, status, created_at, last_used, expires_at
            FROM api_keys
            WHERE status = ?
            ORDER BY created_at DESC
            LIMIT ?
        """

        cursor.execute(query, (status_filter, limit))
        rows = cursor.fetchall()
        conn.close()

        keys = []
        for row in rows:
            import json
            key_data = dict(row)
            if key_data.get('permissions'):
                key_data['permissions'] = json.loads(key_data['permissions'])
            keys.append(key_data)

        return jsonify({
            "success": True,
            "data": {
                "keys": keys,
                "total": len(keys),
                "status_filter": status_filter
            }
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Server error",
            "message": str(e)
        }), 500


# ==================== DETECTION EVENTS APIs ====================

@api_bp.route('/detections/log', methods=['POST'])
@require_auth('detection:write')
async def log_detection_event():
    """
    Log a detection event (internal API for recognition system).

    Request Body:
    {
        "person_id": "EMP001",
        "person_name": "John Doe",
        "confidence": 0.95,
        "source": "camera_1",
        "snapshot_path": "/path/to/snapshot.jpg",
        "metadata": {}
    }
    """
    try:
        data = await request.get_json()

        if not data.get('person_name'):
            return jsonify({
                "success": False,
                "error": "Missing required fields",
                "message": "person_name is required"
            }), 400

        event_id = attendance_system.log_detection(
            person_id=data.get('person_id'),
            person_name=data['person_name'],
            confidence=data.get('confidence', 0.0),
            source=data.get('source', 'unknown'),
            snapshot_path=data.get('snapshot_path'),
            metadata=data.get('metadata', {})
        )

        return jsonify({
            "success": True,
            "message": "Detection logged",
            "event_id": event_id
        }), 201

    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Server error",
            "message": str(e)
        }), 500


# ==================== HEALTH & STATUS APIs ====================

@api_bp.route('/health', methods=['GET'])
async def health_check():
    """System health check (no authentication required)."""
    try:
        return jsonify({
            "success": True,
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0"
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "status": "unhealthy",
            "error": str(e)
        }), 500


@api_bp.route('/status', methods=['GET'])
@require_auth('system:read')
async def system_status():
    """
    Get detailed system status.
    Returns information about recognition threads, database, and connections.
    """
    try:
        # This will be populated from main app
        from app import background_running, snapshot_running, stream_state

        return jsonify({
            "success": True,
            "system": {
                "background_recognition": background_running,
                "snapshot_analysis": snapshot_running,
                "stream_active": stream_state.is_active() if stream_state else False,
                "current_source": stream_state.get_source() if stream_state else None
            },
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Server error",
            "message": str(e)
        }), 500


# ==================== ODOO SYNC APIs ====================

@api_bp.route('/sync/odoo/test', methods=['POST'])
@require_auth('sync:write')
async def odoo_test_connection():
    """
    Test Odoo connection with provided credentials.

    Request Body:
    {
        "url": "http://localhost:8069",
        "db": "database_name",
        "username": "admin",
        "password": "password"
    }
    """
    try:
        from odoo_connector import OdooConnector

        data = await request.get_json()

        if not all([data.get('url'), data.get('db'), data.get('username'), data.get('password')]):
            return jsonify({
                "success": False,
                "error": "Missing required fields",
                "message": "url, db, username, and password are required"
            }), 400

        # Create connector
        connector = OdooConnector(
            url=data['url'],
            db=data['db'],
            username=data['username'],
            password=data['password']
        )

        # Test connection
        result = connector.connect()

        if result.get('success'):
            # Also test if we can access the API
            test_result = connector.test_connection()
            return jsonify(test_result), 200
        else:
            return jsonify(result), 401

    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Connection test failed",
            "message": str(e)
        }), 500


@api_bp.route('/sync/odoo/pull', methods=['POST'])
@require_auth('sync:write')
async def odoo_sync_pull():
    """
    Pull employee data from Odoo and sync to local database.

    Request Body:
    {
        "url": "http://localhost:8069",  // Optional if already configured
        "db": "database_name",            // Optional if already configured
        "username": "admin",              // Optional if already configured
        "password": "password",           // Optional if already configured
        "limit": 1000                     // Optional, default 1000
    }
    """
    try:
        from odoo_connector import OdooConnector

        data = await request.get_json() or {}

        # Try to get Odoo config from system or request
        odoo_config = attendance_system.get_odoo_config()

        if not odoo_config:
            # Use credentials from request
            if not all([data.get('url'), data.get('db'), data.get('username'), data.get('password')]):
                return jsonify({
                    "success": False,
                    "error": "Odoo not configured",
                    "message": "Configure Odoo settings first or provide credentials in request"
                }), 400

            odoo_config = {
                'url': data['url'],
                'db': data['db'],
                'username': data['username'],
                'password': data['password']
            }

        # Create and connect to Odoo
        connector = OdooConnector(**odoo_config)
        connect_result = connector.connect()

        if not connect_result.get('success'):
            return jsonify(connect_result), 401

        # Sync employees
        result = attendance_system.sync_employees_from_odoo(connector)

        status_code = 200 if result['success'] else 500
        return jsonify(result), status_code

    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Sync failed",
            "message": str(e)
        }), 500


@api_bp.route('/sync/odoo/push', methods=['POST'])
@require_auth('sync:write')
async def odoo_sync_push():
    """
    Push attendance data to Odoo for a date range.

    Request Body:
    {
        "start_date": "2025-01-01",
        "end_date": "2025-01-31",
        "url": "http://localhost:8069",  // Optional if already configured
        "db": "database_name",            // Optional if already configured
        "username": "admin",              // Optional if already configured
        "password": "password"            // Optional if already configured
    }
    """
    try:
        from odoo_connector import OdooConnector
        from datetime import datetime

        data = await request.get_json()

        if not data.get('start_date') or not data.get('end_date'):
            return jsonify({
                "success": False,
                "error": "Missing required fields",
                "message": "start_date and end_date are required (YYYY-MM-DD)"
            }), 400

        # Validate dates
        try:
            datetime.strptime(data['start_date'], '%Y-%m-%d')
            datetime.strptime(data['end_date'], '%Y-%m-%d')
        except ValueError:
            return jsonify({
                "success": False,
                "error": "Invalid date format",
                "message": "Dates must be in YYYY-MM-DD format"
            }), 400

        # Try to get Odoo config from system or request
        odoo_config = attendance_system.get_odoo_config()

        if not odoo_config:
            # Use credentials from request
            if not all([data.get('url'), data.get('db'), data.get('username'), data.get('password')]):
                return jsonify({
                    "success": False,
                    "error": "Odoo not configured",
                    "message": "Configure Odoo settings first or provide credentials in request"
                }), 400

            odoo_config = {
                'url': data['url'],
                'db': data['db'],
                'username': data['username'],
                'password': data['password']
            }

        # Create and connect to Odoo
        connector = OdooConnector(**odoo_config)
        connect_result = connector.connect()

        if not connect_result.get('success'):
            return jsonify(connect_result), 401

        # Push attendance
        result = attendance_system.sync_attendance_to_odoo(
            connector,
            data['start_date'],
            data['end_date']
        )

        status_code = 200 if result['success'] else 500
        return jsonify(result), status_code

    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Sync failed",
            "message": str(e)
        }), 500


@api_bp.route('/sync/odoo/config', methods=['POST'])
@require_auth('config:write')
async def odoo_save_config():
    """
    Save Odoo connection configuration.

    Request Body:
    {
        "url": "http://localhost:8069",
        "db": "database_name",
        "username": "admin",
        "password": "password"
    }
    """
    try:
        data = await request.get_json()

        if not all([data.get('url'), data.get('db'), data.get('username'), data.get('password')]):
            return jsonify({
                "success": False,
                "error": "Missing required fields",
                "message": "url, db, username, and password are required"
            }), 400

        # Save to configuration
        attendance_system.set_config('odoo_url', data['url'], 'Odoo server URL')
        attendance_system.set_config('odoo_db', data['db'], 'Odoo database name')
        attendance_system.set_config('odoo_username', data['username'], 'Odoo username')
        attendance_system.set_config('odoo_password', data['password'], 'Odoo password')

        return jsonify({
            "success": True,
            "message": "Odoo configuration saved successfully"
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Failed to save configuration",
            "message": str(e)
        }), 500


@api_bp.route('/sync/odoo/config', methods=['GET'])
@require_auth('config:read')
async def odoo_get_config():
    """Get current Odoo configuration (password masked)."""
    try:
        config = attendance_system.get_odoo_config()

        if not config:
            return jsonify({
                "success": False,
                "message": "Odoo not configured",
                "configured": False
            }), 404

        # Mask password
        config['password'] = '***********'

        return jsonify({
            "success": True,
            "configured": True,
            "config": config
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Failed to get configuration",
            "message": str(e)
        }), 500


@api_bp.route('/sync/status', methods=['GET'])
@require_auth('sync:read')
async def sync_status():
    """Get synchronization status with external systems."""
    try:
        odoo_config = attendance_system.get_odoo_config()

        # Get last sync info from logs
        logs = attendance_system.get_logs(category='odoo_sync', limit=1)
        last_sync = logs[0] if logs else None

        return jsonify({
            "success": True,
            "data": {
                "odoo": {
                    "enabled": bool(odoo_config),
                    "configured": bool(odoo_config),
                    "url": odoo_config.get('url') if odoo_config else None,
                    "db": odoo_config.get('db') if odoo_config else None,
                    "last_sync": last_sync.get('timestamp') if last_sync else None,
                    "last_sync_message": last_sync.get('message') if last_sync else None,
                    "status": "configured" if odoo_config else "not_configured"
                }
            }
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Failed to get sync status",
            "message": str(e)
        }), 500


# Helper function to set global attendance system reference
def init_api_routes(system):
    """Initialize API routes with attendance system instance."""
    global attendance_system
    attendance_system = system

